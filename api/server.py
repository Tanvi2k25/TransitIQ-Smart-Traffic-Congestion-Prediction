import os
import sys
import math
import time
import subprocess
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor
from statistics import mean

import joblib
import numpy as np
import pandas as pd
import requests
from dotenv import load_dotenv
from flask import Flask, jsonify, request

# ---------------- CONFIGURATION ----------------
BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

load_dotenv(os.path.join(BASE, ".env"))
TOMTOM_API_KEY = os.getenv("TOMTOM_API_KEY", "").strip()

app = Flask(__name__)
INCIDENT_CACHE = {}
INCIDENT_CACHE_SECONDS = 60
WEATHER_CACHE = {}
INCIDENT_RADIUS_KM = 10

MODEL_PATH = os.path.join(BASE, "model", "model.pkl")
TRAIN_SCRIPT = os.path.join(BASE, "train_model.py")

# Automatically train the model if it does not exist.
if not os.path.exists(MODEL_PATH):
    print("Model not found. Starting model training...")

    if not os.path.exists(TRAIN_SCRIPT):
        raise FileNotFoundError(
            f"Training script not found: {TRAIN_SCRIPT}"
        )

    subprocess.run(
        [sys.executable, TRAIN_SCRIPT],
        cwd=BASE,
        check=True
    )

if not os.path.exists(MODEL_PATH):
    raise FileNotFoundError(
        f"Model was not created: {MODEL_PATH}"
    )

model = joblib.load(MODEL_PATH)
print(f"TransitIQ model loaded successfully: {type(model).__name__}")


# ---------------- LOCATION NAME ----------------
def reverse_geocode(lat, lon):
    """Return a readable locality name, with Mumbai as fallback."""
    try:
        url = "https://nominatim.openstreetmap.org/reverse"
        params = {
            "lat": lat,
            "lon": lon,
            "format": "json",
            "zoom": 16,
            "addressdetails": 1,
        }
        headers = {"User-Agent": "TransitIQ-Traffic-Dashboard/1.0"}

        response = requests.get(
            url, params=params, headers=headers, timeout=(2, 3)
        )
        response.raise_for_status()

        address = response.json().get("address", {})
        name = (
            address.get("neighbourhood")
            or address.get("neighborhood")
            or address.get("suburb")
            or address.get("village")
            or address.get("town")
            or address.get("municipality")
        )

        if name:
            return name

    except Exception as exc:
        print(f"Nominatim reverse-geocoding error: {exc}")

    if TOMTOM_API_KEY:
        try:
            url = (
                "https://api.tomtom.com/search/2/reverseGeocode/"
                f"{lat},{lon}.json"
            )
            response = requests.get(
                url,
                params={"key": TOMTOM_API_KEY},
                timeout=(2, 3)
            )
            response.raise_for_status()

            addresses = response.json().get("addresses", [])
            if addresses:
                address = addresses[0].get("address", {})
                return (
                    address.get("municipalitySubdivision")
                    or address.get("municipality")
                    or "Mumbai"
                )

        except Exception as exc:
            print(f"TomTom reverse-geocoding error: {exc}")

    return "Mumbai"


