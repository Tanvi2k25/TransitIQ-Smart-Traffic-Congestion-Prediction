import streamlit as st
import requests
import pandas as pd
import folium
from streamlit_folium import st_folium
from datetime import datetime

BACKEND = "http://127.0.0.1:5000"

# ---------------- STYLE ----------------
st.markdown("""
<style>
.title{
    font-size:34px;
    font-weight:700;
    margin-bottom:10px;
}
.section{
    font-size:22px;
    font-weight:600;
    margin-top:25px;
    margin-bottom:12px;
}
.card{
    background:linear-gradient(135deg,#0f172a,#111827);
    border:1px solid #334155;
    border-radius:16px;
    padding:16px;
    margin-bottom:14px;
    color:#f8fafc;
    box-shadow:0 10px 28px rgba(0,0,0,0.28);
    text-align:center;
}
.card-title{
    font-size:12px;
    color:#94a3b8;
    text-transform:uppercase;
    letter-spacing:1px;
    margin-bottom:8px;
}
.card-value{
    font-size:24px;
    font-weight:700;
    margin-top:0;
    color:#ffffff;
}
.incident-legend {
    width: 100%;
    background-color: rgba(2,6,23,0.95);
    color: white;
    border-radius: 12px;
    padding: 18px;
    margin-top: 0;
    font-size:14px;
}
.incident-banner {
    background: linear-gradient(135deg, #111827, #0f172a);
    border: 1px solid #334155;
    border-radius: 16px;
    padding: 16px;
    margin-bottom: 18px;
    color: #e2e8f0;
    box-shadow: 0 10px 28px rgba(0,0,0,0.28);
}
</style>
""", unsafe_allow_html=True)

# ---------------- TITLE ----------------
st.markdown('<div class="title">🚧 Live Traffic Incidents</div>', unsafe_allow_html=True)

# ---------------- LOCATION ----------------
lat = st.session_state.get("lat", 19.0760)
lon = st.session_state.get("lon", 72.8777)

# ---------------- GET PLACE NAME ----------------
place_name = "Selected Location"

try:
    loc_res = requests.get(
        f"{BACKEND}/predict",
        params={"lat": lat, "lon": lon},
        timeout=5
    ).json()

    place_name = loc_res.get("place", "Selected Location")

except:
    pass

# Show location info
st.markdown(f"""
<div style="font-size:18px; margin-bottom:10px; color:#94a3b8;">
📍 Showing incidents around <b>{place_name}</b>
</div>
""", unsafe_allow_html=True)

st.caption("Coverage: ~20 km radius from selected location")
st.markdown("<div style='color:#94a3b8; font-size:14px; margin-bottom:12px;'>Auto-refresh every 15 seconds for live updates.</div>", unsafe_allow_html=True)

# ---------------- GET INCIDENTS ----------------
try:
    res = requests.get(
        f"{BACKEND}/incidents",
        params={"lat": lat, "lon": lon},
        timeout=5
    )
    data = res.json()
except:
    data = []

st.markdown(
    "<script>setTimeout(function(){ window.location.reload(); }, 15000);</script>",
    unsafe_allow_html=True
)

df = pd.DataFrame(data)

incident_count = len(df)
accident_count = int((df["type"] == "Accident").sum()) if not df.empty and "type" in df else 0
traffic_count = int((df["type"] == "Traffic").sum()) if not df.empty and "type" in df else 0
construction_count = int((df["type"] == "Construction").sum()) if not df.empty and "type" in df else 0
other_count = incident_count - accident_count - traffic_count - construction_count
last_update = datetime.now().strftime("%H:%M %d %b")

