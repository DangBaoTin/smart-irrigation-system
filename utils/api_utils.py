import csv
import json
import logging
import requests
import openmeteo_requests
import requests_cache
import pandas as PD
from retry_requests import retry
from kafka import KafkaProducer


class MeteoAPI:
    def __init__(
            self
            , lat=10.823
            , lon=106.6296
            , timezone='Asia/Bangkok'
            , forecast_days=1
            , meteo_state=['temperature_2m', 'relative_humidity_2m', 'rain', 'evapotranspiration', 'wind_speed_10m']
            , cache_expire_after=3600
            , retry_retries=5
        ):
        
        self.lat = lat
        self.lon = lon
        self.timezone = timezone
        self.forecast_days = forecast_days
        self.meteo_url = "https://api.open-meteo.com/v1/forecast"
        
        self.state = meteo_state
        
        self.cache_session = requests_cache.CachedSession('.cache', expire_after=cache_expire_after)
        self.retry_session = retry(self.cache_session, retries=retry_retries, backoff_factor=0.2)
        self.openmeteo = openmeteo_requests.Client(session=self.retry_session)
    
    
    def getWeatherState(state:list[str], lat=10.823, lon=106.6296, timezone='Asia/Bangkok', forecast_days=1):
        
        params = {
            "latitude": lat,
            "longitude": lon,
            "hourly": state,
            "timezone": "Asia/Bangkok",
            "forecast_days": 1
        }
        
        try:
            responses = openmeteo.weather_api(self.meteo_url, params=params)
            return transformMeteoRespose(responses[0], timezone)
                
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
        # print(hourly_dataframe)
        return hourly_dataframe

    def format_data(data):
        pass

