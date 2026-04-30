import pandas as pd
import joblib
import numpy as np

from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestRegressor
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

# ---------------- LOAD ----------------
traffic = pd.read_csv("data/Metro_Interstate_Traffic_Volume.csv")
weather = pd.read_csv("data/mumbai_weather.csv")

# ---------------- DATETIME ----------------
traffic["date_time"] = pd.to_datetime(traffic["date_time"], errors="coerce")
weather["time"] = pd.to_datetime(weather["time"], errors="coerce")

# ---------------- TIME FEATURES ----------------
traffic["hour"] = traffic["date_time"].dt.hour
traffic["day"] = traffic["date_time"].dt.dayofweek
traffic["month"] = traffic["date_time"].dt.month

weather["hour"] = weather["time"].dt.hour
weather["day"] = weather["time"].dt.dayofweek
weather["month"] = weather["time"].dt.month

# ---------------- CLEAN WEATHER ----------------
weather.columns = weather.columns.str.strip()

weather = weather.rename(columns={
    "temperature_2m (°C)": "temp2",
    "rain (mm)": "rain2",
    "relative_humidity_2m (%)": "humidity",
    "wind_speed_10m (km/h)": "wind",
    "cloud_cover (%)": "clouds2"
})

# ---------------- MERGE ----------------
df = pd.merge(traffic, weather, on=["hour","day","month"], how="left")

# ---------------- FALLBACK IF MERGE FAILS ----------------
df.fillna({
    "humidity": 60,
    "wind": 10
}, inplace=True)

# ---------------- FEATURES ----------------
df["is_holiday"] = df["holiday"].apply(lambda x: 0 if x == "None" else 1)

# 🔥 COMBINED WEATHER FEATURES
df["temp_humidity"] = df["temp"] * df["humidity"]
df["rain_intensity"] = df["rain_1h"] * df["clouds_all"]

df["weather_severity"] = (
    df["temp"] * 0.3 +
    df["humidity"] * 0.2 +
    df["clouds_all"] * 0.2 +
    df["wind"] * 0.1 +
    df["rain_1h"] * 0.2
)

# 🌡️ DEW POINT (Approximation)
df["dew_point"] = df["temp"] - ((100 - df["humidity"]) / 5.0)

# 🌡️ HEAT INDEX (Perceived temperature)
df["heat_index"] = 0.5 * (df["temp"] + 61.0 + ((df["temp"] - 68.0) * 1.2) + (df["humidity"] * 0.094))

# 🌬️ WIND CHILL (Temperature with wind effect)
df["wind_chill"] = 13.12 + (0.6215 * df["temp"]) - (11.37 * (df["wind"] ** 0.16)) + (0.3965 * df["temp"] * (df["wind"] ** 0.16))

# 💧 ABSOLUTE HUMIDITY (Moisture in air)
df["abs_humidity"] = (6.112 * np.exp((17.67 * df["temp"]) / (df["temp"] + 243.5)) * df["humidity"] / 100) / 100

# 🌧️ RAIN-HUMIDITY RATIO
df["rain_humidity_ratio"] = df["rain_1h"] / (df["humidity"] + 1)

# ☁️ CLOUD-WIND INTERACTION
df["cloud_wind_interaction"] = df["clouds_all"] * df["wind"]

# 🌡️ HUMIDITY COMFORT (Comfort index: optimal is 30-60%)
df["humidity_comfort"] = np.abs(df["humidity"] - 45)  # Lower is more comfortable

# 🌡️ TEMPERATURE CATEGORY
df["is_hot"] = (df["temp"] > 30).astype(int)
df["is_cold"] = (df["temp"] < 15).astype(int)
df["is_rain"] = (df["rain_1h"] > 0).astype(int)

# 🌩️ WEATHER STABILITY INDEX (Low = stable weather)
df["weather_stability"] = np.abs(df["wind"]) + np.abs(df["clouds_all"] - 50) / 100

# ☁️ CLOUD DENSITY CATEGORIES
df["high_clouds"] = (df["clouds_all"] > 70).astype(int)
df["low_clouds"] = (df["clouds_all"] < 30).astype(int)

# 🌡️ TEMP-WIND-HUMIDITY COMPOUND INDEX
df["discomfort_index"] = (0.4 * (df["temp"] + df["heat_index"]) / 2) + (0.6 * df["humidity"]) - 20

df.fillna(0, inplace=True)

# Clip extreme values
df["heat_index"] = np.clip(df["heat_index"], 20, 60)
df["wind_chill"] = np.clip(df["wind_chill"], -50, 50)
df["discomfort_index"] = np.clip(df["discomfort_index"], 0, 100)

# ---------------- FEATURES ----------------
features = [
    "hour","day","month",
    "temp","rain_1h","clouds_all",
    "humidity","wind","is_holiday",
    "temp_humidity","rain_intensity","weather_severity",
    "dew_point","heat_index","wind_chill","abs_humidity",
    "rain_humidity_ratio","cloud_wind_interaction","humidity_comfort",
    "is_hot","is_cold","is_rain",
    "weather_stability","high_clouds","low_clouds","discomfort_index"
]

X = df[features]
y = df["traffic_volume"]

# ---------------- SPLIT ----------------
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2)

# ---------------- MODELS ----------------
models = {
    "Linear Regression": LinearRegression(),
    "Random Forest": RandomForestRegressor(n_estimators=150)
}

results = []
best_model = None
best_r2 = -999

for name, m in models.items():
    m.fit(X_train, y_train)
    pred = m.predict(X_test)

    mae = mean_absolute_error(y_test, pred)
    rmse = np.sqrt(mean_squared_error(y_test, pred))
    r2 = r2_score(y_test, pred)

    results.append({
        "Model": name,
        "MAE": mae,
        "RMSE": rmse,
        "R2": r2
    })

    if r2 > best_r2:
        best_r2 = r2
        best_model = m

# ---------------- SAVE MODEL ----------------
joblib.dump(best_model, "model/model.pkl")

# ---------------- SAVE METRICS ----------------
pd.DataFrame(results).to_csv("model/model_comparison.csv", index=False)

# ---------------- FEATURE IMPORTANCE ----------------
if hasattr(best_model, "feature_importances_"):
    importance_df = pd.DataFrame({
        "feature": X.columns,
        "importance": best_model.feature_importances_
    }).sort_values(by="importance", ascending=False)

    importance_df.to_csv("model/feature_importance.csv", index=False)

print("\n✅ Training Successful!")
print(pd.DataFrame(results))