# ---------------- WEATHER ----------------
def get_weather(lat, lon):
    """Fetch current weather context from Open-Meteo."""
    cache_key = (round(float(lat), 3), round(float(lon), 3))
    cached = WEATHER_CACHE.get(cache_key)
    if cached and time.time() - cached["saved_at"] < 300:
        return dict(cached["value"])
    try:
        url = "https://api.open-meteo.com/v1/forecast"
        params = {
            "latitude": lat,
            "longitude": lon,
            "current": (
                "temperature_2m,relative_humidity_2m,precipitation,"
                "cloud_cover,uv_index,visibility,wind_speed_10m,is_day"
            ),
            "timezone": "auto",
        }

        response = requests.get(url, params=params, timeout=(2, 4))
        response.raise_for_status()
        payload = response.json()

        current = payload.get("current", {})

        result = {
            "temperature": current.get("temperature_2m", 28),
            "humidity": current.get("relative_humidity_2m", 60),
            "rain": current.get("precipitation", 0),
            "cloudcover": current.get("cloud_cover", 40),
            "uv_index": current.get("uv_index", 0),
            "visibility": current.get("visibility", 10000),
            "windspeed": current.get("wind_speed_10m", 10),
            "is_day": current.get("is_day"),
            "source": "Open-Meteo",
        }
        WEATHER_CACHE[cache_key] = {"saved_at": time.time(), "value": result}
        return result

    except Exception as exc:
        print(f"Weather error: {exc}")
        if cached:
            app.logger.warning("Using cached weather after provider failure.")
            return dict(cached["value"])
        fallback = {
            "temperature": 28,
            "humidity": 60,
            "rain": 0,
            "cloudcover": 40,
            "uv_index": 0,
            "visibility": 10000,
            "is_day": None,
            "windspeed": 10,
            "source": "Fallback estimate",
        }
        WEATHER_CACHE[cache_key] = {"saved_at": time.time(), "value": fallback}
        return dict(fallback)


# ---------------- TOMTOM TRAFFIC ----------------
def get_traffic(lat, lon):
    """
    Fetch traffic flow for one coordinate.
    Fallback values are estimates, not measured live observations.
    """
    if not TOMTOM_API_KEY:
        return 30, 50, 0.3, "Fallback estimate"

    try:
        url = (
            "https://api.tomtom.com/traffic/services/4/"
            "flowSegmentData/absolute/10/json"
        )

        response = requests.get(
            url,
            params={
                "point": f"{lat},{lon}",
                "key": TOMTOM_API_KEY,
            },
            timeout=(2, 4)
        )
        response.raise_for_status()

        data = response.json().get("flowSegmentData", {})
        speed = data.get("currentSpeed")
        free_speed = data.get("freeFlowSpeed")

        if speed is None or free_speed is None or float(free_speed) <= 0:
            raise ValueError("Invalid TomTom speed data")

        congestion = max(
            0.0,
            min(1.0, 1.0 - float(speed) / float(free_speed))
        )

        return float(speed), float(free_speed), congestion, "TomTom Traffic Flow"

    except Exception as exc:
        print(f"Traffic flow error: {exc}")
        return 30, 50, 0.3, "Fallback estimate"


def get_traffic_at_point(lat, lon):
    """Return one real TomTom flow observation, or None."""
    if not TOMTOM_API_KEY:
        return None

    try:
        url = (
            "https://api.tomtom.com/traffic/services/4/"
            "flowSegmentData/absolute/10/json"
        )

        response = requests.get(
            url,
            params={
                "point": f"{lat},{lon}",
                "key": TOMTOM_API_KEY,
            },
            timeout=(2, 4)
        )
        response.raise_for_status()

        segment = response.json().get("flowSegmentData", {})
        current_speed = segment.get("currentSpeed")
        free_flow_speed = segment.get("freeFlowSpeed")

        if current_speed is None or free_flow_speed is None:
            return None

        current_speed = float(current_speed)
        free_flow_speed = float(free_flow_speed)

        if free_flow_speed <= 0:
            return None

        congestion = max(
            0.0,
            min(1.0, 1.0 - current_speed / free_flow_speed)
        )

        return {
            "speed": current_speed,
            "free_speed": free_flow_speed,
            "congestion": congestion,
        }

    except Exception as exc:
        print(
            f"TomTom route traffic lookup failed at "
            f"{lat},{lon}: {exc}"
        )
        return None


# ---------------- ROUTE DISTANCE HELPERS ----------------
def haversine_km(point1, point2):
    """Calculate distance between two [latitude, longitude] points."""
    lat1, lon1 = map(math.radians, point1)
    lat2, lon2 = map(math.radians, point2)

    dlat = lat2 - lat1
    dlon = lon2 - lon1

    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(lat1) * math.cos(lat2)
        * math.sin(dlon / 2) ** 2
    )

    return 6371.0 * 2 * math.atan2(
        math.sqrt(a),
        math.sqrt(1 - a)
    )


