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

DF_COLUMNS = ['id', 'temperature', 'humidity', 'rain', 'evapo', 'wind', 's_moist', 'created_at']




class WeatherProducer:
    def __init__(self, bootstrap_servers, topic_name, lat=None, lon=None, timezone=None, state=None, limit=None):
        self.bootstrap_servers = bootstrap_servers
        self.topic_name = topic_name
        self.lat = lat if lat else 10.823
        self.lon = lon if lon else 106.6296
        self.timezone = timezone
        self.state = state if state else ['temperature_2m', 'relative_humidity_2m', 'rain', 'evapotranspiration', 'wind_speed_10m']
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
            return df
        
        except Exception as exc:
            print(f'ERROR - getWeatherState(): {exc}')
            return None

    def transform_meteo_response(self, response):
        print(f'Coordinates {response.Latitude()}°N {response.Longitude()}°E')
        print(f'Elevation {response.Elevation()} m asl')
        print(f'Timezone {response.Timezone()} {response.TimezoneAbbreviation()}')

        hourly = response.Hourly()
        hourly_data = {
            'created_at': pd.date_range(
                start=pd.to_datetime(hourly.Time(), unit='s', utc=True).tz_convert(self.timezone),
                end=pd.to_datetime(hourly.TimeEnd(), unit='s', utc=True).tz_convert(self.timezone),
                freq=pd.Timedelta(seconds=hourly.Interval()),
                inclusive='left'
            )
        }
        
        hourly_data['id'] = [dt.strftime('%Y%m%d_%H%M%S') for dt in hourly_data['created_at']]
        hourly_data['temperature'] = hourly.Variables(0).ValuesAsNumpy()
        hourly_data['humidity'] = hourly.Variables(1).ValuesAsNumpy()
        hourly_data['rain'] = hourly.Variables(2).ValuesAsNumpy()
        hourly_data['evapo'] = hourly.Variables(3).ValuesAsNumpy()
        hourly_data['wind'] = hourly.Variables(4).ValuesAsNumpy()
        
        hourly_df = pd.DataFrame(hourly_data, columns=['id', 'temperature', 'humidity', 'rain', 'evapo', 'wind', 'created_at'])
        # print(hourly_df)
        return hourly_df

    def get_key(self, records, singleRecord=False):
        if singleRecord:
            return str(int(records[0]['id'][9:11]) % 3)
        else:
            pass

    # def stream_data(self):
    #     record_count = 0
    #     while True if (self.limit is None) else record_count < self.limit:
    #         try:
    #             data = self.get_weather_state()
    #             if data is not None:
    #                 key = self.get_key(data["id"].iloc[0])
    #                 self.producer.send(self.topic_name, key=key, value=json.dumps(data.to_dict()))
                    
    #                 record_count += 1
                    
    #         except Exception as exc:
    #             logging.error(f'ERROR - stream_data(): {exc}')
    #             continue

    #         print(f'{record_count} records sent to topic '{self.topic_name}' of Kafka successfully')

    def extract_data(self, data):
        current_time = dt.now().strftime('%Y-%m-%d %H:%M:%S')
        df = data.loc[data['date'] <= current_time]
        
        return df.loc[df['date'] == df['date'].max()]
    
    def send_data(self, mode='single'):
        try:
            data = self.extract_data(self.get_weather_state())
            data_json = json.loads(data.to_json(orient='records'))
            
            if mode == 'single':
                key = self.get_key(data_json[0], singleRecord=True)
                # print(data_json[0])
                
                # self.producer.send(self.topic_name, key=key, value=json.dumps(data_json[0]))
                # self.producer.flush()
                
                print(f'Record sent to topic <{self.topic_name}>')
            else:
                for rec in data_json:
                    key = self.get_key(rec)
                    # self.producer.send(self.topic_name, key=key, value=json.dumps(rec))
                    # self.producer.flush()
                    
                    print(f'Record sent to topic <{self.topic_name}>')
            
        except Exception as exc:
            logging.error(f'ERROR - send_data(): {exc}')
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
