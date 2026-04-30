from flask import Flask, jsonify, request
import requests, joblib, os
import random
from datetime import datetime, timedelta
import pandas as pd
import numpy as np

app = Flask(__name__)

TOMTOM_API_KEY = "rQGLD1nHFeMPXHfOyeypcstutAh1CEhc"

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
model = joblib.load(os.path.join(BASE, "model", "model.pkl"))

# ---------------- LOCATION NAME ----------------
def reverse_geocode(lat, lon):
    """
    Reverse geocode coordinates to get location name.
    Uses multiple fallback services for reliability.
    """
    try:
        # First try: OpenStreetMap Nominatim (Most reliable for Mumbai)
        url = "https://nominatim.openstreetmap.org/reverse"
        params = {
            "lat": lat,
            "lon": lon,
            "format": "json",
            "zoom": 16,
            "addressdetails": 1
        }
        headers = {
            "User-Agent": "Mumbai-Traffic-Dashboard/1.0"  # ✅ Add user-agent
        }
        res = requests.get(url, params=params, headers=headers, timeout=5)
        
        if res.status_code == 200:
            data = res.json()
            if "address" in data:
                addr = data["address"]
                # Try to get the most specific location name
                location_name = addr.get("neighborhood") or addr.get("suburb") or addr.get("village") or addr.get("town") or addr.get("municipality") or "Mumbai"
                return location_name
            
    except requests.exceptions.RequestException as e:
        print(f"Nominatim request error: {e}")
    except ValueError as e:
        print(f"Nominatim JSON parse error: {e}")
    except Exception as e:
        print(f"Nominatim error: {e}")
    
    try:
        # Second try: TomTom (Backup)
        url = f"https://api.tomtom.com/search/2/reverseGeocode/{lat},{lon}.json"
        res = requests.get(url, params={"key": TOMTOM_API_KEY}, timeout=5)
        
        if res.status_code == 200:
            data = res.json()
            if "addresses" in data and len(data["addresses"]) > 0:
                addr = data["addresses"][0]["address"]
                location_name = addr.get("municipalitySubdivision") or addr.get("municipality") or "Mumbai"
                return location_name
            
    except requests.exceptions.RequestException as e:
        print(f"TomTom request error: {e}")
    except ValueError as e:
        print(f"TomTom JSON parse error: {e}")
    except Exception as e:
        print(f"TomTom error: {e}")
    
    # Fallback
    return "Mumbai"

# ---------------- WEATHER (UPDATED) ----------------
def get_weather(lat, lon):
    try:
        url = "https://api.open-meteo.com/v1/forecast"
        params = {
            "latitude": lat,
            "longitude": lon,
            "hourly": "temperature_2m,relativehumidity_2m,precipitation,cloudcover,uv_index,visibility", # Added more
            "current_weather": True,
            "timezone": "auto"
        }
        res = requests.get(url, params=params, timeout=5).json()
        
        # Find the index for the current hour
        current_time_str = res.get("current_weather", {}).get("time")
        hourly_times = res.get("hourly", {}).get("time", [])
        
        # Default to 0, but try to find actual current hour index
        idx = hourly_times.index(current_time_str) if current_time_str in hourly_times else 0

        hourly = res.get("hourly", {})
        return {
            "temperature": hourly.get("temperature_2m", [28])[idx],
            "humidity": hourly.get("relativehumidity_2m", [60])[idx],
            "rain": hourly.get("precipitation", [0])[idx],
            "cloudcover": hourly.get("cloudcover", [40])[idx],
            "uv_index": hourly.get("uv_index", [0])[idx],           # New
            "visibility": hourly.get("visibility", [10000])[idx],   # New
            "windspeed": res.get("current_weather", {}).get("windspeed", 10)
        }
    except Exception as e:
        print(f"Weather error: {e}")
        return {}

# ---------------- TRAFFIC ----------------
def get_traffic(lat, lon):
    try:
        url = "https://api.tomtom.com/traffic/services/4/flowSegmentData/absolute/10/json"

        res = requests.get(url, params={
            "point": f"{lat},{lon}",
            "key": TOMTOM_API_KEY
        }, timeout=5).json()

        data = res.get("flowSegmentData", {})

        speed = data.get("currentSpeed", 30)
        free = data.get("freeFlowSpeed", 50)

        congestion = 1 - (speed / free) if free else 0

        return speed, free, congestion

    except:
        return 30, 50, 0.3

