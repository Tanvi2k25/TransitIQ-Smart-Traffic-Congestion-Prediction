import streamlit as st
import requests
import folium
from streamlit_folium import st_folium
import time
from datetime import datetime, timedelta

BACKEND = "http://127.0.0.1:5000"

# ---------------- STYLE ----------------
st.markdown("""
<style>
.title{ font-size:34px; font-weight:700; margin-bottom:10px; }
.section{ font-size:22px; font-weight:600; margin-top:20px; margin-bottom:10px; }
.card{
    background:linear-gradient(135deg,#020617,#020617);
    padding:20px; border-radius:14px; text-align:center; color:white;
    box-shadow:0 6px 18px rgba(0,0,0,0.35); border:1px solid #1e293b;
    transition:all 0.3s ease; height: 100%;
}
.card:hover{ border-color:#0ea5e9; }
.card-title{ font-size:12px; color:#94a3b8; text-transform:uppercase; letter-spacing:0.5px; }
.card-value{ font-size:24px; font-weight:700; margin-top:8px; }
.location-box{
    background:linear-gradient(135deg,#0f172a,#1e293b);
    padding:20px; border-radius:14px; color:white;
    border:1px solid #334155; box-shadow:0 4px 12px rgba(0,0,0,0.3);
}
.suggestion{
    padding:15px; border-radius:10px; margin-top:10px;
    font-weight:500; border-left:5px solid; line-height:1.5;
}
.low{background:#064e3b; color:#22c55e; border-color:#22c55e;}
.medium{background:#78350f; color:#facc15; border-color:#facc15;}
.high{background:#7f1d1d; color:#ef4444; border-color:#ef4444;}
.status-badge{
    display:inline-block; padding:4px 10px; border-radius:20px;
    font-size:10px; font-weight:600; margin-top:8px;
}
.status-live{ background:#064e3b; color:#22c55e; }
</style>
""", unsafe_allow_html=True)

# ---------------- INITIALIZATION ----------------
if "lat" not in st.session_state:
    # Default to Mumbai City Center (CST Area)
    st.session_state.lat = 18.9402 
    st.session_state.lon = 72.8353
    st.session_state.searched_location = "Mumbai City Center"

# ---------------- TITLE ----------------
st.markdown('<div class="title">Mumbai Traffic Dashboard</div>', unsafe_allow_html=True)

# ---------------- SEARCH ----------------
location = st.text_input("Search Area", placeholder="Enter neighborhood (e.g. Chembur, Borivali, Dadar)")

if st.button("Set Location"):
    if location:
        try:
            headers = {"User-Agent": "MumbaiTrafficDashboard/1.0"}
            url = f"https://nominatim.openstreetmap.org/search?q={location}, Mumbai&format=json&limit=1&addressdetails=1"
            response = requests.get(url, headers=headers, timeout=5)
            
            if response.status_code == 200:
                res = response.json()
                if res:
                    st.session_state.lat = float(res[0]["lat"])
                    st.session_state.lon = float(res[0]["lon"])
                    # Capture the specific address
                    st.session_state.searched_location = res[0].get("display_name", location)
                    st.success("📍 Location updated!")
                    st.rerun()
                else:
                    st.warning("Area not found in Mumbai. Please try another name.")
        except Exception as e:
            st.error(f"Search error: {e}")

# ---------------- DATA FETCHING ----------------
def get_data(lat, lon):
    try:
        return requests.get(f"{BACKEND}/predict", params={"lat": lat, "lon": lon}, timeout=5).json()
    except: return None

data = get_data(st.session_state.lat, st.session_state.lon)

if not data:
    st.error("Cannot connect to Traffic Server. Please ensure server.py is running.")
    st.stop()

# ---------------- CALCULATIONS ----------------
weather = data.get("weather", {})
level = data.get("traffic_level", "Low")
speed = data.get("speed", 30)

# Create a "Mobility Score" (Area-wise Health)
# Lower volume + Higher speed = Better score
vol_factor = max(0, 100 - (data.get("actual_volume", 0) / 100))
speed_factor = min(100, (speed / 60) * 100)
mobility_score = int((vol_factor * 0.4) + (speed_factor * 0.6))

# ---------------- MAIN UI ----------------
col1, col2 = st.columns([2,1])

with col1:
    m = folium.Map(location=[st.session_state.lat, st.session_state.lon], zoom_start=14)
    folium.CircleMarker(
        location=[st.session_state.lat, st.session_state.lon],
        radius=12, color="#0ea5e9", fill=True, fill_opacity=0.7
    ).add_to(m)
    st_folium(m, height=400, width=700, key="main_map")

