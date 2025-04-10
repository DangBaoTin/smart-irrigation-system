import pandas as pd
import json
import numpy as np
from datetime import datetime as datetime, timedelta
import sys, os
import random
import math

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from utils.api_utils import MeteoAPI


class DataGenerator:
    def __init__(self, meteo_api_args=None):
        self.state_df = None
        self.state_df = {
            'columns': ['id', 'temperature', 'humidity', 'rain', 'salinity', 'ph', 'soil_moisture'],
        }
        self.meteo_api_args = meteo_api_args     
    
    def init_open_meteo(self, days):
        if self.meteo_api_args is None:
            raise ValueError("Meteo API arguments must be provided.")
        
        today = datetime.now().date()
        start_date = today - timedelta(days=2)
        end_date = today + timedelta(days=days)
        start_date_str = start_date.strftime("%Y-%m-%d")
        end_date_str = end_date.strftime("%Y-%m-%d")
        
        return MeteoAPI(
            lat=self.meteo_api_args.get('lat', 10.823),
            lon=self.meteo_api_args.get('lon', 106.6296),
            timezone=self.meteo_api_args.get('timezone', 'Asia/Bangkok'),
            start_date=start_date_str,
	        end_date=end_date_str,
            meteo_state=self.meteo_api_args.get('meteo_state', [])
        )
    
    def generate_state(self, days=0, interval=5):
        self.meteo_api = self.init_open_meteo(days)
        
        state_df = self.meteo_api.getWeatherState()
        
        if interval > 60:
            interval = 60
            print(f"Interval maximum value is 60 minutes.")
        if interval < 1:
            interval = 1
            print(f"Interval minimum value is 1 minute.")
        
        # print(state_df.columns)
        rows = []
        
        for _, row in state_df.iterrows():
            base_time = row['date']
            for i in range(math.floor(60 / interval)):
                new_time = base_time + pd.Timedelta(minutes=interval * i)
                new_row = row.copy()
                new_row['date'] = new_time
                new_row['id'] = new_time.strftime('%Y%m%d%H%M%S')
                new_row['salinity'] = round(random.uniform(19, 21), 1)
                new_row['ph'] = round(random.uniform(5.5, 6.5), 1)
                new_row['soil_moisture'] = round(random.uniform(25, 30), 1)
                
                rows.append(new_row.to_dict())

        new_df = pd.DataFrame(rows).reset_index(drop=True)
        
        self.state_df = new_df[self.state_df['columns']]
        return self.state_df
        
    def write_df(self, opath):
        self.state_df.to_csv('../data/env_state.csv', index=False)
    

class DataGetter:
    def __init__(self, csv_path=None):
        self.csv_path = csv_path

    def get_data(self, combine_num = 1):
        if self.csv_path is None:
            raise ValueError("CSV path must be provided.")
        
        df = pd.read_csv(self.csv_path)
        self.df = df
        
        if combine_num > 1:
            df = self.combine_rows(df, combine_num)
        else:
            df = df.sort_values('id', ascending=False).reset_index(drop=True)

        return df
    
    def combine_rows(self, df, n):
        df_sorted = df.sort_values('id', ascending=False).reset_index(drop=True)
        cols = df.columns
        combined_data = []

        for i in range(len(df_sorted) - n + 1):
            chunk = df_sorted.iloc[i:i + n].reset_index(drop=True)
            combined_row = {}

            combined_row['id'] = chunk.loc[0, 'id']

            for col in cols:
                if col == 'id':
                    continue
                for j in range(n):
                    combined_row[f"{col}{j}"] = chunk.loc[j, col]

            combined_data.append(combined_row)

        return pd.DataFrame(combined_data)
    
    
if __name__ == "__main__":
    # Example usage
    meteo_api_args = {
        'lat': 10.823
        , 'lon': 106.6296
        , 'timezone': 'Asia/Bangkok'
        , 'meteo_state': ['temperature_2m', 'relative_humidity_2m', 'rain', 'evapotranspiration', 'wind_speed_10m']
    }
    data_gen = DataGenerator(meteo_api_args)
    
    days = 120       # days
    interval = 1    # minutes
    # print(data_gen.generate_state(days, interval))
    
    # Change the file name to your desired output path
    # data_gen.write_df('../data/env_state.csv')
    
    data_getter = DataGetter(csv_path='/mnt/d/_ACADEMIC/HCMUT/Term242/Project_Smart_Irrigation/code_/smart-irrigation-system/data/env_state.csv')
    print(data_getter.get_data(combine_num=2))