# ---------------- FEATURES ----------------
def create_features(weather, now):

    temp = weather.get("temperature", 28)
    humidity = weather.get("humidity", 60)
    rain = weather.get("rain", 0)
    cloud = weather.get("cloudcover", 40)
    wind = weather.get("windspeed", 10)

    # 🔥 Basic combined features (Original 12)
    temp_humidity = temp * humidity
    rain_intensity = rain * cloud
    weather_severity = (
        temp * 0.3 +
        humidity * 0.2 +
        cloud * 0.2 +
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
        "clouds_all": cloud,
        "humidity": humidity,
        "wind": wind,
        "is_holiday": 0,

        # Combined weather features
        "temp_humidity": temp_humidity,
        "rain_intensity": rain_intensity,
        "weather_severity": weather_severity,
    }])

# ---------------- HISTORY SUPPORT ----------------
def classify_traffic(actual):
    if actual < 2000:
        return "Low"
    elif actual < 4000:
        return "Medium"
    return "High"


def get_hourly_weather(lat, lon, hours=6):
    now = datetime.now()
    start_date = (now - timedelta(hours=hours)).date().isoformat()
    end_date = now.date().isoformat()
    try:
        url = "https://api.open-meteo.com/v1/forecast"
        params = {
            "latitude": lat,
            "longitude": lon,
            "hourly": "temperature_2m,relativehumidity_2m,precipitation,cloudcover,wind_speed_10m,uv_index,visibility",
            "timezone": "auto",
            "start_date": start_date,
            "end_date": end_date
        }
        res = requests.get(url, params=params, timeout=8)
        res.raise_for_status()
        payload = res.json()
        hourly = payload.get("hourly", {})
        times = hourly.get("time", [])

        weather_map = {}
        for idx, t in enumerate(times):
            weather_map[t] = {
                "temperature": hourly.get("temperature_2m", [28])[idx],
                "humidity": hourly.get("relativehumidity_2m", [60])[idx],
                "rain": hourly.get("precipitation", [0])[idx],
                "cloudcover": hourly.get("cloudcover", [40])[idx],
                "uv_index": hourly.get("uv_index", [0])[idx],
                "visibility": hourly.get("visibility", [10000])[idx],
                "windspeed": hourly.get("wind_speed_10m", [10])[idx]
            }
        return weather_map
    except Exception as e:
        print(f"Hourly weather error: {e}")
        return {}


def build_history(lat, lon, hours=6):
    history = []
    weather_map = get_hourly_weather(lat, lon, hours=hours)
    now = datetime.now()
    for offset in range(hours, -1, -1):
        point = now - timedelta(hours=offset)
        timestamp = point.strftime("%Y-%m-%d %H:00")
        weather = weather_map.get(point.strftime("%Y-%m-%dT%H:00"), {})
        if not weather:
            weather = get_weather(lat, lon)

        predicted = predict_volume(weather, point)
        speed, free, congestion = get_traffic(lat, lon)
        actual = predicted * (1 + congestion)
        history.append({
            "timestamp": timestamp,
            "predicted_volume": round(predicted, 2),
            "actual_volume": round(actual, 2),
            "speed": round(speed, 1),
            "traffic_level": classify_traffic(actual)
        })
    return history


def build_forecast(lat, lon, hours=12):
    now = datetime.now()
    end_time = now + timedelta(hours=hours)
    start_date = now.date().isoformat()
    end_date = end_time.date().isoformat()

    try:
        url = "https://api.open-meteo.com/v1/forecast"
        params = {
            "latitude": lat,
            "longitude": lon,
            "hourly": "temperature_2m,relativehumidity_2m,precipitation,cloudcover,wind_speed_10m,uv_index,visibility",
            "timezone": "auto",
            "start_date": start_date,
            "end_date": end_date
        }
        res = requests.get(url, params=params, timeout=8)
        res.raise_for_status()
        payload = res.json()
        hourly = payload.get("hourly", {})
        times = hourly.get("time", [])

        forecast = []
        speed, free, congestion = get_traffic(lat, lon)
        for idx, time_str in enumerate(times):
            try:
                time_dt = datetime.fromisoformat(time_str)
            except Exception:
                continue
            if time_dt < now or time_dt > end_time:
                continue

            weather = {
                "temperature": hourly.get("temperature_2m", [28])[idx],
                "humidity": hourly.get("relativehumidity_2m", [60])[idx],
                "rain": hourly.get("precipitation", [0])[idx],
                "cloudcover": hourly.get("cloudcover", [40])[idx],
                "uv_index": hourly.get("uv_index", [0])[idx],
                "visibility": hourly.get("visibility", [10000])[idx],
                "windspeed": hourly.get("wind_speed_10m", [10])[idx]
            }
            predicted = predict_volume(weather, time_dt)
            adjusted_volume = predicted * (1 + min(congestion, 0.8) * 0.35)
            forecast.append({
                "time": time_dt.strftime("%Y-%m-%dT%H:00"),
                "temperature": round(weather["temperature"], 1),
                "humidity": int(weather["humidity"]),
                "rain": round(weather["rain"], 1),
                "cloudcover": int(weather["cloudcover"]),
                "wind": round(weather["windspeed"], 1),
                "visibility": int(weather["visibility"]),
                "predicted_volume": round(adjusted_volume, 1),
                "location_congestion": round(congestion, 2),
                "location_speed": round(speed, 1)
            })

        return forecast
    except Exception as e:
        print(f"Forecast error: {e}")
        return []