def get_route_traffic(points):
    """
    Sample up to five geographically distributed points along a route.

    Returns average, minimum and maximum congestion and speed
    using successful TomTom observations only.
    """
    if not points:
        return None

    valid_points = []

    for point in points:
        if (
            isinstance(point, (list, tuple))
            and len(point) >= 2
            and point[0] is not None
            and point[1] is not None
        ):
            try:
                valid_points.append([
                    float(point[0]),
                    float(point[1])
                ])
            except (TypeError, ValueError):
                continue

    if not valid_points:
        return None

    # Calculate cumulative distance along the route.
    cumulative_distances = [0.0]

    for i in range(1, len(valid_points)):
        segment_distance = haversine_km(
            valid_points[i - 1],
            valid_points[i]
        )
        cumulative_distances.append(
            cumulative_distances[-1] + segment_distance
        )

    total_distance = cumulative_distances[-1]

    if total_distance <= 0:
        sample_points = [valid_points[0]]
    else:
        # Select five target positions from 10% to 90% of route length.
        target_distances = np.linspace(
            total_distance * 0.10,
            total_distance * 0.90,
            num=min(5, len(valid_points))
        )

        selected_indices = []

        for target in target_distances:
            nearest_index = min(
                range(len(cumulative_distances)),
                key=lambda i: abs(cumulative_distances[i] - target)
            )
            selected_indices.append(nearest_index)

        # Remove repeated coordinates.
        sample_points = []
        seen = set()

        for index in selected_indices:
            point = valid_points[index]
            coordinate_key = (
                round(point[0], 5),
                round(point[1], 5)
            )

            if coordinate_key not in seen:
                seen.add(coordinate_key)
                sample_points.append(point)

    if not sample_points:
        return None

    with ThreadPoolExecutor(
        max_workers=min(5, len(sample_points))
    ) as pool:
        observations = list(
            pool.map(
                lambda point: get_traffic_at_point(
                    point[0], point[1]
                ),
                sample_points
            )
        )

    successful = [
        item for item in observations
        if item is not None
    ]

    if not successful:
        return None

    congestion_values = [
        item["congestion"] for item in successful
    ]
    speed_values = [
        item["speed"] for item in successful
    ]

    return {
        "congestion": round(mean(congestion_values), 3),
        "congestion_min": round(min(congestion_values), 3),
        "congestion_max": round(max(congestion_values), 3),
        "speed": round(mean(speed_values), 1),
        "speed_min": round(min(speed_values), 1),
        "speed_max": round(max(speed_values), 1),
        "samples": len(successful),
    }


