import streamlit as st
import requests
import plotly.graph_objects as go
import pandas as pd
from datetime import datetime, timedelta

st.title("Weather & Traffic Forecast")

# ---------------- LOCATION ----------------
lat = st.session_state.get("lat", 19.0760)
lon = st.session_state.get("lon", 72.8777)

st.caption(f"Location: {round(lat,4)}, {round(lon,4)}")

# ---------------- WEATHER API ----------------
weather_url = (
    f"https://api.open-meteo.com/v1/forecast?"
    f"latitude={lat}&longitude={lon}"
    f"&hourly=temperature_2m,relativehumidity_2m,precipitation,cloudcover"
)

weather = requests.get(weather_url).json()

times = weather["hourly"]["time"][:12]
temps = weather["hourly"]["temperature_2m"][:12]
humidity = weather["hourly"]["relativehumidity_2m"][:12]
rain = weather["hourly"]["precipitation"][:12]

# ---------------- TRAFFIC FORECAST ----------------
traffic = []
congestion = []

for i in range(len(times)):
    try:
        data = requests.get(
            "http://127.0.0.1:5000/predict",
            params={"lat": lat, "lon": lon},
            timeout=3
        ).json()

        volume = data.get("predicted_volume", 0)

        speed = data.get("speed")
        free = data.get("free_flow")

        if speed and free:
            cong = 1 - (speed / free)
        else:
            cong = None

        traffic.append(volume)
        congestion.append(cong)

    except:
        traffic.append(0)
        congestion.append(None)

# ---------------- DATAFRAME ----------------
df = pd.DataFrame({
    "Time": times,
    "Temperature": temps,
    "Humidity": humidity,
    "Rain": rain,
    "Traffic": traffic,
    "Congestion": congestion
})

# ---------------- CHART ----------------
fig = go.Figure()

fig.add_trace(go.Scatter(
    x=df["Time"],
    y=df["Temperature"],
    name="Temperature °C",
    yaxis="y1",
    line=dict(color="#f59e0b")
))

fig.add_trace(go.Scatter(
    x=df["Time"],
    y=df["Traffic"],
    name="Predicted Traffic",
    yaxis="y2",
    line=dict(color="#3b82f6")
))

fig.update_layout(
    template="plotly_dark",
    yaxis=dict(title="Temperature"),
    yaxis2=dict(
        title="Traffic Volume",
        overlaying="y",
        side="right"
    ),
    height=450
)

st.plotly_chart(fig, use_container_width=True)

# ---------------- CARDS ----------------
st.subheader("Next Hours Forecast")

cols = st.columns(len(df))

for i, row in df.iterrows():

    congestion_text = "--"
    if row["Congestion"] is not None:
        congestion_text = f"{round(row['Congestion']*100,1)}%"

    cols[i].markdown(f"""
    <div style="
    background:#020617;
    padding:10px;
    border-radius:10px;
    text-align:center;
    ">
    <b>{row['Time'][11:16]}</b><br>
    🌡 {row['Temperature']}°C<br>
    💧 {row['Humidity']}%<br>
    🌧 {row['Rain']} mm<br>
    🚗 {int(row['Traffic'])}<br>
    🚦 {congestion_text}
    </div>
    """, unsafe_allow_html=True)

# ---------------- TABLE ----------------
st.subheader("Forecast Table")

df["Congestion"] = df["Congestion"].apply(
    lambda x: f"{round(x*100,1)}%" if x else "--"
)

st.dataframe(df, use_container_width=True)