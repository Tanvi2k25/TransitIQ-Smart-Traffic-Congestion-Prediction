import streamlit as st
import requests
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime
from geopy.geocoders import Nominatim
import time

# ---------------- STYLE ----------------
st.markdown("""
<style>
.metric-card {
    background: linear-gradient(145deg, #020617, #020617);
    padding: 18px;
    border-radius: 12px;
    text-align: center;
    color: white;
    box-shadow: 0 4px 15px rgba(0,0,0,0.4);
}
.section-title {
    font-size: 22px;
    font-weight: 600;
    margin-top: 20px;
    margin-bottom: 10px;
}
</style>
""", unsafe_allow_html=True)

st.title("Traffic Analysis Dashboard")

# ---------------- SESSION ----------------
if "history" not in st.session_state:
    st.session_state.history = []

if "last_fetch" not in st.session_state:
    st.session_state.last_fetch = 0

if "lat" not in st.session_state:
    st.session_state.lat = 19.0760
    st.session_state.lon = 72.8777

# ---------------- LOCATION ----------------
geo = Nominatim(user_agent="traffic_app")

location = st.text_input("Search location")

if location:
    loc = geo.geocode(location + ", Mumbai")
    if loc:
        st.session_state.lat = loc.latitude
        st.session_state.lon = loc.longitude

lat = st.session_state.lat
lon = st.session_state.lon

st.write(f"📍 Location: {round(lat,4)}, {round(lon,4)}")

# ---------------- API ----------------
def get_data():
    try:
        return requests.get(
            "http://127.0.0.1:5000/predict",
            params={"lat": lat, "lon": lon},
            timeout=5
        ).json()
    except:
        return None

# ---------------- FETCH EVERY 2 MIN ----------------
current_time = time.time()

if current_time - st.session_state.last_fetch > 120:
    data = get_data()

    if data:
        predicted = data.get("predicted_volume", 0)
        actual = data.get("actual_volume", predicted)

        speed = data.get("speed", None)
        free = data.get("free_flow", None)

        congestion = None
        if speed is not None and free is not None and free != 0:
            try:
                congestion = 1 - (float(speed) / float(free))
            except:
                congestion = None

        st.session_state.history.append({
            "time": datetime.now().strftime("%H:%M:%S"),
            "predicted": predicted,
            "actual": actual,
            "congestion": congestion
        })

        st.session_state.last_fetch = current_time

df = pd.DataFrame(st.session_state.history)

# ---------------- GRAPH ----------------
st.markdown('<div class="section-title">📈 Traffic Trend</div>', unsafe_allow_html=True)

if not df.empty:
    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=df["time"],
        y=df["predicted"],
        name="Predicted",
        mode="lines+markers",
        line=dict(width=3)
    ))

    fig.add_trace(go.Scatter(
        x=df["time"],
        y=df["actual"],
        name="Actual",
        mode="lines+markers",
        line=dict(dash="dot")
    ))

    fig.update_layout(template="plotly_dark")
    st.plotly_chart(fig, use_container_width=True)

# ---------------- GAUGE ----------------
st.markdown('<div class="section-title">🎯 Traffic Intensity</div>', unsafe_allow_html=True)

if not df.empty:

    latest = df.iloc[-1]

    col1, col2 = st.columns(2)

    pred_gauge = go.Figure(go.Indicator(
        mode="gauge+number",
        value=latest["predicted"],
        title={'text': "Predicted Traffic"},
        gauge={
            'axis': {'range': [0, 6000]},
            'bar': {'color': "#3b82f6", 'thickness': 0.25},
            'steps': [
                {'range': [0, 2000], 'color': "#22c55e"},
                {'range': [2000, 4000], 'color': "#eab308"},
                {'range': [4000, 6000], 'color': "#ef4444"},
            ]
        }
    ))

    actual_gauge = go.Figure(go.Indicator(
        mode="gauge+number",
        value=latest["actual"],
        title={'text': "Actual Traffic"},
        gauge={
            'axis': {'range': [0, 6000]},
            'bar': {'color': "#22c55e", 'thickness': 0.25},
            'steps': [
                {'range': [0, 2000], 'color': "#22c55e"},
                {'range': [2000, 4000], 'color': "#eab308"},
                {'range': [4000, 6000], 'color': "#ef4444"},
            ]
        }
    ))

    col1.plotly_chart(pred_gauge, use_container_width=True)
    col2.plotly_chart(actual_gauge, use_container_width=True)

# ---------------- METRICS ----------------
st.markdown('<div class="section-title">📊 Traffic Stats</div>', unsafe_allow_html=True)

if len(df) >= 1:
    latest = df.iloc[-1]

    col1, col2 = st.columns(2)

    col1.markdown(f"""
    <div class="metric-card">
        <h4>Current Predicted</h4>
        <h2>{int(latest["predicted"])}</h2>
    </div>
    """, unsafe_allow_html=True)

    col2.markdown(f"""
    <div class="metric-card">
        <h4>Current Actual</h4>
        <h2>{int(latest["actual"])}</h2>
    </div>
    """, unsafe_allow_html=True)

# ---------------- PREVIOUS ----------------
if len(df) >= 2:
    prev = df.iloc[-2]

    col3, col4 = st.columns(2)

    col3.markdown(f"""
    <div class="metric-card">
        <h4>Previous Predicted</h4>
        <h2>{int(prev["predicted"])}</h2>
    </div>
    """, unsafe_allow_html=True)

    col4.markdown(f"""
    <div class="metric-card">
        <h4>Previous Actual</h4>
        <h2>{int(prev["actual"])}</h2>
    </div>
    """, unsafe_allow_html=True)

# ---------------- INSIGHTS ----------------
st.markdown('<div class="section-title">🧠 Trend Insights</div>', unsafe_allow_html=True)

if len(df) >= 2:
    latest = df.iloc[-1]
    prev = df.iloc[-2]

    diff = latest["actual"] - prev["actual"]

    if diff > 0:
        st.warning(f"Traffic increasing by {int(diff)} vehicles")
    elif diff < 0:
        st.success(f"Traffic decreasing by {int(abs(diff))} vehicles")
    else:
        st.info("Traffic stable")

# ---------------- CONGESTION ----------------
st.markdown('<div class="section-title">🚦 Congestion</div>', unsafe_allow_html=True)

if not df.empty and "congestion" in df.columns:

    latest = df.iloc[-1]["congestion"]

    if latest is not None:
        st.metric("Current Congestion", f"{round(latest*100,1)}%")
    else:
        st.info("Congestion not available yet")