# ---------------- MODEL FEATURES ----------------
def create_features(weather, now):
    temp = float(weather.get("temperature", 28) or 28)
    humidity = float(weather.get("humidity", 60) or 60)
    rain = float(weather.get("rain", 0) or 0)
    cloud = float(weather.get("cloudcover", 40) or 40)
    wind = float(weather.get("windspeed", 10) or 10)

    temp_humidity = temp * humidity
    rain_intensity = rain * cloud

    weather_severity = (
        temp * 0.3
        + humidity * 0.2
        + cloud * 0.2
        + wind * 0.1
        + rain * 0.2
    )

    dew_point = temp - ((100 - humidity) / 5.0)

    heat_index = 0.5 * (
        temp + 61.0 + ((temp - 68.0) * 1.2)
        + (humidity * 0.094)
    )

    wind_chill = (
        13.12
        + (0.6215 * temp)
        - (11.37 * (wind ** 0.16))
        + (0.3965 * temp * (wind ** 0.16))
    )

    abs_humidity = (
        6.112
        * np.exp((17.67 * temp) / (temp + 243.5))
        * humidity / 100
    ) / 100

    rain_humidity_ratio = rain / (humidity + 1)
    cloud_wind_interaction = cloud * wind
    humidity_comfort = abs(humidity - 45)

    is_hot = 1 if temp > 30 else 0
    is_cold = 1 if temp < 15 else 0
    is_rain = 1 if rain > 0 else 0

    weather_stability = abs(wind) + abs(cloud - 50) / 100
    high_clouds = 1 if cloud > 70 else 0
    low_clouds = 1 if cloud < 30 else 0

    discomfort_index = (
        (0.4 * (temp + heat_index) / 2)
        + (0.6 * humidity) - 20
    )

    heat_index = np.clip(heat_index, 20, 60)
    wind_chill = np.clip(wind_chill, -50, 50)
    discomfort_index = np.clip(discomfort_index, 0, 100)

    feature_values = {
        "hour": now.hour,
        "day": now.weekday(),
        "month": now.month,
        "temp": temp,
        "rain_1h": rain,
        "clouds_all": cloud,
        "humidity": humidity,
        "wind": wind,
        "is_holiday": 0,
        "temp_humidity": temp_humidity,
        "rain_intensity": rain_intensity,
        "weather_severity": weather_severity,
        "dew_point": dew_point,
        "heat_index": heat_index,
        "wind_chill": wind_chill,
        "abs_humidity": abs_humidity,
        "rain_humidity_ratio": rain_humidity_ratio,
        "cloud_wind_interaction": cloud_wind_interaction,
        "humidity_comfort": humidity_comfort,
        "is_hot": is_hot,
        "is_cold": is_cold,
        "is_rain": is_rain,
        "weather_stability": weather_stability,
        "high_clouds": high_clouds,
        "low_clouds": low_clouds,
        "discomfort_index": discomfort_index,
    }

    feature_order = [
        "hour", "day", "month",
        "temp", "rain_1h", "clouds_all",
        "humidity", "wind", "is_holiday",
        "temp_humidity", "rain_intensity", "weather_severity",
        "dew_point", "heat_index", "wind_chill", "abs_humidity",
        "rain_humidity_ratio", "cloud_wind_interaction",
        "humidity_comfort", "is_hot", "is_cold", "is_rain",
        "weather_stability", "high_clouds", "low_clouds",
        "discomfort_index",
    ]

    return pd.DataFrame(
        [[feature_values[name] for name in feature_order]],
        columns=feature_order
    )


def predict_volume(weather, now):
    try:
        features = create_features(weather, now)
        prediction = float(model.predict(features)[0])

        print(f"Predicted traffic volume: {prediction:.2f}")
        return max(0.0, prediction)

    except Exception as exc:
        print(f"Prediction error: {exc}")
        return 2000.0


# ---------------- HISTORY AND FORECAST SUPPORT ----------------
def classify_traffic(volume):
    if volume < 2000:
        return "Low"
    if volume < 4000:
        return "Medium"
    return "High"


def get_hourly_weather(lat, lon, hours=6):
    now = datetime.now()
    start_date = (
        now - timedelta(hours=hours)
    ).date().isoformat()
    end_date = now.date().isoformat()

    try:
        url = "https://api.open-meteo.com/v1/forecast"

        params = {
            "latitude": lat,
            "longitude": lon,
            "hourly": (
                "temperature_2m,relative_humidity_2m,precipitation,"
                "cloud_cover,wind_speed_10m,uv_index,visibility"
            ),
            "timezone": "auto",
            "start_date": start_date,
            "end_date": end_date,
        }

        response = requests.get(url, params=params, timeout=(2, 4))
        response.raise_for_status()

        hourly = response.json().get("hourly", {})
        weather_map = {}

        for idx, time_text in enumerate(hourly.get("time", [])):

            def value(key, default):
                values = hourly.get(key, [])
                return (
                    values[idx]
                    if idx < len(values) and values[idx] is not None
                    else default
                )

            weather_map[time_text] = {
                "temperature": value("temperature_2m", 28),
                "humidity": value("relative_humidity_2m", 60),
                "rain": value("precipitation", 0),
                "cloudcover": value("cloud_cover", 40),
                "uv_index": value("uv_index", 0),
                "visibility": value("visibility", 10000),
                "windspeed": value("wind_speed_10m", 10),
            }

        return weather_map

    except Exception as exc:
        print(f"Hourly weather error: {exc}")
        return {}