def geocode_place(query):
    if not query:
        return None

    try:
        url = "https://nominatim.openstreetmap.org/search"
        params = {
            "q": f"{query}, Mumbai",
            "format": "json",
            "limit": 1,
            "addressdetails": 1
        }
        headers = {"User-Agent": "Mumbai-Traffic-Dashboard/1.0"}
        res = requests.get(url, params=params, headers=headers, timeout=8)
        if res.status_code == 200:
            data = res.json()
            if data:
                item = data[0]
                return {
                    "name": item.get("display_name", query),
                    "lat": float(item["lat"]),
                    "lon": float(item["lon"])
                }
    except Exception as e:
        print(f"Geocode error for '{query}': {e}")
    return None


def get_route_points(src_lat, src_lon, dst_lat, dst_lon, route_type="shortest"):
    try:
        url = f"https://api.tomtom.com/routing/1/calculateRoute/{src_lat},{src_lon}:{dst_lat},{dst_lon}/json"
        params = {
            "key": TOMTOM_API_KEY,
            "routeType": route_type,
            "traffic": "true"
        }
        res = requests.get(url, params=params, timeout=10)
        res.raise_for_status()
        payload = res.json()
        route = payload.get("routes", [])[0]
        summary = route.get("summary", {})
        legs = route.get("legs", [])
        points = []
        if legs:
            for leg in legs:
                for point in leg.get("points", []):
                    points.append([point.get("latitude"), point.get("longitude")])

        return {
            "distance": summary.get("lengthInMeters", 0),
            "time": summary.get("travelTimeInSeconds", 0),
            "points": points
        }
    except Exception as e:
        print(f"Route fetch error: {e}")
        return {"distance": 0, "time": 0, "points": []}


@app.route("/routes")
def routes():
    src = request.args.get("src", "").strip()
    dst = request.args.get("dst", "").strip()
    if not src or not dst:
        return jsonify({"error": "src and dst are required"}), 400

    src_place = geocode_place(src)
    dst_place = geocode_place(dst)
    if not src_place or not dst_place:
        return jsonify({"error": "Unable to geocode source or destination"}), 400

    weather = get_weather(src_place["lat"], src_place["lon"])
    predicted = predict_volume(weather, datetime.now())
    speed, free, actual_congestion = get_traffic(src_place["lat"], src_place["lon"])

    # Calculate predicted congestion based on model prediction vs baseline
    # Assuming baseline volume of 1500 (light traffic), higher volumes indicate congestion
    baseline_volume = 1500
    predicted_congestion = max(0, min(1, (predicted - baseline_volume) / (baseline_volume * 2)))

    route_types = ["shortest", "fastest", "eco", "thrilling"]
    routes = []
    for idx, route_type in enumerate(route_types):
        route_data = get_route_points(src_place["lat"], src_place["lon"], dst_place["lat"], dst_place["lon"], route_type=route_type)
        routes.append({
            "distance": route_data["distance"],
            "time": route_data["time"],
            "predicted_volume": round(predicted, 2),
            "predicted_congestion": round(predicted_congestion, 2),
            "actual_congestion": round(actual_congestion, 2),
            "speed": round(speed, 1),
            "traffic_level": classify_traffic(predicted * (1 + actual_congestion)),
            "points": route_data["points"],
            "type": route_type.title()
        })

    return jsonify({
        "source": src_place,
        "destination": dst_place,
        "routes": routes
    })


# ---------------- PREDICT ----------------
def predict_volume(weather, now):
    try:
        X = create_features(weather, now)
        return float(model.predict(X)[0])
    except Exception as e:
        print(f"Prediction error: {e}")
        return 2000

