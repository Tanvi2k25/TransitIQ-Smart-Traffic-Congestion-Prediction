import pandas as pd

def load_traffic_data():
    df = pd.read_csv("data/Metro_Interstate_Traffic_Volume.csv")

    df["date_time"] = pd.to_datetime(df["date_time"])
    df["hour"] = df["date_time"].dt.hour
    df["day"] = df["date_time"].dt.dayofweek

    return df


def load_weather_data():
    df = pd.read_csv("data/mumbai_weather.csv")
    return df