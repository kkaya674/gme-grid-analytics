import xgboost as xgb
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import holidays
from services.weather import get_weather_data, get_weather_forecast

def prepare_features(df):
    df = df.copy()
    df['date'] = pd.to_datetime(df['date'])
    
    df['interval'] = pd.to_numeric(df['interval'], errors='coerce').fillna(1).astype(int)
    df['hour'] = df['interval'] - 1
    df['dayofweek'] = df['date'].dt.dayofweek
    df['month'] = df['date'].dt.month
    df['year'] = df['date'].dt.year
    df['quarter'] = df['date'].dt.quarter
    df['day'] = df['date'].dt.day
    
    df['hour_sin'] = np.sin(2 * np.pi * df['hour'] / 24)
    df['hour_cos'] = np.cos(2 * np.pi * df['hour'] / 24)
    df['day_sin'] = np.sin(2 * np.pi * df['dayofweek'] / 7)
    df['day_cos'] = np.cos(2 * np.pi * df['dayofweek'] / 7)
    df['month_sin'] = np.sin(2 * np.pi * df['month'] / 12)
    df['month_cos'] = np.cos(2 * np.pi * df['month'] / 12)
    
    it_holidays = holidays.Italy()
    df['is_weekend'] = (df['dayofweek'] >= 5).astype(int)
    df['is_holiday'] = df['date'].apply(lambda x: x in it_holidays).astype(int)
    df['is_offday'] = ((df['is_weekend'] == 1) | (df['is_holiday'] == 1)).astype(int)
    
    for lag in [1, 2, 3, 6, 12, 24]:
        df[f'price_lag{lag}'] = df.groupby('interval')['price'].shift(lag)
    
    df['price_ma24'] = df.groupby('interval')['price'].transform(lambda x: x.rolling(window=24, min_periods=1).mean())
    df['price_std24'] = df.groupby('interval')['price'].transform(lambda x: x.rolling(window=24, min_periods=1).std())
    df['price_min24'] = df.groupby('interval')['price'].transform(lambda x: x.rolling(window=24, min_periods=1).min())
    df['price_max24'] = df.groupby('interval')['price'].transform(lambda x: x.rolling(window=24, min_periods=1).max())
    
    df['price_change_1h'] = df.groupby('interval')['price'].pct_change(1)
    df['price_change_24h'] = df.groupby('interval')['price'].pct_change(24)
    
    return df

def train_and_predict(prices_data, forecast_days=2):
    if not prices_data or len(prices_data) < 72:
        return []
    
    df = pd.DataFrame(prices_data)
    
    if 'interval' not in df.columns:
        df['interval'] = df.index % 24 + 1
    
    df = prepare_features(df)
    
    start_date = df['date'].min().strftime('%Y-%m-%d')
    end_date = df['date'].max().strftime('%Y-%m-%d')
    
    try:
        weather_hist = get_weather_data(start_date, end_date)
        weather_hist['date'] = pd.to_datetime(weather_hist['date'])
        df = df.merge(weather_hist, on=['date', 'interval'], how='left')
        
        weather_fcast = get_weather_forecast(days=forecast_days)
        weather_fcast['date'] = pd.to_datetime(weather_fcast['date'])
    except Exception as e:
        print(f"Weather data unavailable: {e}")
        weather_cols = ['temperature', 'humidity', 'wind_speed', 'solar_radiation', 'cloudcover', 'rain']
        for col in weather_cols:
            if col not in df.columns:
                df[col] = 0
        weather_fcast = None
    
    feature_cols = [
        'hour', 'dayofweek', 'month', 'year', 'quarter',
        'hour_sin', 'hour_cos', 'day_sin', 'day_cos', 'month_sin', 'month_cos',
        'is_weekend', 'is_holiday', 'is_offday',
        'price_lag1', 'price_lag2', 'price_lag3', 'price_lag6', 'price_lag12', 'price_lag24',
        'price_ma24', 'price_std24', 'price_min24', 'price_max24',
        'price_change_1h', 'price_change_24h',
        'temperature', 'humidity', 'wind_speed', 'solar_radiation', 'cloudcover'
    ]
    
    if 'rain' in df.columns:
        feature_cols.append('rain')
    
    feature_cols = [col for col in feature_cols if col in df.columns]
    
    df_clean = df.dropna(subset=feature_cols + ['price'])
    
    if len(df_clean) < 24:
        return []
    
    X = df_clean[feature_cols]
    y = df_clean['price']
    
    model = xgb.XGBRegressor(
        objective='reg:squarederror',
        n_estimators=200,
        max_depth=6,
        learning_rate=0.1,
        subsample=0.8,
        colsample_bytree=0.8,
        random_state=42
    )
    model.fit(X, y)
    
    last_date = df['date'].max()
    future_dates = [last_date + timedelta(days=i) for i in range(1, forecast_days + 1)]
    
    future_records = []
    for future_date in future_dates:
        for hour in range(24):
            future_records.append({
                'date': future_date,
                'interval': hour + 1
            })
    
    future_df = pd.DataFrame(future_records)
    future_df = prepare_features(future_df)
    
    if weather_fcast is not None:
        future_df = future_df.merge(weather_fcast, on=['date', 'interval'], how='left')
    else:
        for col in ['temperature', 'humidity', 'wind_speed', 'solar_radiation', 'cloudcover']:
            if col not in future_df.columns:
                future_df[col] = 0
    
    last_24_prices = df.tail(24)['price'].values
    for i in range(len(future_df)):
        interval = future_df.iloc[i]['interval']
        
        if i < 24:
            lag_source = df[df['interval'] == interval].tail(24)
        else:
            lag_source = future_df.iloc[:i]
            lag_source = lag_source[lag_source['interval'] == interval]
        
        if len(lag_source) > 0:
            for lag in [1, 2, 3, 6, 12, 24]:
                if lag <= len(lag_source):
                    future_df.loc[future_df.index[i], f'price_lag{lag}'] = lag_source.iloc[-lag]['price'] if 'price' in lag_source.columns else lag_source.iloc[-min(lag, len(lag_source))].get('price_pred', last_24_prices[min(interval - 1, 23)])
        
        for col in ['price_ma24', 'price_std24', 'price_min24', 'price_max24', 'price_change_1h', 'price_change_24h']:
            if col not in future_df.columns or pd.isna(future_df.loc[future_df.index[i], col]):
                future_df.loc[future_df.index[i], col] = 0
    
    future_df = future_df.fillna(0)
    
    X_future = future_df[feature_cols]
    predictions = model.predict(X_future)
    future_df['price_pred'] = predictions
    
    result = []
    for idx, row in future_df.iterrows():
        result.append({
            "date": row['date'].strftime("%Y-%m-%d"),
            "interval": int(row['interval']),
            "price": float(row['price_pred']),
            "type": "forecast"
        })
    
    return result
