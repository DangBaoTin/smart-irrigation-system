from kafka import KafkaConsumer
from datetime import datetime, timedelta
# import keras
from utils import *
import numpy as np
import pandas as pd
import json
from utils.api_utils import MeteoAPI
from utils.db_utils import DatabaseInteractor
from utils.streaming_utils import StateConsumer, Producer
import random
import os
from dotenv import load_dotenv



ENV_STATE = {
    'cols': ['id', 'place_id', 'temperature', 'humidity', 'salinity', 'ph', 'rain', 's_moist', 'created_at', 'updated_at'],
}
METEO_API = {
    'cols_input': ['temperature_2m', 'relative_humidity_2m', 'rain', 'evapotranspiration', 'wind_speed_10m']
    , 'cols_output': ['id', 'place_id', 'temperature', 'humidity', 'salinity', 'ph', 'rain', 's_moist', 'created_at', 'updated_at']
}
ACTION_LOG = {
    'cols': ['id', 'place_id', 'neg_time', 'neg_tstep', 'pos_time', 'pos_tstep', 'action', 'reward', 'created_at', 'updated_at']
}

N_STATE = 1000

STREAMING_INFO = {
    'bootstrap_servers': ['localhost:9092', 'localhost:9094']
    , 'topic_name': ['env_state_xx0', 'action_log_xx0']
    , 'consumer_group_id': 'AI_agent_xx0'
}




def generate_timestamp(start_date, num_samples):
    start = datetime.strptime(str(start_date), "%Y%m%d%H%M%S")
    timestamps = [
        int((start + timedelta(seconds=random.randint(0, 86400))).strftime("%Y%m%d%H%M%S"))
        for _ in range(num_samples)
    ]
    return timestamps

num_rows = 2 
now_time = datetime.now()
now_time = int(datetime.strftime(now_time, "%Y%m%d%H%M%S"))
# _DF = pd.DataFrame({
#     'id': generate_timestamp(now_time, num_rows), 
#     'place_id': [1 for _ in range(num_rows)],
#     'temperature': [random.uniform(20, 35) for _ in range(num_rows)], 
#     'humidity': [random.uniform(40, 80) for _ in range(num_rows)], 
#     'salinity': [random.uniform(0, 40) for _ in range(num_rows)], 
#     'ph': [random.uniform(6, 8) for _ in range(num_rows)],
#     'rain': [random.uniform(0, 50) for _ in range(num_rows)], 
#     's_moist': [random.uniform(10, 50) for _ in range(num_rows)],
#     'created_at': [datetime.now() for _ in range(num_rows)],
#     'updated_at': [datetime.now() for _ in range(num_rows)],
#     'requested_at': [datetime.now() for _ in range(num_rows)]
# })

# _DF['id'] = _DF['id'].astype(int)
# _DF.loc[0, ['temperature', 'humidity', 's_moist']] = np.nan