# ---------------- MAIN API ----------------
@app.route("/predict")
def predict():

    lat = float(request.args.get("lat"))
    lon = float(request.args.get("lon"))

    now = datetime.now()

    weather = get_weather(lat, lon)
    predicted = predict_volume(weather, now)

    speed, free, congestion = get_traffic(lat, lon)

    actual = predicted * (1 + congestion)

    # 🔥 dynamic classification
    if actual < 2000:
        level = "Low"
    elif actual < 4000:
        level = "Medium"
    else:
        level = "High"

    return jsonify({
        "traffic_level": level,
        "predicted_volume": round(predicted, 2),
        "actual_volume": round(actual, 2),
        "speed": speed,
        "weather": weather,
        "place": reverse_geocode(lat, lon),
        "lat": lat,
        "lon": lon,
        "timestamp": now.strftime("%I:%M:%S %p")
    })

@app.route("/history")
def history():
    lat = float(request.args.get("lat", 19.0760))
    lon = float(request.args.get("lon", 72.8777))
    hours = int(request.args.get("hours", 6))
    hours = min(max(hours, 3), 12)
    return jsonify({
        "history": build_history(lat, lon, hours=hours),
        "place": reverse_geocode(lat, lon)
    })


def generate_incidents(lat, lon):
    now = datetime.now()
    time_slot = now.hour * 60 + now.minute
    seed = int(round(lat * 1000)) ^ int(round(lon * 1000)) ^ time_slot
    rnd = random.Random(seed)

    incident_templates = {
        "Accident": {
            "desc": [
                "Minor collision causing slow traffic.",
                "Two-vehicle crash slowing one lane.",
                "Rear-end collision near the intersection."
            ],
            "places": [
                "Main junction",
                "Crossing point",
                "Flyover entrance"
            ],
            "colors": "red"
        },
        "Traffic": {
            "desc": [
                "Heavy congestion due to peak flow.",
                "Traffic is backed up through the area.",
                "Slow-moving traffic from a late arrival."
            ],
            "places": [
                "Market area",
                "Highway entrance",
                "Bus depot stretch"
            ],
            "colors": "orange"
        },
        "Construction": {
            "desc": [
                "Roadwork ahead, expect lane closures.",
                "Maintenance crew working on the pavement.",
                "Utility repair closing one lane."
            ],
            "places": [
                "Construction zone",
                "Repair site",
                "Maintenance corridor"
            ],
            "colors": "blue"
        },
        "Road Closure": {
            "desc": [
                "Temporary closure for maintenance.",
                "Emergency work has closed the road.",
                "Detour in place due to local closure."
            ],
            "places": [
                "Service road",
                "Connector road",
                "Access lane"
            ],
            "colors": "darkred"
        },
        "Other": {
            "desc": [
                "Street event causing minor delays.",
                "Signal outage slowing the intersection.",
                "Unexpected obstruction on the route."
            ],
            "places": [
                "Nearby street",
                "Local road",
                "Market lane"
            ],
            "colors": "gray"
        }
    }

    count = rnd.randint(2, 5)
    incidents = []
    for i in range(count):
        incident_type = rnd.choice(list(incident_templates.keys()))
        template = incident_templates[incident_type]
        offset_lat = rnd.uniform(-0.015, 0.015)
        offset_lon = rnd.uniform(-0.015, 0.015)
        delay = f"{rnd.randint(5, 35)} mins"
        incidents.append({
            "type": incident_type,
            "description": rnd.choice(template["desc"]),
            "delay": delay,
            "place": f"{rnd.choice(template['places'])}",
            "lat": lat + offset_lat,
            "lon": lon + offset_lon,
            "updated_at": now.strftime("%H:%M")
        })

    return incidents


@app.route("/forecast")
def forecast():
    try:
        lat = float(request.args.get("lat", 19.0760))
        lon = float(request.args.get("lon", 72.8777))
    except Exception:
        lat = 19.0760
        lon = 72.8777

    return jsonify(build_forecast(lat, lon, hours=12))


@app.route("/incidents")
def incidents():
    try:
        lat = float(request.args.get("lat", 19.0760))
        lon = float(request.args.get("lon", 72.8777))
    except Exception:
        lat = 19.0760
        lon = 72.8777

    return jsonify(generate_incidents(lat, lon))


@app.route("/")
def home():
    return "Server running"

if __name__ == "__main__":
    app.run(debug=True)