import pandas as pd
import joblib
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestRegressor

# ---------------- LOAD ----------------
traffic = pd.read_csv("data/Metro_Interstate_Traffic_Volume.csv")
weather = pd.read_csv("data/mumbai_weather.csv")

# ---------------- CLEAN DATETIME ----------------
traffic["date_time"] = pd.to_datetime(traffic["date_time"], errors="coerce")
weather["time"] = pd.to_datetime(weather["time"], errors="coerce")

# ---------------- TIME FEATURES ----------------
traffic["hour"] = traffic["date_time"].dt.hour
traffic["day"] = traffic["date_time"].dt.dayofweek
traffic["month"] = traffic["date_time"].dt.month

weather["hour"] = weather["time"].dt.hour
weather["day"] = weather["time"].dt.dayofweek
weather["month"] = weather["time"].dt.month

# ---------------- CLEAN WEATHER COLUMNS ----------------
weather.columns = weather.columns.str.strip()

weather = weather.rename(columns={
    "temperature_2m (°C)": "temp",
    "rain (mm)": "rain_1h",
    "relative_humidity_2m (%)": "humidity",
    "wind_speed_10m (km/h)": "wind",
    "cloud_cover (%)": "clouds_all"
})

# ---------------- REMOVE TRAFFIC WEATHER ----------------
traffic = traffic.drop(columns=["temp","rain_1h","snow_1h","clouds_all"])

# ---------------- MERGE ----------------
df = pd.merge(traffic, weather, on=["hour","day","month"], how="inner")

# ---------------- CLEAN ----------------
df["is_holiday"] = df["holiday"].apply(lambda x: 0 if x == "None" else 1)
df.fillna(0, inplace=True)

# ---------------- FEATURES ----------------
features = [
    "hour","day","month",
    "temp","rain_1h","clouds_all",
    "humidity","wind","is_holiday"
]

X = df[features]
y = df["traffic_volume"]

# ---------------- TRAIN ----------------
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2)

model = RandomForestRegressor(n_estimators=100)
model.fit(X_train, y_train)

# ---------------- SAVE ----------------
joblib.dump(model, "model/model.pkl")

print("✅ Model trained successfully!")