def build_history(lat, lon, hours=6):
    history = []

    weather_map = get_hourly_weather(lat, lon, hours)
    fallback_weather = get_weather(lat, lon)
    speed, _free, congestion, traffic_source = get_traffic(lat, lon)

    now = datetime.now()

    for offset in range(hours, -1, -1):
        point = now - timedelta(hours=offset)

        timestamp = point.strftime("%Y-%m-%d %H:00")
        weather_key = point.strftime("%Y-%m-%dT%H:00")

        weather = weather_map.get(weather_key, fallback_weather)

        predicted = predict_volume(weather, point)
        estimated_value = predicted * (1 + congestion)

        history.append({
            "timestamp": timestamp,
            "predicted_volume": round(predicted, 2),
            "estimated_volume": round(estimated_value, 2),
            "speed": round(speed, 1),
            "traffic_congestion": round(congestion, 3) if traffic_source == "TomTom Traffic Flow" else None,
            "traffic_source": traffic_source,
            "traffic_level": classify_traffic(estimated_value),
        })

    return history


def build_forecast(lat, lon, hours=12):
    now = datetime.now()
    end_time = now + timedelta(hours=hours)

    try:
        url = "https://api.open-meteo.com/v1/forecast"

        params = {
            "latitude": lat,
            "longitude": lon,
            "hourly": (
                "temperature_2m,relative_humidity_2m,precipitation,"
                "cloud_cover,wind_speed_10m,uv_index,visibility"
            ),
            "timezone": "auto",
            "forecast_days": 2,
        }

        response = requests.get(url, params=params, timeout=(2, 4))
        response.raise_for_status()

        hourly = response.json().get("hourly", {})
        times = hourly.get("time", [])

        speed, _free, congestion, traffic_source = get_traffic(lat, lon)
        forecast_rows = []

        for idx, time_text in enumerate(times):
            try:
                time_dt = datetime.fromisoformat(time_text)
            except ValueError:
                continue

            if time_dt < now or time_dt > end_time:
                continue

            def value(key, default):
                values = hourly.get(key, [])
                return (
                    values[idx]
                    if idx < len(values) and values[idx] is not None
                    else default
                )

            weather = {
                "temperature": value("temperature_2m", 28),
                "humidity": value("relative_humidity_2m", 60),
                "rain": value("precipitation", 0),
                "cloudcover": value("cloud_cover", 40),
                "uv_index": value("uv_index", 0),
                "visibility": value("visibility", 10000),
                "windspeed": value("wind_speed_10m", 10),
            }

            predicted = predict_volume(weather, time_dt)

            adjusted = predicted * (
                1 + min(max(congestion, 0), 0.8) * 0.35
            )

            forecast_rows.append({
                "time": time_dt.strftime("%Y-%m-%dT%H:00"),
                "temperature": round(weather["temperature"], 1),
                "humidity": int(weather["humidity"]),
                "rain": round(weather["rain"], 1),
                "cloudcover": int(weather["cloudcover"]),
                "wind": round(weather["windspeed"], 1),
                "visibility": int(weather["visibility"]),
                "predicted_volume": round(adjusted, 1),
                "location_congestion": round(congestion, 2),
                "location_speed": round(speed, 1),
                "traffic_source": traffic_source,
            })

        return forecast_rows

    except Exception as exc:
        print(f"Forecast error: {exc}")
        return []


