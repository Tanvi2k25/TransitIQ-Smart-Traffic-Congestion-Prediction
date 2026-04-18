import streamlit as st
import requests
import folium
from streamlit_folium import st_folium
from geopy.geocoders import Nominatim
import polyline
import time

st.title("Route Traffic Analysis")

geo = Nominatim(user_agent="route_app")

# ---------------- SESSION ----------------
if "map_html" not in st.session_state:
    st.session_state.map_html = None

if "last_update" not in st.session_state:
    st.session_state.last_update = 0

if "route_data" not in st.session_state:
    st.session_state.route_data = None


# ---------------- INPUT ----------------
src = st.text_input("Source (Mumbai)")
dst = st.text_input("Destination (Mumbai)")


# ---------------- BUILD MAP ----------------
def build_map(coords, s, d):

    m = folium.Map(location=[s.latitude, s.longitude], zoom_start=12)

    route_colors = []

    for point in coords[::15]:
        lat, lon = point

        try:
            data = requests.get(
                "http://127.0.0.1:5000/predict",
                params={"lat": lat, "lon": lon},
                timeout=2
            ).json()

            # ---------- ACTUAL ----------
            speed = data.get("speed")
            free = data.get("free_flow")

            actual = None
            if speed and free:
                actual = 1 - (speed / free)

            # ---------- PREDICTED ----------
            pred_volume = data.get("predicted_volume", 0)

            # predicted route color
            if pred_volume < 2000:
                pred_color = "green"
            elif pred_volume < 4000:
                pred_color = "orange"
            else:
                pred_color = "red"

            route_colors.append((point, pred_color))

            # actual dot color
            if actual is None:
                actual_color = "gray"
            elif actual < 0.25:
                actual_color = "green"
            elif actual < 0.5:
                actual_color = "orange"
            else:
                actual_color = "red"

        except:
            pred_color = "gray"
            actual_color = "gray"

        # -------- ACTUAL DOT --------
        folium.CircleMarker(
            location=[lat, lon],
            radius=6,
            color=actual_color,
            fill=True,
            fill_opacity=0.9,
            tooltip=f"Actual congestion"
        ).add_to(m)

    # -------- PREDICTED ROUTE SEGMENTS --------
    for i in range(len(route_colors)-1):
        p1, color = route_colors[i]
        p2, _ = route_colors[i+1]

        folium.PolyLine(
            [p1, p2],
            color=color,
            weight=6,
            opacity=0.8
        ).add_to(m)

    # markers
    folium.Marker(
        [s.latitude, s.longitude],
        tooltip="Source",
        icon=folium.Icon(color="green")
    ).add_to(m)

    folium.Marker(
        [d.latitude, d.longitude],
        tooltip="Destination",
        icon=folium.Icon(color="red")
    ).add_to(m)

    # legend
    legend = """
    <div style="
    position: fixed; 
    bottom: 50px; left: 50px; width: 230px;
    background-color: white;
    border-radius:10px;
    z-index:9999;
    font-size:14px;
    padding:10px;
    ">
    <b>Traffic Legend</b><br><br>

    <b>Route Color = Predicted</b><br>
    🟢 Low<br>
    🟠 Medium<br>
    🔴 High<br><br>

    <b>Dots = Actual</b><br>
    🟢 Low<br>
    🟠 Medium<br>
    🔴 Heavy
    </div>
    """

    m.get_root().html.add_child(folium.Element(legend))

    return m._repr_html_()


# ---------------- BUTTON ----------------
if st.button("Show Route"):

    s = geo.geocode(src + ", Mumbai")
    d = geo.geocode(dst + ", Mumbai")

    if s and d:

        url = f"http://router.project-osrm.org/route/v1/driving/{s.longitude},{s.latitude};{d.longitude},{d.latitude}?overview=full"
        route = requests.get(url).json()

        coords = polyline.decode(route["routes"][0]["geometry"])

        st.session_state.route_data = (coords, s, d)
        st.session_state.last_update = 0


# ---------------- REFRESH EVERY 5 MIN ----------------
if st.session_state.route_data:

    now = time.time()

    if now - st.session_state.last_update > 300:

        coords, s, d = st.session_state.route_data

        st.session_state.map_html = build_map(coords, s, d)
        st.session_state.last_update = now


# ---------------- DISPLAY ----------------
if st.session_state.map_html:
    st.components.v1.html(st.session_state.map_html, height=600)