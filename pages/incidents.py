import requests
import pandas as pd
import folium
import streamlit as st
from html import escape
from streamlit_folium import st_folium
from datetime import datetime
import math

BACKEND = "http://127.0.0.1:5000"

st.markdown("""
<style>
.title {font-size:34px;font-weight:700;margin-bottom:10px}
.section {font-size:22px;font-weight:600;margin:24px 0 12px}
.card,.banner {background:linear-gradient(135deg,#0f172a,#111827);border:1px solid #334155;border-radius:16px;padding:16px;margin-bottom:14px;color:#f8fafc;text-align:center}
.card-title {font-size:12px;color:#94a3b8;text-transform:uppercase;letter-spacing:1px}
.card-value {font-size:24px;font-weight:700;margin-top:8px}
</style>
""", unsafe_allow_html=True)

st.markdown('<div class="title">Live Traffic Incidents</div>', unsafe_allow_html=True)
lat = st.session_state.get("lat", 19.0760)
lon = st.session_state.get("lon", 72.8777)
place_name = escape(str(st.session_state.get("searched_location", "Selected Location")))
st.markdown(f"Showing incidents around **{place_name}**")
st.caption("The map shows incidents within the 10 km coverage circle around the selected location.")

source = "unavailable"
error_message = None
data = []
try:
    response = requests.get(
        f"{BACKEND}/incidents", params={"lat": lat, "lon": lon},
        timeout=(2, 8)
    )
    payload = response.json()
    data = payload.get("incidents", []) if isinstance(payload, dict) else payload
    source = payload.get("source", "live") if isinstance(payload, dict) else "live"
    if response.status_code >= 400:
        error_message = payload.get("error", "The live incident service is unavailable.")
except (requests.RequestException, ValueError) as exc:
    error_message = str(exc)

if source == "live":
    st.caption("Data source: TomTom Traffic Incidents (live response)")
elif source == "cache":
    st.info("Showing recently cached TomTom results.")
elif source == "stale-cache":
    st.warning("TomTom could not be reached. Showing the last cached incident results.")
else:
    st.warning("Live incidents are unavailable. Check connectivity and the TomTom API key, then refresh.")
if error_message:
    st.caption(f"Service detail: {error_message}")

if st.button("Refresh incidents"):
    st.rerun()

df = pd.DataFrame(data)
if not df.empty:
    for col in ("type", "description", "delay", "place", "lat", "lon"):
        if col not in df:
            df[col] = "Not provided"
    df["lat"] = pd.to_numeric(df["lat"], errors="coerce")
    df["lon"] = pd.to_numeric(df["lon"], errors="coerce")
    df = df.dropna(subset=["lat", "lon"])
    # Apply the same radius in the UI so only pins inside the visible Home circle remain.
    center_lat, center_lon = math.radians(lat), math.radians(lon)
    incident_lats = df["lat"].map(math.radians)
    incident_lons = df["lon"].map(math.radians)
    delta_lat = incident_lats - center_lat
    delta_lon = incident_lons - center_lon
    haversine = (
        (delta_lat / 2).map(math.sin) ** 2
        + math.cos(center_lat) * incident_lats.map(math.cos)
        * (delta_lon / 2).map(math.sin) ** 2
    )
    df["distance_km"] = 6371.0 * 2 * haversine.map(
        lambda value: math.asin(min(1.0, math.sqrt(max(0.0, value))))
    )
    df = df[df["distance_km"] <= 10.0].copy()

count_map = df["type"].value_counts() if not df.empty else pd.Series(dtype=int)
accident_count = int(count_map.get("Accident", 0))
traffic_count = int(count_map.get("Traffic", 0))
construction_count = int(count_map.get("Construction", 0))
other_count = max(0, len(df) - accident_count - traffic_count - construction_count)
st.markdown(
    f"<div class='banner'><b>{len(df)} active incident(s)</b> · Updated {datetime.now().strftime('%H:%M %d %b')}</div>",
    unsafe_allow_html=True
)
cols = st.columns(4)
for col, title, value in zip(cols, ["Accidents", "Traffic alerts", "Construction", "Other"], [accident_count, traffic_count, construction_count, other_count]):
    col.markdown(f"<div class='card'><div class='card-title'>{title}</div><div class='card-value'>{value}</div></div>", unsafe_allow_html=True)

st.markdown('<div class="section">Incident map</div>', unsafe_allow_html=True)
map_col, details_col = st.columns([2, 1])
colors = {"Accident": "red", "Traffic": "orange", "Road Closure": "darkred", "Construction": "blue"}
with map_col:
    incident_map = folium.Map(location=[lat, lon], zoom_start=12, tiles="OpenStreetMap")
    folium.CircleMarker(
        location=[lat, lon], radius=12, color="#0ea5e9",
        fill=True, fill_opacity=0.7, tooltip=f"Selected location: {place_name}"
    ).add_to(incident_map)
    folium.Circle(
        location=[lat, lon], radius=10000, color="#38bdf8",
        weight=2, fill=True, fill_color="#38bdf8", fill_opacity=0.05,
        tooltip="10 km incident coverage, matching the Home map"
    ).add_to(incident_map)
    legend_items = [
        ("#0ea5e9", "Selected location"),
        ("red", "Accident"),
        ("orange", "Traffic"),
        ("darkred", "Road closure"),
        ("blue", "Construction"),
        ("gray", "Other / unspecified"),
    ]
    legend_html = "".join(
        "<span style='display:inline-flex;align-items:center;gap:5px;margin:3px 12px 3px 0;'>"
        f"<i style='display:inline-block;width:11px;height:11px;border-radius:50%;background:{color};'></i>"
        f"{label}</span>"
        for color, label in legend_items
    )
    st.markdown(
        "<div style='background:#0f172a;color:#e2e8f0;border:1px solid #334155;"
        "border-radius:8px;padding:8px 10px;margin-bottom:8px;font-size:13px;'>"
        f"<b>Pin legend:</b> {legend_html}</div>",
        unsafe_allow_html=True,
    )
    for incident_number, (_, row) in enumerate(df.iterrows(), start=1):
        incident_type = escape(str(row["type"]))
        folium.Marker(
            [row["lat"], row["lon"]],
            tooltip=(
                f"{incident_type} · {row['distance_km']:.1f} km from center · "
                f"{escape(str(row['description']))}"
            ),
            popup=f"<b>{incident_type}</b><br>{escape(str(row['place']))}<br>{escape(str(row['description']))}<br>Delay: {escape(str(row['delay']))}",
            icon=folium.Icon(color=colors.get(row["type"], "gray"))
        ).add_to(incident_map)
    st_folium(incident_map, height=500, use_container_width=True)

with details_col:
    st.markdown("### Incident details")
    if df.empty:
        st.info("No current incident records are available.")
    else:
        table = df.rename(columns={"type": "Type", "description": "Description", "delay": "Delay", "place": "Road / location"})
        table["Distance from center (km)"] = df["distance_km"].map(lambda value: f"{value:.1f}")
        table.insert(0, "Map #", [f"#{i}" for i in range(1, len(table) + 1)])
        st.dataframe(table[["Map #", "Distance from center (km)", "Type", "Road / location", "Description", "Delay"]], use_container_width=True, hide_index=True)

st.caption("Incident availability depends on TomTom coverage and network connectivity. Cached results are labeled when used.")
