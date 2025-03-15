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

BOOTSTRAP_SERVERS = ["localhost:9092", "localhost:9094"]
TOPIC_NAMES = ['env_state_xx0']
CONSUMER_GROUP_ID = 'AI_agent_xx0'
DF_COLUMNS = ['id', 'temperature', 'humidity', 'rain', 'evapo', 'wind', 's_moist', 'created_at']

class StateConsumer:
    def __init__(self, topic_name, group_id, bootstrap_servers):
        self.bootstrap_servers = bootstrap_servers
        self.group_id = group_id
        self.topic_name = topic_name
        self.df = None
        
        self.consumer = self.createConsumer()
    
    def createConsumer(self):
        return KafkaConsumer(
            self.topic_name,
            bootstrap_servers=self.bootstrap_servers,
            auto_offset_reset='earliest',
            enable_auto_commit=True,
            group_id=self.group_id,
            key_deserializer=lambda k: k.decode('utf-8'),
            value_deserializer=lambda v: v.decode('utf-8')
        )
        
    def consume_data(self):
        try:
            for message in self.consumer:
                print(f'{message.key}: {message.value}')
                
                self.df = self.df.append(json.loads(message.value), ignore_index=True)
                if len(self.df) >= 10:
                    self.db_client.write_dataframe(self.df, 'env_state')
                    self.df = pd.DataFrame(columns=DF_COLUMNS)
                
        except Exception as exc:
            logging.error(f'ERROR - consume_data(): {exc}')
            return None