st.markdown(f"""
<div class='incident-banner'>
    <div style='display:flex; flex-wrap:wrap; gap:12px; justify-content:space-between; align-items:center;'>
        <div>
            <div style='font-size:12px; color:#94a3b8; text-transform:uppercase; letter-spacing:1px;'>Live incident summary</div>
            <div style='font-size:22px; font-weight:700; margin-top:6px;'>{incident_count} active issue{'s' if incident_count != 1 else ''}</div>
            <div style='margin-top:8px; color:#cbd5e1;'>Updated {last_update}</div>
        </div>
        <div style='text-align:right;'>
            <div style='font-size:13px; color:#94a3b8;'>Coverage</div>
            <div style='font-size:16px; font-weight:600; margin-top:4px;'>~20 km radius</div>
        </div>
    </div>
</div>
""", unsafe_allow_html=True)

if st.button("🔄 Refresh incidents"):
    st.rerun()

count_cols = st.columns(4)
count_cols[0].markdown(f"""
<div class='card'><div class='card-title'>Accidents</div><div class='card-value'>{accident_count}</div></div>
""", unsafe_allow_html=True)
count_cols[1].markdown(f"""
<div class='card'><div class='card-title'>Traffic Alerts</div><div class='card-value'>{traffic_count}</div></div>
""", unsafe_allow_html=True)
count_cols[2].markdown(f"""
<div class='card'><div class='card-title'>Construction</div><div class='card-value'>{construction_count}</div></div>
""", unsafe_allow_html=True)
count_cols[3].markdown(f"""
<div class='card'><div class='card-title'>Other Issues</div><div class='card-value'>{other_count}</div></div>
""", unsafe_allow_html=True)

# ---------------- COLOR FUNCTION ----------------

def get_color(incident_type):
    if incident_type == "Accident":
        return "red"
    elif incident_type == "Traffic":
        return "orange"
    elif incident_type == "Road Closure":
        return "darkred"
    elif incident_type == "Construction":
        return "blue"
    else:
        return "gray"

# ---------------- MAP ----------------
st.markdown(f'<div class="section">🗺 Incident Map - {place_name}</div>', unsafe_allow_html=True)

map_col, legend_col = st.columns([3,1])

with map_col:
    m = folium.Map(location=[lat, lon], zoom_start=12)

    # 🟢 Selected location marker
    folium.Marker(
        [lat, lon],
        tooltip=f"Selected location: {place_name}",
        popup=f"<b>{place_name}</b>",
        icon=folium.Icon(color="lightgreen", icon="info-sign")
    ).add_to(m)

    # 🔴 Incident markers
    if not df.empty:
        for _, r in df.iterrows():
            try:
                folium.Marker(
                    [float(r["lat"]), float(r["lon"])],
                    tooltip=f"{r['type']} - {r['description']}",
                    popup=f"""
                    <b>Type:</b> {r['type']}<br>
                    <b>Location:</b> {r['place']}<br>
                    <b>Delay:</b> {r['delay']}
                    """,
                    icon=folium.Icon(color=get_color(r["type"]))
                ).add_to(m)
            except Exception:
                continue

    st_folium(m, height=500)

legend_html = """
<div class="incident-legend">
<b>🚦 Incident Legend</b><br><br>
<span style="color:lightgreen;">●</span> Selected Location<br><br>
<span style="color:red;">●</span> Accident<br>
<span style="color:orange;">●</span> Traffic<br>
<span style="color:darkred;">●</span> Road Closure<br>
<span style="color:blue;">●</span> Construction<br>
<span style="color:gray;">●</span> Other
</div>
"""

with legend_col:
    st.markdown(legend_html, unsafe_allow_html=True)

# ---------------- TABLE ----------------
st.markdown('<div class="section">📊 Incident Details</div>', unsafe_allow_html=True)

if not df.empty:

    table_df = df.copy()

    table_df = table_df.rename(columns={
        "type": "Incident Type",
        "delay": "Delay Level",
        "description": "Description",
        "place": "Location"
    })

    table_df = table_df[[
        "Location",
        "Incident Type",
        "Description",
        "Delay Level"
    ]]

    st.dataframe(table_df, use_container_width=True)

else:
    st.info("✅ No live incidents reported in this area currently.")
    st.write("This depends on real-time data availability and local traffic feed coverage.")