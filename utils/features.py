import pandas as pd
import numpy as np

def create_features(weather, now):
    temp = weather.get("temperature", 25)
    humidity = weather.get("humidity", 60)
    wind = weather.get("windspeed", 10)
    rain = weather.get("rain", 0)
    clouds = weather.get("cloudcover", 50)
    
    # 🔥 Basic weather features
    temp_humidity = temp * humidity
    rain_intensity = rain * clouds
    
    # 🌡️ Dew point
    dew_point = temp - ((100 - humidity) / 5.0)
    
    # 🌡️ Heat index
    heat_index = 0.5 * (temp + 61.0 + ((temp - 68.0) * 1.2) + (humidity * 0.094))
    heat_index = np.clip(heat_index, 20, 60)
    
    # 🌬️ Wind chill
    wind_chill = 13.12 + (0.6215 * temp) - (11.37 * (wind ** 0.16)) + (0.3965 * temp * (wind ** 0.16))
    wind_chill = np.clip(wind_chill, -50, 50)
    
    # 💧 Absolute humidity
    abs_humidity = (6.112 * np.exp((17.67 * temp) / (temp + 243.5)) * humidity / 100) / 100
    
    # 🌧️ Rain-humidity ratio
    rain_humidity_ratio = rain / (humidity + 1)
    
    # ☁️ Cloud-wind interaction
    cloud_wind_interaction = clouds * wind
    
    # 🌡️ Humidity comfort
    humidity_comfort = np.abs(humidity - 45)
    
    # 🌬️ Weather stability
    weather_stability = np.abs(wind) + np.abs(clouds - 50) / 100
    
    # 🌡️ Discomfort index
    discomfort_index = (0.4 * (temp + heat_index) / 2) + (0.6 * humidity) - 20
    discomfort_index = np.clip(discomfort_index, 0, 100)
    
    # 🌡️ Weather severity
    weather_severity = (
        temp * 0.3 +
        humidity * 0.2 +
        clouds * 0.2 +
        wind * 0.1 +
        rain * 0.2
    )
    
    return pd.DataFrame([{
        # Time features
        "hour": now.hour,
        "day": now.weekday(),
        "month": now.month,
        # Basic weather
        "temp": temp,
        "rain_1h": rain,
        "clouds_all": clouds,
        "humidity": humidity,
        "wind": wind,
        "is_holiday": 0,
        # Combined weather
        "temp_humidity": temp_humidity,
        "rain_intensity": rain_intensity,
        "weather_severity": weather_severity,
        # Advanced weather features
        "dew_point": dew_point,
        "heat_index": heat_index,
        "wind_chill": wind_chill,
        "abs_humidity": abs_humidity,
        "rain_humidity_ratio": rain_humidity_ratio,
        "cloud_wind_interaction": cloud_wind_interaction,
        "humidity_comfort": humidity_comfort,
        # Weather categories
        "is_hot": int(temp > 30),
        "is_cold": int(temp < 15),
        "is_rain": int(rain > 0),
        # Weather conditions
        "weather_stability": weather_stability,
        "high_clouds": int(clouds > 70),
        "low_clouds": int(clouds < 30),
        "discomfort_index": discomfort_index,
    }])