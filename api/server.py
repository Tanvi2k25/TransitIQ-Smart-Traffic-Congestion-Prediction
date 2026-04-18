from flask import Flask, jsonify, request
import joblib, requests, os
from datetime import datetime
from geopy.geocoders import Nominatim
from utils.features import create_features

app = Flask(__name__)

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
model = joblib.load(os.path.join(BASE, "model", "model.pkl"))

TOMTOM_API_KEY = "giy1oKjHP1ncGgr6laaFs6YNZx77oTVh"
geo = Nominatim(user_agent="traffic_app")


# ---------------- WEATHER ----------------
def get_weather(lat, lon):
    try:
        url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current_weather=true&hourly=relativehumidity_2m,cloudcover,precipitation,uv_index"
        res = requests.get(url).json()

        current = res.get("current_weather", {})
        hourly = res.get("hourly", {})

        return {
            "temperature": current.get("temperature", 28),
            "windspeed": current.get("windspeed", 10),
            "cloudcover": hourly.get("cloudcover", [50])[0],
            "humidity": hourly.get("relativehumidity_2m", [70])[0],
            "rain": hourly.get("precipitation", [0])[0],
            "uv_index": hourly.get("uv_index", [5])[0]
        }
    except:
        return {
            "temperature": 28,
            "windspeed": 10,
            "cloudcover": 50,
            "humidity": 70,
            "rain": 0,
            "uv_index": 5
        }


# ---------------- REAL TRAFFIC ----------------
def get_real_traffic(lat, lon):
    try:
        url = f"https://api.tomtom.com/traffic/services/4/flowSegmentData/absolute/10/json?point={lat},{lon}&key={TOMTOM_API_KEY}"
        res = requests.get(url).json()

        data = res.get("flowSegmentData", {})

        return {
            "speed": data.get("currentSpeed"),
            "free_flow": data.get("freeFlowSpeed")
        }
    except:
        return None


# ---------------- PLACE ----------------
def get_place(lat, lon):
    try:
        return geo.reverse((lat, lon)).address
    except:
        return "Mumbai"


# ---------------- MODEL ----------------
def predict_volume(weather, now):
    X = create_features(weather, now)
    return model.predict(X)[0]


# ---------------- API ----------------
@app.route("/predict")
def predict():
    try:
        lat = float(request.args.get("lat", 19.0760))
        lon = float(request.args.get("lon", 72.8777))
    except:
        lat = 19.0760
        lon = 72.8777

    now = datetime.now()

    weather = get_weather(lat, lon)
    predicted_volume = predict_volume(weather, now)

    real = get_real_traffic(lat, lon)

    actual_congestion = None
    actual_volume = None
    speed = None
    free = None

    if real:
        speed = real["speed"]
        free = real["free_flow"]

        if speed and free and free != 0:
            actual_congestion = 1 - (speed / free)
            actual_volume = predicted_volume * (1 + actual_congestion)

    pred_class = 0 if predicted_volume < 2000 else 1 if predicted_volume < 4000 else 2

    return jsonify({
        "prediction": pred_class,
        "predicted_volume": float(predicted_volume),
        "actual_volume": float(actual_volume) if actual_volume else None,
        "actual_congestion": actual_congestion,
        "speed": speed,
        "free_flow": free,
        "weather": weather,
        "place": get_place(lat, lon),
        "lat": lat,
        "lon": lon,
        "timestamp": now.strftime("%d %B %Y %I:%M:%S %p")
    })


if __name__ == "__main__":
    app.run(debug=True)