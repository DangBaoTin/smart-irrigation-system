import csv
import json
import logging
import requests
import openmeteo_requests
import requests_cache
import pandas as pd
import numpy as np
import json
from retry_requests import retry
from kafka import KafkaConsumer
from datetime import datetime as dt
from sqlalchemy import create_engine, inspect
from dotenv import load_dotenv
import os



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

class DatabaseInteractor:
    def __init__(self, host='localhost', port=5432, db_name=None, user=None, password=None):
        if not db_name: raise ValueError("Database name is required.")
        if not user: raise ValueError("Database user is required.")
        if not password: raise ValueError("Database password is required.")
        
        self.host = host
        self.port = port
        self.db_name = db_name
        self.user = user
        self.password = password
        
        self.db_url = f'postgresql://{user}:{password}@{host}:{port}/{db_name}'
        self.engine = create_engine(self.db_url)
        self.inspector = inspect(self.engine)
    
    
    def isExisted(self, schema='public', table_name=None):
        if not table_name: raise ValueError("[ERROR] Table name is required.")
        
        if self.inspector.has_table(table_name, schema=schema): 
            return True
        else: 
            return False
    
    def create_table_if_not_exists(self, df: pd.DataFrame, table_name: str, schema: str, conn):
        if not self.table_exists(table_name, schema):
            df.head(0).to_sql(name=table_name, con=conn, schema=schema, if_exists='fail', index=False)
            print(f"Table '{schema}.{table_name}' created successfully.")
    
    def check_schema_compatibility(self, df: pd.DataFrame, table_name: str, schema: str = 'public'):
        try:
            if not self.isExisted(schema=schema, table_name=table_name):
                print(f"Table {schema}.{table_name} does not exist. Proceeding to write data.")
                return True, 'table_not_exist'

            columns_info = self.inspector.get_columns(table_name, schema=schema)
            table_columns = {col['name']: col['type'] for col in columns_info}

            df_columns = {col: str(dtype) for col, dtype in df.dtypes.items()}

            missing_columns = [col for col in df_columns if col not in table_columns]
            extra_columns = [col for col in table_columns if col not in df_columns]

            if missing_columns:
                print(f"[ERROR] DataFrame contains columns not in table {schema}.{table_name}: {missing_columns}")
                return False, 'missing_columns'
            
            if extra_columns:
                print(f"[ERROR]] Table {schema}.{table_name} contains columns not in DataFrame: {extra_columns}")
                return False, 'extra_columns'


            # there are some cases that the column type is not matched but still acceptable: varchar and string, int and int64,...
            for col in df_columns:
                if col in table_columns and df_columns[col] != str(table_columns[col]):
                    if 'varchar' in str(table_columns[col]).lower() ==  and df_columns[col] == 'string':
                        continue
                    if str(table_columns[col]).lower() == 'int' and df_columns[col] == 'int64':
                        continue
                    if str(table_columns[col]).lower() == 'float' and df_columns[col] == 'float64':
                        continue
                    if str(table_columns[col]).lower() == 'timestamp' and df_columns[col] == 'datetime64[ns]':
                        continue
                    print(f"[ERROR] Type mismatches found: {col} - {df_columns[col]} - {str(table_columns[col])}")
                    return False, 'type_mismatches'
        
            return True, 'compatible'
        
        
        
        except Exception as e:
            print(f"[ERROR] {e}")
            return False, 'exception'
    
    def write_dataframe(self, df: pd.DataFrame, table_name:str, schema:str='public', create_if_not_exist:bool=False, method:str='insert', key_columns:list=None):
        if not table_name:
            raise ValueError("Table name is required.")
        
        if not self.isExisted(schema=schema, table_name=table_name):
            if create_if_not_exist:
                with self.engine.begin() as conn:
                    self.create_table_if_not_exists(df, table_name, schema, conn)
            else:
                print(f"[ERROR] Table {schema}.{table_name} does not exist.")
                return False
            
        if method not in ['insert', 'update', 'overwrite', 'upsert']:
            raise ValueError("Invalid method. Choose from 'insert', 'update', 'overwrite', 'upsert'.")

        with self.engine.begin() as conn:
            if method == 'overwrite':
                self.overwrite_table(df, table_name, schema, conn)
                
            elif method == 'insert':
                df.to_sql(name=table_name, con=conn, schema=schema, if_exists='append', index=False, method='multi')
                
            elif method == 'update':
                if not key_columns:
                    raise ValueError("For 'update', you must specify key_columns.")
                self.update_table(df, table_name, schema, key_columns, conn)
                
            elif method == 'upsert':
                if not key_columns:
                    raise ValueError("For 'upsert', you must specify key_columns.")
                self.upsert_table(df, table_name, schema, key_columns, conn)

            print(f"Data written successfully using method: {method}")

    def overwrite_table(self, df, table_name, schema, conn):
        try:
            conn.execute(text(f'drop table if exists {schema}.{table_name} cascade'))
            df.to_sql(name=table_name, con=conn, schema=schema, if_exists='replace', index=False, method='multi')
            return True
        except Exception as e:
            print(f"[ERROR] {e}")
            return False

    def update_table(self, df, table_name, schema, key_columns, conn):
        try:
            for _, row in df.iterrows():
                set_clause = ', '.join(f"{col} = '{row[col]}'" for col in df.columns if col not in key_columns)
                where_clause = ' and '.join(f"{col} = '{row[col]}'" for col in key_columns)
                sql = f"update {schema}.{table_name} set {set_clause} where {where_clause}"
                conn.execute(text(sql))
            return True
        except Exception as e:
            print(f"[ERROR] {e}")
            return False

    def upsert_table(self, df, table_name, schema, key_columns, conn):
        try:
            columns = ', '.join(df.columns)
            update_clause = ', '.join(f"{col} = excluded.{col}" for col in df.columns if col not in key_columns)
            
            for _, row in df.iterrows():
                values = ', '.join(f"'{row[col]}'" for col in df.columns)
                sql = f"""
                    insert into {schema}.{table_name} ({columns})
                    values ({values})
                    on conflict ({', '.join(key_columns)}) 
                    do update set {update_clause}
                """
                conn.execute(text(sql))
            return True
        except Exception as e:
            print(f"[ERROR] {e}")
            return False

    def read_table(self, schema:str='public', table_name:str='', query:str=None):
        if not table_name:
            raise ValueError("Table name is required.")
        
        if not self.isExisted(schema=schema, table_name=table_name):
            print(f"[ERROR] Table {schema}.{table_name} does not exist.")
            return None
        
        if query is None:
            query = f"select * from {schema}.{table_name}"
        return pd.read_sql(query, self.engine)
        
        except Exception as e:
            print(f"Error reading data from table {schema}.{table_name}: {e}")
            return None
            
    def read_latest_record(self, time_column:str, conditions:list(str), schema:str='public', table_name:str=''):
        if not table_name:
            raise ValueError("Table name is required.")
        
        if not self.isExisted(schema=schema, table_name=table_name):
            print(f"[ERROR] Table {schema}.{table_name} does not exist.")
            return None
        
        query = f"select * from {schema}.{table_name}"
        if len(conditions) > 0:
            query += 'where 1 = 1'
            query += ' and '.join(conditions)
        
        query += f'order by {time_column} desc limit 1'
        return pd.read_table(schema=schema, table_name=table_name, query=query)
        
        except Exception as e:
            print(f"Error reading data from table {schema}.{table_name}: {e}")
            return None
    
    
    
    