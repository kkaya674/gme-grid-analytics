import requests
import pandas as pd
from datetime import datetime, timedelta

def get_weather_data(start_date, end_date, lat=45.46, lon=9.18):
    url = (
        f"https://archive-api.open-meteo.com/v1/archive?"
        f"latitude={lat}&longitude={lon}"
        f"&start_date={start_date}&end_date={end_date}"
        f"&hourly=temperature_2m,relative_humidity_2m,wind_speed_10m,shortwave_radiation,cloudcover,rain&timezone=Europe%2FBerlin"
    )
    
    response = requests.get(url)
    weather_data = response.json()
    
    temp_df = pd.DataFrame({
        'datetime': pd.to_datetime(weather_data['hourly']['time']),
        'temperature': weather_data['hourly']['temperature_2m'],
        'humidity': weather_data['hourly']['relative_humidity_2m'],
        'wind_speed': weather_data['hourly']['wind_speed_10m'],
        'solar_radiation': weather_data['hourly']['shortwave_radiation'],
        'cloudcover': weather_data['hourly']['cloudcover'],
        'rain': weather_data['hourly']['rain']
    })
    temp_df['date'] = temp_df['datetime'].dt.date
    temp_df['interval'] = temp_df['datetime'].dt.hour + 1
    
    return temp_df[['date', 'interval', 'temperature', 'humidity', 'wind_speed', 'solar_radiation', 'cloudcover', 'rain']]

def get_weather_forecast(days=2, lat=45.46, lon=9.18):
    url = (
        f"https://api.open-meteo.com/v1/forecast?"
        f"latitude={lat}&longitude={lon}"
        f"&hourly=temperature_2m,relative_humidity_2m,wind_speed_10m,shortwave_radiation,cloudcover&timezone=Europe%2FBerlin"
        f"&forecast_days={days}"
    )
    
    response = requests.get(url)
    forecast_data = response.json()
    
    temp_df = pd.DataFrame({
        'datetime': pd.to_datetime(forecast_data['hourly']['time']),
        'temperature': forecast_data['hourly']['temperature_2m'],
        'humidity': forecast_data['hourly']['relative_humidity_2m'],
        'wind_speed': forecast_data['hourly']['wind_speed_10m'],
        'solar_radiation': forecast_data['hourly']['shortwave_radiation'],
        'cloudcover': forecast_data['hourly']['cloudcover']
    })
    temp_df['date'] = temp_df['datetime'].dt.date
    temp_df['interval'] = temp_df['datetime'].dt.hour + 1
    
    return temp_df[['date', 'interval', 'temperature', 'humidity', 'wind_speed', 'solar_radiation', 'cloudcover']]
