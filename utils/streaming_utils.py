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


BOOTSTRAP_SERVERS = ['localhost:9092', 'localhost:9094']
TOPIC_NAMES = ['state_xx0', 'log_data_xx0']
STREAMING_INFO = {
    'bootstrap_servers': ['localhost:9092', 'localhost:9094']
    , 'topic_name': ['state_xx0', 'log_data_xx0']
    , 'consumer_group_id': ['AI_agent_xx0']
}
DF_COLUMNS = ['id', 'temperature', 'humidity', 'rain', 'evapo', 'wind', 's_moist', 'created_at']


class StateConsumer:
    def __init__(self, bootstrap_servers, topic_name, consumer_group_id):
        self.bootstrap_servers = bootstrap_servers
        self.group_id = consumer_group_id
        self.topic_name = topic_name
        self.df = None
        
        self.consumer = self.createConsumer()
    
    def createConsumer(self):
        return KafkaConsumer(
            self.topic_name,
            bootstrap_servers=self.bootstrap_servers,
            auto_offset_reset='earliest',
            # enable_auto_commit=True,
            enable_auto_commit=False,
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
                    self.db_client.write_dataframe(self.df, 'state')
                    self.df = pd.DataFrame(columns=DF_COLUMNS)
                
        except Exception as e:
            logging.error(f'[ERROR] consume_data(): {e}')
            return None


class Producer:
    def __init__(self, bootstrap_servers, topic_name):
        self.bootstrap_servers = bootstrap_servers
        self.topic_name = topic_name
        self.producer = self.createProducer()
        
    def createProducer(self):
        return KafkaProducer(
            bootstrap_servers=self.bootstrap_servers,
            key_serializer=lambda k: k.encode('utf-8'),
            value_serializer=lambda v: json.dumps(v).encode('utf-8')
        )
    
    def get_key(self, records):
        return int(str(records['id'])[9:15]) % 3
    
    def send_data(self, json_record):
        try:
            self.producer.send(self.topic_name, key=self.get_key(json_record), value=json_record)
            self.producer.flush()
        except Exception as e:
            logging.error(f'[ERROR] send_data(): {e}')
            return None