# ---------------- GEOCODING AND ROUTING ----------------
def geocode_place(query):
    if not query:
        return None

    try:
        url = "https://nominatim.openstreetmap.org/search"

        params = {
            "q": f"{query}, Mumbai",
            "format": "json",
            "limit": 1,
            "addressdetails": 1,
        }

        headers = {"User-Agent": "TransitIQ-Traffic-Dashboard/1.0"}

        response = requests.get(
            url, params=params, headers=headers, timeout=(2, 4)
        )
        response.raise_for_status()

        results = response.json()

        if results:
            item = results[0]

            return {
                "name": item.get("display_name", query),
                "lat": float(item["lat"]),
                "lon": float(item["lon"]),
            }

    except Exception as exc:
        print(f"Geocode error for '{query}': {exc}")

    return None


def get_route_points(
    src_lat, src_lon, dst_lat, dst_lon,
    route_type="shortest"
):
    if not TOMTOM_API_KEY:
        print("TomTom API key is missing; cannot request routes.")
        return {"distance": 0, "time": 0, "points": []}

    try:
        url = (
            "https://api.tomtom.com/routing/1/calculateRoute/"
            f"{src_lat},{src_lon}:{dst_lat},{dst_lon}/json"
        )

        params = {
            "key": TOMTOM_API_KEY,
            "routeType": route_type,
            "traffic": "true",
        }

        response = requests.get(url, params=params, timeout=12)
        response.raise_for_status()

        route_list = response.json().get("routes", [])

        if not route_list:
            return {"distance": 0, "time": 0, "points": []}

        route = route_list[0]
        summary = route.get("summary", {})

        points = []

        for leg in route.get("legs", []):
            for point in leg.get("points", []):
                lat = point.get("latitude")
                lon = point.get("longitude")

                if lat is not None and lon is not None:
                    points.append([float(lat), float(lon)])

        return {
            "distance": summary.get("lengthInMeters", 0),
            "time": summary.get("travelTimeInSeconds", 0),
            "points": points,
        }

    except Exception as exc:
        print(f"Route fetch error ({route_type}): {exc}")
        return {"distance": 0, "time": 0, "points": []}


# ---------------- ROUTES API ----------------
@app.route("/routes")
def routes():
    src = request.args.get("src", "").strip()
    dst = request.args.get("dst", "").strip()

    if not src or not dst:
        return jsonify({
            "error": "src and dst are required"
        }), 400

    if not TOMTOM_API_KEY:
        return jsonify({
            "error": (
                "TomTom API key is missing. "
                "Add TOMTOM_API_KEY to the project .env file."
            )
        }), 503

    src_place = geocode_place(src)
    dst_place = geocode_place(dst)

    if not src_place or not dst_place:
        return jsonify({
            "error": "Unable to geocode source or destination in Mumbai."
        }), 400

    # Shared source-location model estimate.
    source_weather = get_weather(
        src_place["lat"], src_place["lon"]
    )
    shared_model_volume = predict_volume(
        source_weather, datetime.now()
    )

    route_types = [
        "shortest",
        "fastest",
        "eco",
        "thrilling"
    ]

    route_results = []

    for route_type in route_types:
        route_data = get_route_points(
            src_place["lat"],
            src_place["lon"],
            dst_place["lat"],
            dst_place["lon"],
            route_type=route_type
        )

        if (
            not route_data["points"]
            or route_data["distance"] <= 0
            or route_data["time"] <= 0
        ):
            continue

        route_traffic = get_route_traffic(
            route_data["points"]
        )

        if route_traffic is None:
            route_congestion = None
            congestion_min = None
            congestion_max = None

            route_speed = None
            speed_min = None
            speed_max = None

            traffic_level = "Unavailable"
            sample_count = 0
            congestion_source = "Unavailable"

        else:
            route_congestion = route_traffic["congestion"]
            congestion_min = route_traffic["congestion_min"]
            congestion_max = route_traffic["congestion_max"]

            route_speed = route_traffic["speed"]
            speed_min = route_traffic["speed_min"]
            speed_max = route_traffic["speed_max"]

            sample_count = route_traffic["samples"]

            if route_congestion < 0.25:
                traffic_level = "Low"
            elif route_congestion < 0.50:
                traffic_level = "Medium"
            else:
                traffic_level = "High"

            congestion_source = "TomTom Traffic Flow"

        route_results.append({
            "distance": route_data["distance"],
            "time": route_data["time"],
            "points": route_data["points"],
            "type": route_type.title(),

            "predicted_volume": round(
                shared_model_volume, 2
            ),

            "route_congestion": route_congestion,
            "congestion_min": congestion_min,
            "congestion_max": congestion_max,

            "speed": route_speed,
            "speed_min": speed_min,
            "speed_max": speed_max,

            "traffic_level": traffic_level,
            "traffic_samples": sample_count,
            "congestion_source": congestion_source,
        })

    if not route_results:
        return jsonify({
            "error": (
                "TomTom did not return any valid route alternatives. "
                "Check the places and API access."
            )
        }), 502

    return jsonify({
        "source": src_place,
        "destination": dst_place,
        "routes": route_results,
        "traffic_note": (
            "Route congestion is calculated from available TomTom "
            "traffic-flow observations sampled at up to five distributed "
            "points along each route. Model volume is a shared "
            "source-location estimate."
        ),
    })


