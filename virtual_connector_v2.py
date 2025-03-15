from kafka import KafkaConsumer
from datetime import datetime, timedelta
import keras
from utils import *
import numpy as np
import json
from utils.db_utils import DatabaseInteractor

ENV_STATE = {
    'col': ['id', 'place_id', 'temperature', 'humidity', 'rain', 'evapo', 'wind', 's_moist', 'created_at', 'updated_at'],
}

class VirtuaEnv:
    def __init__(selfend_of_season, trained_model, steps):
        self.missing_data_count = 0

        self.model = keras.models.load_model(trained_model)
        
        self.latest_sensors = {
            'soil_moisture': None,
            'soil_temperature': None,
            'soil_salinity': None,
            'soil_ph': None
        }
        self.last_received_time = None
        self.buffer = []
        self.EoS = end_of_season
        self.irrigation_map = {0: 0, 1: 5, 2: 10, 3: 15, 4: 20, 5: 25}
        self.steps = steps
        self.score_buffer = []
        self.M_opt = 35.0
        self.db_utils = DatabaseInteractor(POSTGRES_HOST, POSTGRES_PORT, POSTGRES_DB, POSTGRES_USER, POSTGRES_PASSWORD)
    
    def get_n_state_before(self, n, duration, mark_time=None):
        # duration: {days, hours, minutes, seconds}

        if not mark_time:
            timestamp = datetime.now()
                
            
        timestamp_id = int(mark_time)
        duration = timedelta(
            days=duration.get('days', 0),
            hours=duration.get('hours', 0),
            minutes=duration.get('minutes', 0),
            seconds=duration.get('seconds', 0)
        )
        start_time = timestamp - duration
        start_time_id = int(start_time.timestamp())
        
        
        query = f"""
            with cte as (
                select
                    *
                    , row_number() over (order by id desc) as row_num
                from env_state
                where id >= {start_time_id} and id <= {timestamp_id}
            )
            select * from cte where row_num <= {n}
        """
        df = db_utils.read_table(table_name='env_state', query=query)
        df = df[ENV_STATE['col']]
        return df

    def get_latest_state(self):
        """Retrieve the latest values from different sensors and return a complete state."""
        # query the latest state from the database
        # if no data available, return None
        # if data available, return the state
        state = self.db_utils.read_latest_record('env_state')
        if not state:
            return None
        else:
            # check the state and the time of the state
            current_time = datetime.now()
            
            state_id = datetime.strptime(state['id'], "%Y%m%d%H%M%S")
            if current_time - state_id > 5*60: # 5 minutes
                return state
            else:
                return predict_next_state()
            
    def score(self, state, action=None):
        state = self.get_latest_state()
        if not action:
            self.score_buffer.append(state)
            return state
        else:
            self.score_buffer.append(state)
            score = 0
            for s in self.score_buffer:
                score += abs(s['soil_moisture'] - self.M_opt)
            self.score_buffer = [state]
            return score






    def predict_next_state(self):
        """Simple trend-based prediction using last known values."""
        pass

    def store_to_db(self, state, current_time):
        """Store the latest sensor state in SQL db"""
        # Transform state to dataframe
        state_df = pd.DataFrame(state, index=[0])
        state_df['created_at'] = current_time
        state_df['updated_at'] = current_time
        state_df = state_df[ENV_STATE['col']]
        
        self.db_utils.write_dataframe(
            df
            , table_name='env_state'
            , schema='public'
            , method:str='insert'
        ):
    
    def store_into_buffer(self, state, buffer):
        if len(buffer) < 1000:
            buffer.append(state)
        else:
            buffer.pop(0)
            buffer.append(state)
    
        
    
            
    def run(self):
        """Continuously fetch state, either from Kafka or via prediction."""
        while True:
            state, is_predicted = self.get_latest_state()
            if state:
                print("Using {} data: {}".format("Predicted" if is_predicted else "Real", state))
            else:
                print("No data available, stopping predictions.")
                break


