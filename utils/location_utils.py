from geopy.geocoders import Nominatim

geolocator = Nominatim(user_agent="traffic_app")

def search_location(place):
    try:
        location = geolocator.geocode(place)
        return location.latitude, location.longitude
    except:
        return 19.0760, 72.8777  # Default Mumbai