# ---------------- PREDICT API ----------------
@app.route("/predict")
def predict():
    try:
        lat = float(request.args.get("lat"))
        lon = float(request.args.get("lon"))

    except (TypeError, ValueError):
        return jsonify({
            "error": "Valid lat and lon parameters are required."
        }), 400

    now = datetime.now()
    weather = get_weather(lat, lon)

    predicted = predict_volume(weather, now)
    speed, free_speed, congestion, traffic_source = get_traffic(lat, lon)

    estimated_value = predicted * (1 + congestion)

    return jsonify({
        "model_name": type(model).__name__,
        "traffic_level": classify_traffic(estimated_value),
        "predicted_volume": round(predicted, 2),
        "estimated_volume": round(estimated_value, 2),
        "speed": speed,
        "free_flow_speed": free_speed,
        "traffic_congestion": round(congestion, 3) if traffic_source == "TomTom Traffic Flow" else None,
        "traffic_source": traffic_source,
        "weather": weather,
        "place": reverse_geocode(lat, lon),
        "lat": lat,
        "lon": lon,
        "timestamp": now.strftime("%I:%M:%S %p"),
    })


# ---------------- HISTORY API ----------------
@app.route("/history")
def history():
    try:
        lat = float(request.args.get("lat", 19.0760))
        lon = float(request.args.get("lon", 72.8777))

        hours = min(
            max(int(request.args.get("hours", 6)), 3),
            12
        )

        return jsonify({
            "history": build_history(lat, lon, hours)
        })

    except Exception as exc:
        print(f"History API error: {exc}")
        return jsonify({"error": str(exc)}), 500


