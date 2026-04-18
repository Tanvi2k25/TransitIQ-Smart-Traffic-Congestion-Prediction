import pandas as pd
def create_features(weather, now):
    return pd.DataFrame([{
        "hour": now.hour,
        "day": now.weekday(),
        "month": now.month,
        "temp": weather["temperature"],
        "rain_1h": weather["rain"],
        "clouds_all": weather["cloudcover"],
        "humidity": weather["humidity"],
        "wind": weather["windspeed"],
        "is_holiday": 0
    }])