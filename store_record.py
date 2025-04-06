import csv
import json
import logging
import requests
import openmeteo_requests
import requests_cache
import pandas as pd
from retry_requests import retry
from kafka import KafkaConsumer
from datetime import datetime as dt, timedelta
from sqlalchemy import create_engine
from dotenv import load_dotenv
from sqlalchemy import inspect
import os
import random 

from utils.db_utils import DatabaseInteractor
from utils.streaming_utils import StateConsumer
from utils.api_utils import MeteoAPI

from sklearn.model_selection import train_test_split
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_squared_error, r2_score
    
    

load_dotenv()

DF_COLUMNS = {
    'id': 'bigint'
    , 'place_id': 'int'
    , 'temperature': 'float'
    , 'humidity': 'float'
    , 'salinity': 'float'
    , 'ph': 'float'
    , 'rain': 'float'
    , 's_moist': 'float'
    , 'created_at': 'datetime'
    , 'updated_at': 'datetime'
    , 'intervention': 'int'
    , 'intervention_time': 'datetime'
    , 'intervention_action': 'string'
}

STREAMING_INFO = {
    'bootstrap_servers': ['localhost:9092', 'localhost:9094']
    , 'topic_name': ['env_state_xx0', 'action_log_xx0']
    , 'consumer_group_id': 'AI_agent_xx0'
    , 'cols': ['place_id', 'temperature', 'humidity', 'salinity', 'ph', 'rain', 's_moist']
}

ENV_STATE = {
    'cols': ['id', 'place_id', 'temperature', 'humidity', 'salinity', 'ph', 'rain', 's_moist', 'created_at', 'updated_at']
}
METEO_API = {
    'cols_input': ['temperature_2m', 'relative_humidity_2m', 'rain', 'evapotranspiration', 'wind_speed_10m']
    , 'cols_input_': ['temperature', 'humidity', 'rain']
    , 'cols_output': ['id', 'place_id', 'temperature', 'humidity', 'salinity', 'ph', 'rain', 's_moist', 'created_at', 'updated_at']
}

TRAIN_COLUMNS = {
    'pH': ['normalized_id']
    , 'salinity': ['normalized_id']
    , 's_moist': ['normalized_id', 'temperature', 'humidity']
}

