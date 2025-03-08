import csv
import json
import logging
import requests
import openmeteo_requests
import requests_cache
import pandas as PD
from retry_requests import retry
from kafka import KafkaProducer




# SETUP FOR KAKFA
TOPIC_NAMES = ['env_state_xx0']
BOOTSTRAP_SERVERS = ["localhost:9092", "localhost:9094"]

limit = None
limit = 10

# SETUP FOR METEO API
lon = None
lat = None 

lat = 10.823
lon = 106.6296
timezone = 'Asia/Bangkok'
forecast_days = 1

state = ['temperature_2m', 'relative_humidity_2m', 'rain', 'evapotranspiration', 'wind_speed_10m']

# Setup the Open-Meteo API client with cache and retry on error
cache_session = requests_cache.CachedSession('.cache', expire_after = 3600)
retry_session = retry(cache_session, retries = 5, backoff_factor = 0.2)
openmeteo = openmeteo_requests.Client(session = retry_session)






# UTIL FUNTIONS
def getWeatherState(state:list[str], lat=10.823, lon=106.6296, timezone='Asia/Bangkok', forecast_days=1):
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": lat,
        "longitude": lon,
        "hourly": state,
        "timezone": "Asia/Bangkok",
        "forecast_days": 1
    }
    
    try:
        responses = openmeteo.weather_api(url, params=params)
        transformMeteoRespose(responses[0], timezone)
            
    except Exception as exc:
        print(f'ERROR - getWeatherState(): {exc}')
        return None 


def transformMeteoRespose(response, timezone):
    print(f"Coordinates {response.Latitude()}°N {response.Longitude()}°E")
    print(f"Elevation {response.Elevation()} m asl")
    print(f"Timezone {response.Timezone()} {response.TimezoneAbbreviation()}")
    print(f"Timezone difference to GMT+0 {response.UtcOffsetSeconds()} s")

    # Process hourly data. The order of variables needs to be the same as requested.
    hourly = response.Hourly()
    hourly_temperature_2m = hourly.Variables(0).ValuesAsNumpy()
    hourly_relative_humidity_2m = hourly.Variables(1).ValuesAsNumpy()
    hourly_rain = hourly.Variables(2).ValuesAsNumpy()
    hourly_evapotranspiration = hourly.Variables(3).ValuesAsNumpy()
    hourly_wind_speed_10m = hourly.Variables(4).ValuesAsNumpy()

    hourly_data = {"date": pd.date_range(
        start = pd.to_datetime(hourly.Time(), unit = "s", utc = True).tz_convert(timezone),
        end = pd.to_datetime(hourly.TimeEnd(), unit = "s", utc = True).tz_convert(timezone),
        freq = pd.Timedelta(seconds = hourly.Interval()),
        inclusive = "left"
    )}
    
    hourly_data["id"] = [dt.strftime("%Y%m%d %H%M%S") for dt in hourly_data["date"]]
    hourly_data["temperature"] = hourly_temperature_2m
    hourly_data["humidity"] = hourly_relative_humidity_2m
    hourly_data["rain"] = hourly_rain
    hourly_data["evapo"] = hourly_evapotranspiration
    hourly_data["wind"] = hourly_wind_speed_10m
    # print(hourly_data)

    hourly_dataframe = pd.DataFrame(data = hourly_data)
    print(hourly_dataframe)



def format_data(data):
    pass


def getKey(data):
    return 'even' if (int(data[0])%2 == 0) else 'odd' 



def streamData():
    # Init producer    
    producer = createProducer()
    
    
    # Read data from CSV and send to Kafka
    
    while (True if not limit else limit):
        try:
            data = callMeteoApi()
            # print(data)
            producer.send(TOPIC_NAMES[0], key=key, value=json.dumps(data))
            # producer.send(TOPIC_NAMES[0], key=key, value=data)
            
            
            record_count += 1
        except Exception as exc:
            logging.error(f'An error occured: {exc}')
            continue
            
        print(f'{record_count} records sent to topic \'{TOPIC_NAMES[0]}\' of Kafka successfully')
    

def createProducer():
    return KafkaProducer(
        bootstrap_servers=BOOTSTRAP_SERVERS,
        key_serializer=lambda key: key.encode('utf-8'),
        value_serializer=lambda value: value.encode('utf-8'),
    )

# MAIN FUNCTION
if __name__ == "__main__":
    getWeatherState(state=state, lat=lat, lon=lon, timezone=timezone, forecast_days=forecast_days)
    # streamData()