import streamlit as st
import requests
import folium
from streamlit_folium import st_folium
from geopy.geocoders import Nominatim
import time

#st.set_page_config(layout="wide")

BACKEND = "http://127.0.0.1:5000/predict"

# ---------------- STYLE ----------------
st.markdown("""
<style>

.title{
font-size:36px;
font-weight:700;
margin-bottom:15px;
}

.section{
font-size:22px;
font-weight:600;
margin-top:25px;
margin-bottom:10px;
}

.card{
background:linear-gradient(135deg,#020617,#020617);
padding:24px;
border-radius:16px;
text-align:center;
color:white;
box-shadow:0 8px 25px rgba(0,0,0,0.35);
}

.card-title{
font-size:14px;
color:#94a3b8;
}

.card-value{
font-size:28px;
font-weight:700;
}

.location-box{
background:linear-gradient(135deg,#020617,#020617);
padding:20px;
border-radius:14px;
color:white;
margin-bottom:10px;
}

</style>
""", unsafe_allow_html=True)

# ---------------- TITLE ----------------
st.markdown('<div class="title">Mumbai Traffic Dashboard</div>', unsafe_allow_html=True)

# ---------------- LOCATION ----------------
geo = Nominatim(user_agent="traffic")

if "lat" not in st.session_state:
    st.session_state.lat = 19.0760
    st.session_state.lon = 72.8777

location = st.text_input("Search location")

if location:
    loc = geo.geocode(location + ", Mumbai")
    if loc:
        st.session_state.lat = loc.latitude
        st.session_state.lon = loc.longitude

lat = st.session_state.lat
lon = st.session_state.lon

# ---------------- FETCH ----------------
if "last_fetch" not in st.session_state:
    st.session_state.last_fetch = 0

if "data" not in st.session_state:
    st.session_state.data = None

now = time.time()

if now - st.session_state.last_fetch > 120:
    try:
        st.session_state.data = requests.get(
            BACKEND,
            params={"lat": lat, "lon": lon}
        ).json()
    except:
        pass

    st.session_state.last_fetch = now

data = st.session_state.data

if not data:
    st.stop()

place = data.get("place","Mumbai")
weather = data.get("weather",{})

# ---------------- MAP + LOCATION ----------------
col1, col2 = st.columns([2,1])

with col1:
    m = folium.Map(location=[lat, lon], zoom_start=12)
    folium.Marker([lat, lon]).add_to(m)
    st_folium(m, height=350)

with col2:
    st.markdown(f"""
    <div class="location-box">
    <b>📍 {place}</b><br><br>
    Latitude: {lat:.4f}<br>
    Longitude: {lon:.4f}
    </div>
    """, unsafe_allow_html=True)

# ---------------- TRAFFIC ----------------
st.markdown('<div class="section">Traffic Status</div>', unsafe_allow_html=True)

pred = data.get("prediction",0)
pred_vol = data.get("predicted_volume",0)
actual_vol = data.get("actual_volume",None)
cong = data.get("actual_congestion",None)

traffic = ["Low","Medium","High"]

t1,t2,t3,t4 = st.columns(4)

t1.markdown(f"""
<div class="card">
<div class="card-title">Predicted</div>
<div class="card-value">{traffic[pred]}</div>
</div>
""", unsafe_allow_html=True)

t2.markdown(f"""
<div class="card">
<div class="card-title">Pred Volume</div>
<div class="card-value">{int(pred_vol)}</div>
</div>
""", unsafe_allow_html=True)

t3.markdown(f"""
<div class="card">
<div class="card-title">Actual Volume</div>
<div class="card-value">{int(actual_vol) if actual_vol else "--"}</div>
</div>
""", unsafe_allow_html=True)

t4.markdown(f"""
<div class="card">
<div class="card-title">Congestion</div>
<div class="card-value">{round(cong*100,1) if cong else "--"}%</div>
</div>
""", unsafe_allow_html=True)

# ---------------- WEATHER ----------------
st.markdown('<div class="section">Weather</div>', unsafe_allow_html=True)

w1,w2,w3 = st.columns(3)

w1.markdown(f"""
<div class="card">
<div class="card-title">Temperature</div>
<div class="card-value">{weather.get("temperature","--")}°C</div>
</div>
""", unsafe_allow_html=True)

w2.markdown(f"""
<div class="card">
<div class="card-title">Humidity</div>
<div class="card-value">{weather.get("humidity","--")}%</div>
</div>
""", unsafe_allow_html=True)

w3.markdown(f"""
<div class="card">
<div class="card-title">Rainfall</div>
<div class="card-value">{weather.get("rain","--")} mm</div>
</div>
""", unsafe_allow_html=True)

w4,w5,w6 = st.columns(3)

w4.markdown(f"""
<div class="card">
<div class="card-title">Wind Speed</div>
<div class="card-value">{weather.get("windspeed","--")} km/h</div>
</div>
""", unsafe_allow_html=True)

w5.markdown(f"""
<div class="card">
<div class="card-title">Cloud Cover</div>
<div class="card-value">{weather.get("cloudcover","--")}%</div>
</div>
""", unsafe_allow_html=True)

w6.markdown(f"""
<div class="card">
<div class="card-title">UV Index</div>
<div class="card-value">{weather.get("uv_index","--")}</div>
</div>
""", unsafe_allow_html=True)