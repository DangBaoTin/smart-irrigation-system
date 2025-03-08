# Code for me a class to consume from Kafka broker
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
import os
from sqlalchemy import inspect



# Setup PostgreSQL credentials
POSTGRES_HOST = os.getenv('POSTGRES_HOST')
POSTGRES_PORT = os.getenv('POSTGRES_PORT')
POSTGRES_USER = os.getenv('POSTGRES_USER')
POSTGRES_PASSWORD = os.getenv('POSTGRES_PASSWORD')
POSTGRES_DB = 'sis'
TABLE_LIST = ['env_state', 'place', 'action_log', 'train_data']

BOOTSTRAP_SERVERS = ["localhost:9092", "localhost:9094"]
TOPIC_NAMES = ['env_state_xx0']
CONSUMER_GROUP_ID = 'AI_agent_xx0'
DF_COLUMNS = ['id', 'temperature', 'humidity', 'rain', 'evapo', 'wind', 's_moist', 'created_at']



class DataWriter:
    def __init__(self, host='localhost', port=5432, db_name='mydb', user='postgres', password='password'):
        self.db_url = f'postgresql://{user}:{password}@{host}:{port}/{db_name}'
        
        self.engine = create_engine(self.db_url)
        self.inspector = inspect(self.engine)
        

    def check_schema_compatibility(self, df: pd.DataFrame, table_name: str, schema: str = 'public'):
        self.inspector = inspect(self.engine)

        if not self.inspector.has_table(table_name, schema=schema):
            print(f"Table {schema}.{table_name} does not exist. Proceeding to write data.")
            return True, 'table_not_exist'


        columns_info = self.inspector.get_columns(table_name, schema=schema)
        table_columns = {col['name']: col['type'] for col in columns_info}

        df_columns = {col: str(dtype) for col, dtype in df.dtypes.items()}

        missing_columns = [col for col in df_columns if col not in table_columns]
        extra_columns = [col for col in table_columns if col not in df_columns]

        if missing_columns:
            print(f"Warning: DataFrame contains columns not in table {schema}.{table_name}: {missing_columns}")
            return False, 'missing_columns'
        
        if extra_columns:
            print(f"Warning: Table {schema}.{table_name} contains columns not in DataFrame: {extra_columns}")
            return False, 'extra_columns'


        type_mismatches = {
            col: (df_columns[col], str(table_columns[col]))
            for col in df_columns if col in table_columns and df_columns[col] != str(table_columns[col])
        }

        if type_mismatches:
            print(f"Type mismatches found: {type_mismatches}")
            return False, 'type_mismatches'
        
        return True, 'compatible'
    
    
    def write_dataframe(self, df:pd.DataFrame, schema:str='public', table_name:str='', if_exists:str='append', index:bool=False):
        try:
            if not table_name:
                print("Table name is required.")
                return False
            
            # is_compatible, reason = self.check_schema_compatibility(df, table_name, schema)
            # if not is_compatible:
            #     print(f"Error writing DataFrame to PostgreSQL: Schema compatibility check failed. Reason: {reason}")
            #     return False
            
            
            df.to_sql(name=table_name, con=self.engine, schema=schema, if_exists=if_exists, index=index, method='multi')
            print(f"Data written successfully to {table_name}")
            return True
            
        except Exception as e:
            print(f"Error writing DataFrame to PostgreSQL: {e}")
            return False
    
    def read_table(self, schema:str='public', table_name:str='', query:str=None):
        try:
            if not table_name:
                print("Table name is required.")
                return None
            
            if not self.inspector.has_table(table_name, schema=schema):
                print(f"Table {schema}.{table_name} does not exist.")
                return None
            
            if query is None:
                query = f"select * from {schema}.{table_name}"
            
            return pd.read_sql(query, self.engine)
        
        except Exception as e:
            print(f"Error reading data from table {schema}.{table_name}: {e}")
            return None
         


class WeatherConsumer:
    def __init__(self, topic_name, group_id, bootstrap_servers):
        self.bootstrap_servers = bootstrap_servers
        self.group_id = group_id
        self.topic_name = topic_name
        self.df = pd.DataFrame(columns=DF_COLUMNS)
        
        self.consumer = self.createConsumer()
        self.db_client = DataWriter(
            host=POSTGRES_HOST
            , port=POSTGRES_PORT
            , user=POSTGRES_USER
            , password=POSTGRES_PASSWORD
            , db_name=POSTGRES_DB
        )
        
    
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



me = DataWriter(
    host='localhost'
    , port=5432
    , db_name='sis'
    , user='admin'
    , password='admin1234'
)


# Add datatype to dataframe



data = {
    'id': pd.Series([1, 2], dtype='int'),
    'name': pd.Series(['John', 'Jane'], dtype='string'),
    'job': pd.Series(['Engineer', 'Data Scientist'], dtype='string')
}


df = pd.DataFrame(data)
print(df)

res = me.write_dataframe(df, schema='public', table_name='test', if_exists='append', index=False)
print(res)
if res:
    df = me.read_table(schema='public', table_name='test')
    print(df)
else:
    print("Error writing data to table")


# if __name__ == "__main__":
#     consumer = WeatherConsumer(
#         bootstrap_servers=BOOTSTRAP_SERVERS,
#         group_id=CONSUMER_GROUP_ID,
#         topic_name=TOPIC_NAMES[0]
#     )
#     consumer.consume_data()
