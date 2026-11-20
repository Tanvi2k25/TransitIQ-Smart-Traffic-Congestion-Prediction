from pathlib import Path
import time
import warnings
import joblib
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LinearRegression
from sklearn.tree import DecisionTreeRegressor
from sklearn.ensemble import (
    RandomForestRegressor,
    GradientBoostingRegressor
)
from sklearn.metrics import (
    mean_absolute_error,
    mean_squared_error,
    r2_score
)

# XGBoost dependency check
try:
    from xgboost import XGBRegressor
except ImportError:
    raise ImportError(
        "XGBoost is not installed. Run: python -m pip install xgboost"
    )

warnings.filterwarnings("ignore", category=RuntimeWarning)


# =====================================================
# 1. PATHS
# =====================================================

BASE_DIR = Path(__file__).resolve().parent

DATA_PATH = BASE_DIR / "data" / "Metro_Interstate_Traffic_Volume.csv"
MODEL_DIR = BASE_DIR / "model"

MODEL_DIR.mkdir(parents=True, exist_ok=True)


# =====================================================
# 2. LOAD DATA
# =====================================================

print("\nLoading traffic dataset...")

df = pd.read_csv(DATA_PATH)

required_columns = [
    "date_time",
    "traffic_volume",
    "temp",
    "rain_1h",
    "clouds_all"
]

missing = [c for c in required_columns if c not in df.columns]

if missing:
    raise ValueError(f"Missing required columns: {missing}")

df["date_time"] = pd.to_datetime(
    df["date_time"], errors="coerce"
)

for col in ["traffic_volume", "temp", "rain_1h", "clouds_all"]:
    df[col] = pd.to_numeric(df[col], errors="coerce")

df = df.dropna(
    subset=["date_time", "traffic_volume"]
).copy()

df = df[
    np.isfinite(df["traffic_volume"])
    & (df["traffic_volume"] >= 0)
].copy()

df = df.sort_values("date_time").reset_index(drop=True)

if len(df) < 100:
    raise ValueError("Not enough valid records for training.")

print("Dataset records:", len(df))


# =====================================================
# 3. CLEAN WEATHER DATA
# =====================================================

# Metro Interstate temperature is recorded in Kelvin.
df.loc[df["temp"] <= 0, "temp"] = np.nan

if df["temp"].median() > 100:
    df["temp"] = df["temp"] - 273.15

df["temp"] = df["temp"].clip(-50, 60)

if df["temp"].notna().sum() == 0:
    raise ValueError("Temperature column has no valid values.")

df["temp"] = df["temp"].fillna(df["temp"].median())

df["rain_1h"] = df["rain_1h"].fillna(0).clip(0, 500)
df["clouds_all"] = df["clouds_all"].fillna(50).clip(0, 100)

# Defaults maintain compatibility with existing backend features.
df["humidity"] = 60.0
df["wind"] = 10.0


# =====================================================
# 4. TIME FEATURES
# =====================================================

df["hour"] = df["date_time"].dt.hour
df["day"] = df["date_time"].dt.dayofweek
df["month"] = df["date_time"].dt.month

if "holiday" in df.columns:
    holiday = df["holiday"].fillna("None").astype(str)

    df["is_holiday"] = (
        holiday.str.lower().ne("none")
        & holiday.str.lower().ne("nan")
    ).astype(int)
else:
    df["is_holiday"] = 0


# =====================================================
# 5. WEATHER FEATURE ENGINEERING
# =====================================================

df["temp_humidity"] = df["temp"] * df["humidity"]

df["rain_intensity"] = (
    df["rain_1h"] * df["clouds_all"]
)

df["weather_severity"] = (
    df["temp"] * 0.3
    + df["humidity"] * 0.2
    + df["clouds_all"] * 0.2
    + df["wind"] * 0.1
    + df["rain_1h"] * 0.2
)

df["dew_point"] = (
    df["temp"] - ((100 - df["humidity"]) / 5.0)
)

df["heat_index"] = (
    0.5 * (
        df["temp"]
        + 61.0
        + ((df["temp"] - 68.0) * 1.2)
        + (df["humidity"] * 0.094)
    )
)

df["wind_chill"] = (
    13.12
    + (0.6215 * df["temp"])
    - (11.37 * (df["wind"] ** 0.16))
    + (
        0.3965
        * df["temp"]
        * (df["wind"] ** 0.16)
    )
)

