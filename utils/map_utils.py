import requests
import random

def generate_routes(center):
    lat, lon = center

    routes = []
    for _ in range(4):
        end = (
            lat + random.uniform(-0.03, 0.03),
            lon + random.uniform(-0.03, 0.03)
        )
        routes.append((center, end))

    return routes

def get_route(start, end):
    url = f"http://router.project-osrm.org/route/v1/driving/{start[1]},{start[0]};{end[1]},{end[0]}?overview=full&geometries=geojson"
    
    try:
        res = requests.get(url).json()
        coords = res["routes"][0]["geometry"]["coordinates"]
        return [(c[1], c[0]) for c in coords]
    except:
        return []

def get_color(pred):
    return ["green","orange","red"][pred]