class VirtuaEnv:
    def __init__(
            self
            , meteo_api:MeteoAPI=None
            , db_utils:DatabaseInteractor=None
            , log_producer:Producer=None
        ):
        
        self.irrigation_map = {0: 0, 1: 5, 2: 10, 3: 15, 4: 20, 5: 25}
        self.api_utils = meteo_api
        self.db_utils = db_utils
        self.log_producer = log_producer
        self.place_id = 1

    def get_n_state_before(self, n, mark_time=None, mark_id=None, duration=None, cols=[]):
        # duration: {days, hours, minutes, seconds}
        
        current_time = datetime.now()
        
        if mark_id is None:
            if mart_time is None:
                mark_time = current_time
            mark_time = int(datetime.strftime(mark_time, "%Y%m%d%H%M%S"))
        else:
            mark_time = mark_id
        cols_query = ', '.join(cols) if len(cols) > 0 else '*'
        
        if not duration:
            query = f"""
                with cte as (
                    select
                        {cols_query}
                        , row_number() over (order by id desc) as row_num
                    from env_state
                    where id <= {timestamp_id}
                )
                select * from cte where row_num <= {n}
            """
        else:
            duration = timedelta(
                days=duration.get('days', 0),
                hours=duration.get('hours', 0),
                minutes=duration.get('minutes', 0),
                seconds=duration.get('seconds', 0)
            )
            start_time_id = int((timestamp - duration).timestamp())
            
            
            query = f"""
                with cte as (
                    select
                        {cols_query}
                        , row_number() over (order by id desc) as row_num
                    from state
                    where id <= {timestamp_id} and id >= {start_time_id} 
                )
                select * from cte where row_num <= {n}
            """
            
        df = self.db_utils.read_table(table_name='state', query=query)
        df = df[ENV_STATE['cols']] if (len(cols) == 0) else df[['id'] + cols]
        df = df.sort_values(by="id", ascending=False).head(n)
        df = df[cols]
        
        if len(df) == 0:
            print(f'[ERROR] get_n_state_before(): No data found')
            return False, None
        elif len(df) < n:
            return False, df
        elif len(df) == n: 
            return True, df
        elif len(df) > n:
            return False, None

    def get_latest_state(self, mark_time=None, mark_id=None, cols=[]):
        retries = 0
        isSuccess = False
        current_time = datetime.now()
        
        if mark_id is None:
            if mart_time is None:
                mark_time = current_time
            mark_time = int(datetime.strftime(mark_time, "%Y%m%d%H%M%S"))
        else:
            mark_time = mark_id
        
        cols = ', '.join(ENV_STATE['cols']) if len(cols) > 0 else '*'
        
        query = f"""
            select 
                {cols}
            from state
            where 
                id <= {mark_time}
                and place_id = {self.place_id}
            order by id desc
            limit 1
        """
        
        while (retries < 5) and (not isSuccess):
            state_df = self.db_utils.read_table(table_name='state', query=query)

            if (state_df is not None) and (len(state_df) > 0):
                current_time = datetime.now()
                state_time = datetime.strptime(str(state_df['id'])[:-2], '%Y%m%d%H%M%S')
                
                if (current_time - state_time).total_seconds() > 5*60: # 5 minutes
                    isSuccess = True
                pass
            
            retries += 1
       
        if not isSuccess:
        #    return self.predict_next_state()
            pass
    
    def get_n_log_before(self, n, mark_time=None, mark_id=None, duration=None, cols=[]):
        # duration: {days, hours, minutes, seconds}

        # return  _DF # ...
        
        current_time = datetime.now()
        
        if mark_id is None:
            if mart_time is None:
                mark_time = current_time
            mark_time = int(datetime.strftime(mark_time, "%Y%m%d%H%M%S"))
        else:
            mark_time = mark_id
        cols_query = ', '.join(cols) if len(cols) > 0 else '*'
        
        if not duration:
            query = f"""
                with cte as (
                    select
                        {cols_query}
                        , row_number() over (order by id desc) as row_num
                    from env_log
                    where id <= {timestamp_id}
                )
                select * from cte where row_num <= {n}
            """
        else:
            duration = timedelta(
                days=duration.get('days', 0),
                hours=duration.get('hours', 0),
                minutes=duration.get('minutes', 0),
                seconds=duration.get('seconds', 0)
            )
            start_time_id = int((timestamp - duration).timestamp())
            
            
            query = f"""
                with cte as (
                    select
                        {cols_query}
                        , row_number() over (order by id desc) as row_num
                    from log
                    where id <= {timestamp_id} and id >= {start_time_id} 
                )
                select * from cte where row_num <= {n}
            """
            
        df = db_utils.read_table(table_name='log', query=query)
        df = df[ENV_STATE['cols']] if (len(cols) == 0) else df[['id'] + cols]
        df = df.sort_values(by="id", ascending=False).head(n)
        df = df[cols]
        
        if len(df) == 0:
            print(f'[ERROR] get_n_log_before(): No data found')
            return False, None
        elif len(df) < n:
            return False, df
        elif len(df) == n: 
            return True, df
        elif len(df) > n:
            return False, None

    def get_latest_log(self, mark_time=None, mark_id=None, cols=[]):
        retries = 0
        isSuccess = False
        
        current_time = datetime.now()
        
        if mark_id is None:
            if mart_time is None:
                mark_time = current_time
            mark_time = int(datetime.strftime(mark_time, "%Y%m%d%H%M%S"))
        else:
            mark_time = mark_id
        cols = ', '.join(ENV_STATE['cols']) if len(cols) > 0 else '*'
        
        query = f"""
            select 
                {cols}
            from log_data
            where 
                id <= {mark_time}
                and place_id = {self.place_id}
            order by id desc
            limit 1
        """
        
        while (retries < 5) and (not isSuccess):
            log_df = self.db_utils.read_table(table_name='log_data', query=query)
            # print(str(log_df['id']))
            if (log_df is not None) and (len(log_df) > 0):
                current_time = datetime.now()
                log_time = datetime.strptime(str(log_df['id'])[:-2], '%Y%m%d%H%M%S')
                
                if (current_time - log_time).total_seconds() > 5*60: # 5 minutes
                    isSuccess = True
                pass
            
            retries += 1
       
        if not isSuccess:
        #    return self.predict_next_log()
            pass

    def score(self, state, action=None):
        # to_do ... <- Tin Dang
        pass
 
    def send_log(self, log:dict={}):
        try:
            if self.log_producer:
                if len([x for x in log.keys() if x not in ACTION_LOG['cols']]) > 0:
                    print(f'[ERROR] send_log(): Invalid log data')
                    return False
                
                for key in ACTION_LOG['cols']:
                    if key not in log:
                        state[key] = None
                    
                self.log_producer.send_data(state)
                return True
            else:
                print(f'[INFO] send_log(): No log producer available')
        except Exception as e:
            logging.error(f'[ERROR] send_log(): {e}')
            return False
       
    def get_API_data(self):
        try:
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
            keys_from_API = ['temperature', 'humidity', 'rain']
            for key in keys_from_API:
                json_data[key] = float(nearest_row[key])
            return json_data
        
        except Exception as e:
            logging.error(f'[ERROR] fill_API(): {e}')
            return None
    
    def get_input(self, n=1, mark_time=None, mark_id=None):
        current_time = datetime.now()
        if mark_time is None:
            mark_time = current_time
        
        if n == 1:
            isSuccess, state_df = self.get_latest_state(mark_time=mark_time, cols=ENV_STATE['cols'][2:-2])
            if not isSuccess:
                json_data = self.get_API_data()
                _, state_df = self.get_latest_state(mark_time=mark_time - timedelta(hours=24), cols=ENV_STATE['cols'][2:-2])
                for key in json_data.keys():
                    state_df[key] = json_data[key]
                    
            ordered_cols = sorted(state_df.columns)
            state_df = state_df[ordered_cols]
        
        else:
            isSuccess, state_df = self.get_n_state_before(n=n, mark_time=mark_time, cols=ENV_STATE['cols'][2:-2])
            if not isSuccess:
                json_data = self.get_API_data()
                _, state_df = self.get_n_state_before(n=n, mark_time=mark_time - timedelta(hours=24), cols=ENV_STATE['cols'][2:-2])
                for key in json_data.keys():
                    state_df[key] = json_data[key]
            # state_df = _DF[ENV_STATE['cols'][2:-2]]
            state_df = pd.DataFrame([state_df.values.flatten()], columns=[f"{col}{i}" for i in range(len(state_df)) for col in state_df.columns])

            ordered_cols = sorted(state_df.columns)
            state_df = state_df[ordered_cols]
            
        return state_df, state_df.columns



if __name__ == '__main__':
    # trained_model = 'model.h5'
    # steps = 5
    load_dotenv()
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
    
    log_producer = Producer(
        bootstrap_servers=STREAMING_INFO['bootstrap_servers']
        , topic_name=STREAMING_INFO['topic_name'][1]
    )
    
    
    db_utils = None
    meteo_api = None
    log_producer = None
    venv = VirtuaEnv(
        db_utils=db_utils
        , meteo_api=meteo_api
        , log_producer=log_producer
    )
    
    df, cols = venv.get_input(n=2)
    print(df)