import pandas as pd
import json
import numpy as np
from datetime import datetime as dt, timedelta
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
        
        if days <= 60: 
            past_days = days
            forecast_days = 0
        else:
            past_days = 60
            forecast_days = days - 60
        
        return MeteoAPI(
            lat=self.meteo_api_args.get('lat', 10.823),
            lon=self.meteo_api_args.get('lon', 106.6296),
            timezone=self.meteo_api_args.get('timezone', 'Asia/Bangkok'),
            past_days=past_days,
            forecast_days=forecast_days,
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
        # print(new_df[self.state_df['columns']])
        
    def write_df(self, opath):
        self.state_df.to_csv('./data/env_state.csv', index=False)
    
    
    
    
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
    data_gen.generate_state(days, interval)
    data_gen.write_df('../data/env_state.csv')