# ---------------- TOMTOM INCIDENTS ----------------
def generate_incidents(lat, lon):
    """Fetch and normalize live TomTom incidents around a location.

    A one-minute in-memory cache keeps the page usable during brief
    connectivity drops and avoids repeated API calls during reruns.
    """
    now = time.time()
    cache_key = (round(float(lat), 2), round(float(lon), 2))
    cached = INCIDENT_CACHE.get(cache_key)
    if cached and cached["expires_at"] > now:
        return cached["items"], "cache"
    if not TOMTOM_API_KEY:
        if cached and cached["items"]:
            return cached["items"], "stale-cache"
        return [], "unavailable"

    # Fetch only incidents that can appear inside the Home map's 10 km circle.
    lat_delta = INCIDENT_RADIUS_KM / 111.0
    lon_delta = INCIDENT_RADIUS_KM / (111.0 * max(math.cos(math.radians(lat)), 0.2))
    bbox = f"{lon-lon_delta},{lat-lat_delta},{lon+lon_delta},{lat+lat_delta}"
    fields = "{incidents{type,geometry{type,coordinates},properties{iconCategory,magnitudeOfDelay,events{description},startTime,endTime,from,to,length,delay,roadNumbers}}}"
    url = "https://api.tomtom.com/traffic/services/5/incidentDetails"
    try:
        response = requests.get(url, params={
            "key": TOMTOM_API_KEY,
            "bbox": bbox,
            "fields": fields,
            "language": "en-GB",
            "timeValidityFilter": "present",
        }, timeout=(3, 6))
        response.raise_for_status()
        payload = response.json()
        categories = {
            1: "Accident", 6: "Traffic", 7: "Road Closure",
            8: "Road Closure", 9: "Construction"
        }
        items = []
        for feature in payload.get("incidents", []):
            props = feature.get("properties", {})
            geometry = feature.get("geometry", {})
            coords = geometry.get("coordinates", [])
            # TomTom GeoJSON positions are [longitude, latitude].
            if geometry.get("type") == "Point" and len(coords) >= 2:
                point = coords
            elif coords and isinstance(coords[0], list):
                point = coords[0]
            else:
                point = [lon, lat]
            incident_lon, incident_lat = float(point[0]), float(point[1])
            distance_km = haversine_km([lat, lon], [incident_lat, incident_lon])
            if distance_km > INCIDENT_RADIUS_KM:
                continue
            events = props.get("events") or []
            description = next((e.get("description") for e in events if e.get("description")), None)
            category = props.get("iconCategory")
            try:
                category = int(category)
            except (TypeError, ValueError):
                category = -1
            delay_seconds = props.get("delay", 0) or 0
            place = props.get("roadNumbers") or props.get("from") or "Nearby road"
            if isinstance(place, list):
                place = ", ".join(str(part) for part in place)
            items.append({
                "type": categories.get(category, "Other"),
                "description": description or props.get("from") or "Traffic incident reported by TomTom.",
                "delay": f"{max(0, round(float(delay_seconds) / 60))} mins" if delay_seconds else "Not provided",
                "place": place,
                "lat": incident_lat, "lon": incident_lon,
                "distance_km": round(distance_km, 1),
                "updated_at": datetime.now().strftime("%H:%M"),
                "source": "TomTom Traffic Incidents",
                "start_time": props.get("startTime"),
                "end_time": props.get("endTime"),
            })
        INCIDENT_CACHE[cache_key] = {"expires_at": now + INCIDENT_CACHE_SECONDS, "items": items}
        return items, "live"
    except Exception as exc:
        app.logger.warning("TomTom incidents unavailable: %s", exc)
        if cached and cached["items"]:
            return cached["items"], "stale-cache"
        return [], "unavailable"


# ---------------- FORECAST API ----------------
@app.route("/forecast")
def forecast():
    try:
        lat = float(request.args.get("lat", 19.0760))
        lon = float(request.args.get("lon", 72.8777))

    except (TypeError, ValueError):
        lat, lon = 19.0760, 72.8777

    return jsonify(
        build_forecast(lat, lon, hours=12)
    )


# ---------------- INCIDENTS API ----------------
@app.route("/incidents")
def incidents():
    try:
        lat = float(request.args.get("lat", 19.0760))
        lon = float(request.args.get("lon", 72.8777))

    except (TypeError, ValueError):
        lat, lon = 19.0760, 72.8777

    items, source = generate_incidents(lat, lon)
    status = 200 if source != "unavailable" else 503
    response = jsonify({"incidents": items, "source": source})
    response.status_code = status
    return response


# ---------------- HOME ----------------
@app.route("/")
def home():
    return "TransitIQ Flask API is running."


if __name__ == "__main__":
    app.run(debug=False, threaded=True)
