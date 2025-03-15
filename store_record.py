import csv
import json
import logging
import requests
import openmeteo_requests
import requests_cache
import pandas as pd
from retry_requests import retry
from kafka import KafkaConsumer
from datetime import datetime as dt
from sqlalchemy import create_engine
from dotenv import load_dotenv
from sqlalchemy import inspect
import os

from utils.db_utils import DatabaseInteractor
from utils.streaming_utils import StateConsumer


DF_COLUMNS = {
    'id': 'bigint'
    , 'temperature': 'float'
    , 'humidity': 'float'
    , 'pH': 'float'
    , 'rain': 'float'
    , 's_moist': 'float'
    , 'created_at': 'datetime'
}


def prepocessing_data(json_data:dict):
    try:
        current_dt = dt.now()
        id = int(current_dt.strftime("%Y%m%d%H%M%S"))
        
        json_data['id'] = id
        json_data['created_at'] = current_dt
    except Exception as e:
        logging.error(f'ERROR - prepocessing_data(): {e}')
        return None


def main_flow(db_utils:DatabaseInteractor=None, state_consumer:StateConsumer=None, streaming_mode=False):
    try:
        state_arr = []
        
        for message in state_consumer.consumer:
            print(f'{message.key}: {message.value}')
            
            json_data = json.loads(message.value)
            
            
            if not streaming_mode:
                db_utils.write_dataframe(pd.DataFrame([json_data]), 'env_state')
                
            else:
                state_arr.append(json_data)
                
                if len(state_arr) >= 100:
                    state_consumer.df = pd.DataFrame(state_arr, columns=DF_COLUMNS.keys())
                    db_utils.write_dataframe(state_consumer.df, 'env_state')
                    state_arr = []
                
                
    except Exception as e:
        logging.error(f'ERROR - main_flow(): {e}')
        return None