safe_temp = df["temp"].clip(-50, 60)

df["abs_humidity"] = (
    6.112
    * np.exp(
        (17.67 * safe_temp)
        / (safe_temp + 243.5)
    )
    * df["humidity"] / 100
) / 100

df["rain_humidity_ratio"] = (
    df["rain_1h"] / (df["humidity"] + 1)
)

df["cloud_wind_interaction"] = (
    df["clouds_all"] * df["wind"]
)

df["humidity_comfort"] = np.abs(
    df["humidity"] - 45
)

df["is_hot"] = (df["temp"] > 30).astype(int)
df["is_cold"] = (df["temp"] < 15).astype(int)
df["is_rain"] = (df["rain_1h"] > 0).astype(int)

df["weather_stability"] = (
    np.abs(df["wind"])
    + np.abs(df["clouds_all"] - 50) / 100
)

df["high_clouds"] = (
    df["clouds_all"] > 70
).astype(int)

df["low_clouds"] = (
    df["clouds_all"] < 30
).astype(int)

df["discomfort_index"] = (
    0.4 * ((df["temp"] + df["heat_index"]) / 2)
    + 0.6 * df["humidity"]
    - 20
)

df["heat_index"] = df["heat_index"].clip(20, 60)
df["wind_chill"] = df["wind_chill"].clip(-50, 50)
df["discomfort_index"] = df["discomfort_index"].clip(0, 100)


# =====================================================
# 6. SELECT FEATURES
# =====================================================

# Preserve the feature names and order used by the backend.

features = [
    "hour", "day", "month",
    "temp", "rain_1h", "clouds_all",
    "humidity", "wind", "is_holiday",
    "temp_humidity", "rain_intensity",
    "weather_severity", "dew_point",
    "heat_index", "wind_chill",
    "abs_humidity", "rain_humidity_ratio",
    "cloud_wind_interaction", "humidity_comfort",
    "is_hot", "is_cold", "is_rain",
    "weather_stability", "high_clouds",
    "low_clouds", "discomfort_index"
]

X = df[features].copy()

X = X.replace([np.inf, -np.inf], np.nan)
X = X.fillna(0)
X = X.clip(-1000000, 1000000)

if not np.isfinite(X.to_numpy(dtype=float)).all():
    raise ValueError("Invalid values remain in feature dataset.")

y = df["traffic_volume"].astype(float)

print("Features prepared:", len(features))


# =====================================================
# 7. CHRONOLOGICAL TRAIN-TEST SPLIT
# =====================================================

split_index = int(len(df) * 0.80)

X_train = X.iloc[:split_index]
X_test = X.iloc[split_index:]

y_train = y.iloc[:split_index]
y_test = y.iloc[split_index:]

if len(X_train) == 0 or len(X_test) == 0:
    raise ValueError("Training or testing dataset is empty.")

print("Training records:", len(X_train))
print("Testing records:", len(X_test))


# =====================================================
# 8. DEFINE FIVE MODELS
# =====================================================

models = {

    "Linear Regression": Pipeline([
        ("scaler", StandardScaler()),
        ("model", LinearRegression())
    ]),

    "Decision Tree": DecisionTreeRegressor(
        max_depth=15,
        min_samples_leaf=2,
        random_state=42
    ),

    "Random Forest": RandomForestRegressor(
        n_estimators=100,
        max_depth=15,
        min_samples_leaf=2,
        n_jobs=-1,
        random_state=42
    ),

    "Gradient Boosting": GradientBoostingRegressor(
        n_estimators=100,
        learning_rate=0.1,
        max_depth=3,
        random_state=42
    ),

    "XGBoost": XGBRegressor(
        n_estimators=150,
        learning_rate=0.05,
        max_depth=5,
        subsample=0.8,
        colsample_bytree=0.8,
        objective="reg:squarederror",
        eval_metric="rmse",
        tree_method="hist",
        n_jobs=-1,
        random_state=42,
        verbosity=0
    )
}


# =====================================================
# 9. TRAIN AND EVALUATE ALL MODELS
# =====================================================

results = []
trained_models = {}
predictions = {}