class State_Processor:
    def __init__(self, state_consumer:StateConsumer=None, db_utils:DatabaseInteractor=None, meteo_api:MeteoAPI=None):
        self.meteo_api = meteo_api
        self.state_consumer = state_consumer
        self.db_utils = db_utils
        self.streaming_mode = False
        self.state_arr = []

    # HELPER FUNCTIONS
    def check_json_data_null(self, json_data:dict):
        keys = []
        for key, value in json_data.items():
            if value is None:
                keys.append(key)
        keys.append([x for x in json_data.keys() if x not in ENV_STATE['cols']])
        
        return keys

    def check_data_row_num(self, db_utils:DatabaseInteractor=None, timestamp=None, row_num:int=1000):
        try:
            
            timestamp_id = int(timestamp.strftime('%Y%m%d%H%M%S'))
            
            query = f"""
                with cte as (
                    select
                        *
                        , row_number() over(order by id desc) as row_num
                    from public.state
                    where id <= {timestamp_id}
                )
                select * as number_of_rows
                from cte
                where row_num <= {row_num}
            """
            
            df = self.db_utils.read_table(
                schema='public'
                , table_name='state'
                , query=query
            )
            return df, df.shape[0]
        
        except Exception as e:
            logging.error(f'[ERROR] query_data_from_db(): {e}')
            return None

    def evaluate_model(self, model, X_test, y_test):
        try:
            y_pred = model.predict(X_test)
            mse = mean_squared_error(y_test, y_pred)
            r2 = r2_score(y_test, y_pred)
            if r2 >= 0.75:
                return True
            
            return False   
        
        except Exception as e:
            logging.error(f'[ERROR] evaluate_model(): {e}')
            return None

    def return_next_state(self, input_df:pd.DataFrame=None):
        try:
            X = input_df[x_attributes].values
            y = input_df[missing_attributes].values
            X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.1, random_state=42)
            
            scaler = StandardScaler()
            X_train_scaled = scaler.fit_transform(X_train)
            X_test_scaled = scaler.transform(X_test)

            model = LinearRegression()
            model.fit(X_train_scaled, y_train)

            if not evaluate_model(model, X_test_scaled, y_test):
                return False, -1
            
            y_pred = model.predict(x_data)
            return True, y_pred
        
        except Exception as e:
            logging.error(f'[ERROR] init_model(): {e}')
            return None

    # FUNTIONALITY
    def prepocessing_data(self, json_data:dict, meteo_api:MeteoAPI=None, db_utils:DatabaseInteractor=None):
        try:
            current_dt = dt.now() + timedelta(hours=7)
            json_data['id'] = int(current_dt.strftime('%Y%m%d%H%M%S'))
            json_data['created_at'] = str(current_dt)
            json_data['updated_at'] = str(current_dt)
            
            keys = self.check_json_data_null(json_data)
            keys_str = ','.join(keys)
            
            if len(keys) == 0:
                json_data['intervention'] = 0
                json_data['intervention_time'] = None
                json_data['intervention_action'] = None
                return json_data
            
            json_data['intervention'] = len(keys)
            json_data['intervention_time'] = current_dt
            json_data['intervention_action'] = keys_str
            
            json_data = self.fill_data_API(json_data, meteo_api)
            
            if len(check_json_data_null(json_data)) == 0:
                return json_data
            
            df, row_num = check_data_row_num(
                db_utils=db_utils
                , timestamp=current_dt
                , row_num=1000
            )
            
            if row_num < 10:
                json_data = self.fill_data_random(json_data)
            elif row_num < 100:
                json_data = self.fill_data_avg(json_data, df)
            else:
                json_data = self.fill_data_AI(json_data, df)
            
            
        except Exception as e:
            logging.error(f'[ERROR] prepocessing_data(): {e}')
            return None

    def fill_data_API(self, json_data:dict, meteo_api:MeteoAPI=None, keys:list=[]):
        try:
            if len(keys) == 0:
                for key, value in json_data.items(): 
                    if value is None:
                        keys.append(key)
                    
            keys_from_API = [x for x in keys if x in METEO_API['cols_input_']]
            
            df_1day = self.meteo_api.getWeatherState(
                state=METEO_API['cols_input']
                , lat=10.823
                , lon=106.6296
                , timezone='Asia/Bangkok'
                , forecast_days=1
            )
            
            created_at = pd.Timestamp(json_data['created_at'], tz='Asia/Bangkok')
            nearest_row = df_1day.iloc[(df_1day['date'] - created_at).abs().idxmin()]
            # nearest_idx = (df_1day['date'] - created_at).abs().idxmin()
            # nearest_temperature = df_1day.loc[nearest_idx, 'temperature']

            for key in keys_from_API:
                json_data[key] = float(nearest_row[key])
            
            return json_data
        
        except Exception as e:
            logging.error(f'[ERROR] fill_API(): {e}')
            return None

    def fill_data_random(json_data:dict):
        try:
            for key, value in json_data.items():
                if value is None:
                    if key == 'salinity':
                        json_data[key] = random.uniform(0.0, 35.0)
                    elif key == 'ph':
                        json_data[key] = random.uniform(6.5, 8.5)
                    elif key == 's_moist':
                        json_data[key] = random.uniform(0.0, 100.0)
            return json_data
            
        except Exception as e:
            logging.error(f'[ERROR] fill_data_random(): {e}')
            return None

    def fill_data_avg(json_data:dict, df:pd.DataFrame=None, keys:list=None):
        try:
            if df is None:
                raise ValueError("Dataframe is None")
            
            if keys is None:
                keys = json_data.keys()
            
            for key in keys:
                if json_data[key] is None:
                    json_data[key] = df[key].mean()
            return json_data
            
        except Exception as e:
            logging.error(f'[ERROR] fill_data_avg(): {e}')
            return None

    def fill_data_AI(json_data:dict, df:pd.DataFrame=None, keys:list=None):
        try:
            if df is None:
                raise ValueError("Dataframe is None")
            if keys is None:
                keys = json_data.keys()
            
            
            df['normalized_id'] = df['id'] - df['id'].min()
            for key in keys:
                if key == 's_moist':
                    isSuccess, res = self.return_next_state(df=df, input_col=TRAIN_COLUMNS[key], output_col=key)
                    if isSuccess:
                        json_data[key] = res
                    else:
                        json_data[key] = df[key].mean()
                else:
                    json_data[key] = df[key].mean()
            return json_data        
            
        except Exception as e:
            logging.error(f'[ERROR] fill_data_AI(): {e}')
            return None
        
    def write_dataframe_to_db(json_data:dict, table_name:str, db_utils:DatabaseInteractor=None):
        try:
            self.db_utils.write_dataframe(pd.DataFrame([json_data]), 'state')
            
        except Exception as e:
            logging.error(f'[ERROR] write_dataframe_to_db(): {e}')
            return None

    def main_flow(self, streaming_mode=False):
        try:
            state_arr = []
            
            for message in state_consumer.consumer:
                # print(f'{message.key}: {message.value}')
                json_data = self.prepocessing_data(json.loads(message.value), meteo_api=meteo_api)
                # print(json_data)
                print(pd.DataFrame([json_data]))
                
                if not streaming_mode:
                    self.write_dataframe_to_db(json_data=json_data)
                          
        except Exception as e:
            logging.error(f'[ERROR] main_flow(): {e}')
            return None


if __name__ == '__main__':
    db_utils = DatabaseInteractor(
        host=os.getenv('POSTGRES_HOST')
        , port=os.getenv('POSTGRES_PORT')
        , db_name='sis'
        , user=os.getenv('POSTGRES_USER')
        , password=os.getenv('POSTGRES_PASSWORD')
    )
    
    meteo_api = MeteoAPI(
        lat=10.823
        , lon=106.6296
        , timezone='Asia/Bangkok'
        , forecast_days=1
        , meteo_state=['temperature_2m', 'relative_humidity_2m', 'rain', 'evapotranspiration', 'wind_speed_10m']
    )
    
    state_consumer = StateConsumer(
        bootstrap_servers=["localhost:9092", "localhost:9094"]
        , topic_name='env_state_xx0'
        , consumer_group_id='AI_agent_xx0'
    )
    
    
    
    state_processor = State_Processor(
        state_consumer=state_consumer
        , db_utils=db_utils
        , meteo_api=meteo_api
    )
    state_processor.main_flow(streaming_mode=False)
    
    