with col2:
    # Dynamic Label based on search
    is_default = st.session_state.searched_location == "Mumbai City Center"
    label = "🏙️ Default View" if is_default else "📍 Selected Area"
    
    st.markdown(f"""
    <div class="location-box">
        <span style="font-size:10px; color:#94a3b8; text-transform:uppercase;">{label}</span><br>
        <div style="font-size:15px; font-weight:600; color:#ffffff; line-height:1.4; margin-top:5px;">
            {st.session_state.searched_location}
        </div>
        <hr style="border:0.5px solid #334155; margin:15px 0;">
        <div style="font-size:12px; color:#94a3b8;">
            Mobility Score: <b style="color:#0ea5e9; font-size:16px;">{mobility_score}/100</b>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Contextual Area-Wise Suggestions
    if level == "High":
        st.markdown(f'<div class="suggestion high"><b>🚨 Critical Congestion</b><br>Significant bottlenecks in this sector. Check the <b>Routes</b> page for bypass options.</div>', unsafe_allow_html=True)
    elif level == "Medium":
        st.markdown(f'<div class="suggestion medium"><b>⚠️ Moderate Flow</b><br>Typical urban crawl. Visit the <b>Forecast</b> page to see when this will clear.</div>', unsafe_allow_html=True)
    else:
        st.markdown(f'<div class="suggestion low"><b>✅ Clear Roads</b><br>Area is moving at {speed} km/h. Great time for travel in this neighborhood.</div>', unsafe_allow_html=True)

# ---------------- TRAFFIC STATUS ----------------
st.markdown('<div class="section">Traffic Intelligence</div>', unsafe_allow_html=True)
t1, t2, t3 = st.columns(3)
t1.markdown(f'<div class="card"><div class="card-title">Congestion</div><div class="card-value">{level}</div></div>', unsafe_allow_html=True)
t2.markdown(f'<div class="card"><div class="card-title">Avg. Area Speed</div><div class="card-value">{speed} km/h</div></div>', unsafe_allow_html=True)
t3.markdown(f'<div class="card"><div class="card-title">Est. Volume</div><div class="card-value">{int(data.get("actual_volume",0))}</div></div>', unsafe_allow_html=True)

# ---------------- WEATHER CONDITIONS ----------------
st.markdown('<div class="section">🌤️ Area Weather snapshot</div>', unsafe_allow_html=True)
w1, w2, w3, w4 = st.columns(4)
weather_items = [
    ("🌡️ Temp", f"{weather.get('temperature','--')}°C"),
    ("💧 Humidity", f"{weather.get('humidity','--')}%"),
    ("🌧️ Rain", f"{weather.get('rain','--')}mm"),
    ("👁️ Visibility", f"{weather.get('visibility', 10000)/1000}km")
]
for col, (title, val) in zip([w1,w2,w3,w4], weather_items):
    col.markdown(f'<div class="card"><div class="card-title">{title}</div><div class="card-value">{val}</div></div>', unsafe_allow_html=True)

# Row 2 Weather
st.write("")
w5, w6, w7, w8 = st.columns(4)
adv_weather = [
    ("☀️ UV Index", f"{weather.get('uv_index','--')}"),
    ("☁️ Cloud", f"{weather.get('cloudcover','--')}%"),
    ("💨 Wind", f"{weather.get('windspeed','--')} km/h"),
    ("🌫️ Condition", "Clear" if weather.get('rain',0) == 0 else "Rainy")
]
for col, (title, val) in zip([w5,w6,w7,w8], adv_weather):
    col.markdown(f'<div class="card"><div class="card-title">{title}</div><div class="card-value">{val}</div></div>', unsafe_allow_html=True)

# ---------------- STATUS & REFRESH ----------------
st.divider()
c_status, c_refresh, c_interval = st.columns([2,1,1])
with c_status:
    st.markdown(f"""
    <div class="card" style="padding:15px;">
        <div class="card-title">Last Sync</div>
        <div class="card-value" style="font-size:18px;">{data.get('timestamp','--')}</div>
        <div class="status-badge status-live">🟢 LIVE AREA FEED</div>
    </div>
    """, unsafe_allow_html=True)

with c_refresh:
    if st.button("🔄 Sync Now", use_container_width=True):
        st.rerun()

with c_interval:
    refresh_options = {"2 min": 120, "3 min": 180, "5 min": 300}
    selected = st.selectbox("Auto-Refresh", list(refresh_options.keys()))
    st.session_state.refresh_interval = refresh_options[selected]

# Auto-refresh helper
remaining = max(0, int(st.session_state.get('refresh_interval', 180) - (time.time() - st.session_state.get('last_refresh', time.time()))))
st.caption(f"⏳ Refreshing in {remaining}s | Logic: Current Area Intelligence")