for name, model in models.items():

    print(f"\nTraining {name}...", flush=True)

    start_time = time.time()

    model.fit(X_train, y_train)

    elapsed = time.time() - start_time

    pred = model.predict(X_test)

    mae = mean_absolute_error(y_test, pred)

    rmse = np.sqrt(
        mean_squared_error(y_test, pred)
    )

    r2 = r2_score(y_test, pred)

    results.append({
        "Model": name,
        "MAE": mae,
        "RMSE": rmse,
        "R2": r2,
        "Training_Time_Seconds": elapsed
    })

    trained_models[name] = model
    predictions[name] = pred

    print(f"MAE: {mae:.2f}")
    print(f"RMSE: {rmse:.2f}")
    print(f"R2 Score: {r2:.4f}")
    print(f"Training Time: {elapsed:.2f} seconds")


# =====================================================
# 10. SAVE MODEL COMPARISON
# =====================================================

results_df = pd.DataFrame(results)

results_df = results_df.sort_values(
    by="R2",
    ascending=False
).reset_index(drop=True)

results_df.to_csv(
    MODEL_DIR / "model_comparison.csv",
    index=False
)

print("\nFIVE-MODEL COMPARISON")
print(results_df.to_string(index=False))


# =====================================================
# 11. SELECT AND SAVE BEST MODEL
# =====================================================

best_model_name = results_df.iloc[0]["Model"]
best_model = trained_models[best_model_name]

joblib.dump(
    best_model,
    MODEL_DIR / "model.pkl"
)

print("\nBest model:", best_model_name)
print("Saved: model/model.pkl")


# =====================================================
# 12. SAVE FEATURE IMPORTANCE
# =====================================================

# Random Forest provides a consistent tree-based
# feature importance report for this experiment.

importance_model = trained_models["Random Forest"]

importance_df = pd.DataFrame({
    "Feature": features,
    "Importance": importance_model.feature_importances_
})

importance_df = importance_df.sort_values(
    by="Importance",
    ascending=False
)

importance_df.to_csv(
    MODEL_DIR / "feature_importance.csv",
    index=False
)


# =====================================================
# 13. GENERATE COMPARISON GRAPHS
# =====================================================

graph_metrics = [
    ("MAE", "Mean Absolute Error"),
    ("RMSE", "Root Mean Squared Error"),
    ("R2", "R2 Score")
]

for metric, title in graph_metrics:

    plot_df = results_df.sort_values(
        by=metric,
        ascending=(metric != "R2")
    )

    plt.figure(figsize=(10, 5))

    bars = plt.bar(
        plot_df["Model"],
        plot_df[metric]
    )

    plt.title(f"Five-Model Comparison - {title}")
    plt.xlabel("Regression Models")
    plt.ylabel(title)
    plt.xticks(rotation=15)
    plt.grid(axis="y", linestyle="--", alpha=0.4)

    for bar in bars:
        value = bar.get_height()

        plt.annotate(
            f"{value:.3f}",
            (
                bar.get_x() + bar.get_width() / 2,
                value
            ),
            ha="center",
            va="bottom" if value >= 0 else "top"
        )

    plt.tight_layout()

    plt.savefig(
        MODEL_DIR / f"{metric.lower()}_comparison.png",
        dpi=300,
        bbox_inches="tight"
    )

    plt.close()


# =====================================================
# 14. ACTUAL VS PREDICTED GRAPH
# =====================================================

best_predictions = predictions[best_model_name]

plt.figure(figsize=(8, 6))

plt.scatter(
    y_test,
    best_predictions,
    alpha=0.4
)

minimum = min(y_test.min(), best_predictions.min())
maximum = max(y_test.max(), best_predictions.max())

plt.plot(
    [minimum, maximum],
    [minimum, maximum],
    linestyle="--"
)

plt.title(f"Actual vs Predicted - {best_model_name}")
plt.xlabel("Actual Traffic Volume")
plt.ylabel("Predicted Traffic Volume")
plt.grid(alpha=0.3)
plt.tight_layout()

plt.savefig(
    MODEL_DIR / "actual_vs_predicted.png",
    dpi=300,
    bbox_inches="tight"
)

plt.close()


# =====================================================
# 15. COMPLETION
# =====================================================

print("\n======================================")
print("TRANSITIQ MODEL TRAINING COMPLETED")
print("======================================")

print("Models compared:", len(models))
print("Best model:", best_model_name)
print("Comparison CSV: model/model_comparison.csv")
print("Graphs saved inside: model/")
print("Model saved: model/model.pkl")
