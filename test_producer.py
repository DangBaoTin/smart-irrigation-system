import csv
import json
import logging
import requests
import openmeteo_requests
import requests_cache
import pandas as pd
from retry_requests import retry
from kafka import KafkaProducer
from datetime import datetime as dt


# SETUP CONSTANTS
BOOTSTRAP_SERVERS = ["localhost:9092", "localhost:9094"]
TOPIC_NAMES = ['env_state_xx0']

TIMEZONE = 'Asia/Bangkok'
STATE = ['temperature_2m', 'relative_humidity_2m', 'rain', 'evapotranspiration', 'wind_speed_10m']
LIMIT = None

# Ho Chi Minh City
LAT = 10.823
LON = 106.6296

METEO_URL = "https://api.open-meteo.com/v1/forecast"

DF_COLUMNS = ['id', 'place_id', 'temperature', 'humidity', 'salinity', 'ph', 'rain', 's_moist', 'requested_at', 'created_at', 'updated_at']




class WeatherProducer:
    def __init__(self, bootstrap_servers, topic_name, lat=None, lon=None, timezone=None, state=None, limit=None):
        self.bootstrap_servers = bootstrap_servers
        self.topic_name = topic_name
        self.lat = lat if lat else 10.823
        self.lon = lon if lon else 106.6296
        self.timezone = timezone
        self.state = state if state else ['temperature_2m', 'relative_humidity_2m', 'rain']
        self.limit = limit
        self.forecast_days = 1
        
        self.producer = self.create_producer()
        
        # Setup API Client
        self.cache_session = requests_cache.CachedSession('.cache', expire_after=3600)
        self.retry_session = retry(self.cache_session, retries=5, backoff_factor=0.2)
        self.openmeteo = openmeteo_requests.Client(session=self.retry_session)

    def create_producer(self):
        return KafkaProducer(
            bootstrap_servers=self.bootstrap_servers,
            key_serializer=lambda key: key.encode('utf-8'),
            value_serializer=lambda value: value.encode('utf-8'),
        )

    def get_weather_state(self):
        params = {
            "latitude": self.lat,
            "longitude": self.lon,
            "hourly": self.state,
            "timezone": self.timezone,
            "forecast_days": self.forecast_days
        }
        
        try:
            responses = self.openmeteo.weather_api(METEO_URL, params=params)
            df = self.transform_meteo_response(responses[0])
            df['s_moist'] = 0
            df['salinity'] = 0
            df['ph'] = 0
            df['place_id'] = 1
            
            df = df[DF_COLUMNS[:-2]]
            return df
        
        except Exception as e:
            print(f'[ERROR] getWeatherState(): {e}')
            return None

    def transform_meteo_response(self, response):
        # print(f'Coordinates {response.Latitude()}°N {response.Longitude()}°E')
        # print(f'Elevation {response.Elevation()} m asl')
        # print(f'Timezone {response.Timezone()} {response.TimezoneAbbreviation()}')

        hourly = response.Hourly()
        hourly_data = {
            'time': pd.date_range(
                start=pd.to_datetime(hourly.Time(), unit='s', utc=True).tz_convert(self.timezone),
                end=pd.to_datetime(hourly.TimeEnd(), unit='s', utc=True).tz_convert(self.timezone),
                freq=pd.Timedelta(seconds=hourly.Interval()),
                inclusive='left'
            )
        }
        
        # hourly_data['id'] = [int(dt.strftime('%Y%m%d%H%M%S')) for dt in hourly_data['time']]
        hourly_data['requested_at'] = [dt.now().strftime('%Y-%m-%d %H:%M:%S') for x in hourly_data['time']]
        hourly_data['temperature'] = hourly.Variables(0).ValuesAsNumpy()
        hourly_data['humidity'] = hourly.Variables(1).ValuesAsNumpy()
        hourly_data['rain'] = hourly.Variables(2).ValuesAsNumpy()
        
        state_df = pd.DataFrame(hourly_data, columns=['id', 'temperature', 'humidity', 'rain', 'requested_at'])
        
        # print(state_df)
        return state_df

    def get_key(self, records, singleRecord=False):
        if singleRecord:
            # return str(int(str(records[0]['id'])[9:11]) % 3)
            return str(records['id'])
            # return int(str(records['id'])[9:15]) % 3
        else:
            pass

    def extract_data(self, data):
        current_time = int(dt.now().strftime('%Y%m%d%H%M%S'))
        if data is None:
            return None
        df = data.loc[data['id'] <= current_time]
        
        return df.loc[df['id'] == df['id'].max()]
    
    def send_data(self, mode='single'):
        try:
            df = self.get_weather_state()
            data = self.extract_data(df)
            # data['requested_at'] = data['requested_at'].astype(str)
            # print(f'data: {data}')
            
            data_json = json.loads(data.to_json(orient='records'))
            # print(f'data_json: {data_json}')
            if mode == 'single':
                key = self.get_key(data_json[0], singleRecord=True)
                # print(key)
                # print(data_json[0])
                
                
                self.producer.send(self.topic_name, key=json.dumps(key), value=json.dumps(data_json[0]))
                self.producer.flush()
                
                print(f'Record sent to topic <{self.topic_name}>')
            else:
                # for rec in data_json:
                #     key = self.get_key(rec)
                #     # self.producer.send(self.topic_name, key=key, value=json.dumps(rec))
                #     # self.producer.flush()
                    
                #     print(f'Record sent to topic <{self.topic_name}>')
                pass
            
        except Exception as e:
            print(f'[ERROR] send_data(): {e}')
            return None
        

if __name__ == "__main__":
    streamer = WeatherProducer(
        bootstrap_servers=BOOTSTRAP_SERVERS,
        topic_name=TOPIC_NAMES[0],
        lat=LAT,
        lon=LON,
        timezone=TIMEZONE,
        state=STATE,
        limit=LIMIT
    )
    streamer.send_data()
    # streamer.stream_data()
