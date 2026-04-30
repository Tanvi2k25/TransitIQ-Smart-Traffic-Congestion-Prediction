import streamlit as st
import requests
import pandas as pd
import plotly.graph_objects as go

BACKEND = "http://127.0.0.1:5000"

# ---------------- STYLE ----------------
st.markdown("""
<style>
.title{
    font-size:34px;
    font-weight:700;
    margin-bottom:18px;
}
.section{
    font-size:22px;
    font-weight:600;
    margin-top:24px;
    margin-bottom:12px;
}
.card{
    background:linear-gradient(135deg,#0f172a,#111827);
    padding:18px;
    border-radius:16px;
    text-align:center;
    color:white;
    box-shadow:0 10px 28px rgba(0,0,0,0.28);
    border:1px solid #334155;
    margin-bottom:18px;
}
.card-title{
    font-size:12px;
    color:#94a3b8;
    text-transform:uppercase;
    letter-spacing:1px;
    margin-bottom:10px;
}
.card-value{
    font-size:18px;
    font-weight:700;
    line-height:1.5;
}
.metric-grid{
    display:grid;
    grid-template-columns:repeat(4, minmax(0, 1fr));
    gap:16px;
    margin-bottom:22px;
}
@media(max-width: 900px) {
    .metric-grid{grid-template-columns:repeat(2, minmax(0, 1fr));}
}
@media(max-width: 640px) {
    .metric-grid{grid-template-columns:1fr;}
}
</style>
""", unsafe_allow_html=True)

# ---------------- TITLE ----------------
st.markdown('<div class="title">Traffic & Weather Forecast</div>', unsafe_allow_html=True)

lat = st.session_state.get("lat", 19.0760)
lon = st.session_state.get("lon", 72.8777)
selected_location = st.session_state.get("searched_location", "Mumbai City Center")

st.markdown(f"<div style='font-size:16px; margin-bottom:12px;'>Forecast based on selected location: <strong>{selected_location}</strong></div>", unsafe_allow_html=True)

st.markdown("""
<div class='card' style='text-align:left;'>
    <div class='card-title'>Why weather matters for traffic</div>
    <div class='card-value' style='font-size:15px; font-weight:500; line-height:1.6;'>
        This forecast is driven by weather and the selected location's local road conditions. Rain, humidity, wind and visibility affect driver speed and congestion,
        while the backend also factors in current traffic flow for the chosen area.
    </div>
</div>
""", unsafe_allow_html=True)

# ---------------- FETCH FORECAST ----------------
try:
    response = requests.get(
        f"{BACKEND}/forecast",
        params={"lat": lat, "lon": lon},
        timeout=10
    )
    response.raise_for_status()
    forecast_data = response.json()
except Exception as exc:
    st.error("Unable to load forecast data. Please make sure the backend server is running.")
    st.write(f"Error: {exc}")
    st.stop()

if not forecast_data:
    st.warning("Forecast service returned no data. Try again later.")
    st.stop()

# ---------------- DATA PREP ----------------
df = pd.DataFrame(forecast_data)
df["time"] = pd.to_datetime(df["time"], errors="coerce")
df = df.dropna(subset=["time"])
df["label"] = df["time"].dt.strftime("%H:%M")

# ---------------- SUMMARY ----------------
peak_row = df.loc[df["predicted_volume"].idxmax()]
max_temp_row = df.loc[df["temperature"].idxmax()]

summary_cols = st.columns(4)
summary_values = [
    ("Peak Traffic", f"{int(peak_row['predicted_volume'])} vehicles"),
    ("Peak Time", f"{peak_row['label']}"),
    ("Max Temp", f"{int(max_temp_row['temperature'])}°C"),
    ("Rain Total", f"{df['rain'].sum():.1f} mm")
]
for col, (title, value) in zip(summary_cols, summary_values):
    col.markdown(f"""
    <div class='card'>
        <div class='card-title'>{title}</div>
        <div class='card-value'>{value}</div>
    </div>
    """, unsafe_allow_html=True)

# ---------------- CHART ----------------
st.markdown('<div class="section">Forecast Trend</div>', unsafe_allow_html=True)

fig = go.Figure()
fig.add_trace(go.Scatter(
    x=df["label"],
    y=df["predicted_volume"],
    name="Traffic Volume",
    mode="lines+markers",
    line=dict(color="#38bdf8"),
    marker=dict(size=6)
))
fig.add_trace(go.Scatter(
    x=df["label"],
    y=df["temperature"],
    name="Temperature",
    yaxis="y2",
    mode="lines+markers",
    line=dict(color="#f59e0b"),
    marker=dict(size=6)
))
fig.update_layout(
    template="plotly_dark",
    height=440,
    margin=dict(l=20, r=20, t=40, b=20),
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    yaxis=dict(title="Traffic Volume"),
    yaxis2=dict(
        title="Temperature (°C)",
        overlaying="y",
        side="right"
    ),
    xaxis=dict(title="Time")
)

st.plotly_chart(fig, use_container_width=True)

# ---------------- NEXT HOURS ----------------
st.markdown('<div class="section">Next Forecast Hours</div>', unsafe_allow_html=True)
st.markdown("<div style='color:#cbd5e1; margin-bottom:16px;'>The hourly cards show the most important traffic and weather details at a glance.</div>", unsafe_allow_html=True)

hourly_rows = df.iloc[:9]
for i in range(0, len(hourly_rows), 3):
    row_cols = st.columns(3, gap='large')
    for j, row in enumerate(hourly_rows.iloc[i:i+3].itertuples()):
        row_cols[j].markdown(f"""
        <div class='card' style='text-align:left; min-height:180px;'>
            <div class='card-title'>{row.label}</div>
            <div style='font-size:20px; font-weight:700; margin-bottom:10px; color:#f8fafc;'>{int(row.predicted_volume)} vehicles</div>
            <div style='font-size:14px; line-height:1.75; color:#cbd5e1;'>
                🌡 Temp: <strong>{row.temperature}°C</strong><br>
                💧 Humidity: <strong>{row.humidity}%</strong><br>
                🌧 Rain: <strong>{row.rain} mm</strong>
            </div>
        </div>
        """, unsafe_allow_html=True)

