import folium, json
from streamlit_folium import st_folium
import streamlit as st

colors = ["green","orange","red"]

def show_map(data):
    st.title("🚦 Mumbai Traffic Map")

    m = folium.Map(location=[19.0728,72.8826], zoom_start=13)

    with open("static/geojson_routes.json") as f:
        routes = json.load(f)

    for feature in routes["features"]:
        name = feature["properties"]["route"]

        route_pred = (data["prediction"] + hash(name)%3)%3

        folium.GeoJson(
            feature,
            style_function=lambda x,p=route_pred: {
                "color": colors[p],
                "weight": 6
            },
            tooltip=f"{name} - {['Low','Moderate','Heavy'][route_pred]}"
        ).add_to(m)

    st_folium(m, width=1000, height=500)

    st.subheader("Prediction")
    st.success(f"Traffic Volume: {int(data['volume'])}")