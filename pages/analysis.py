import streamlit as st
import requests
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta
import time

BACKEND = "http://127.0.0.1:5000"
DEFAULT_HISTORY_HOURS = 12
LEVEL_COLOR = {"Low": "#22c55e", "Medium": "#f59e0b", "High": "#ef4444"}

# ---------------- CACHE DATA ----------------
@st.cache_data
def load_historical_data():
    df = pd.read_csv("data/Metro_Interstate_Traffic_Volume.csv")
    df["date_time"] = pd.to_datetime(df["date_time"], errors="coerce")
    df["hour"] = df["date_time"].dt.hour
    # Group by hour and calculate mean traffic_volume
    hourly_avg = df.groupby("hour")["traffic_volume"].mean().reset_index()
    hourly_avg["time"] = hourly_avg["hour"].apply(lambda h: f"{h:02d}:00")
    return hourly_avg

historical_data = load_historical_data()

# ---------------- STYLE ----------------
st.markdown("""
<style>
body { background: #020617; color: #e2e8f0; }
.section-title {
    font-size: 24px;
    font-weight: 700;
    margin-top: 24px;
    margin-bottom: 14px;
}
.card {
    background: linear-gradient(135deg, #0f172a, #111827);
    border: 1px solid #334155;
    border-radius: 16px;
    padding: 18px;
    margin-bottom: 18px;
    box-shadow: 0 8px 30px rgba(0,0,0,0.35);
}
.card-title { font-size: 12px; color: #94a3b8; text-transform: uppercase; letter-spacing: 1px; }
.card-value { font-size: 26px; font-weight: 700; margin-top: 10px; color: #f8fafc; }
.metric-card {
    background: linear-gradient(145deg, #020617, #111827);
    display: flex;
    flex-direction: column;
    justify-content: center;
    align-items: center;
    min-height: 120px;
    margin-bottom: 14px;
    border: 1px solid #334155;
    border-radius: 16px;
    padding: 12px;
    color: white;
    box-shadow: 0 8px 28px rgba(0,0,0,0.28);
    text-align: center;
}
.metric-card h4 { margin: 0; color: #94a3b8; font-weight: 600; }
.metric-card h2 { margin: 6px 0 0; font-size: 26px; }
.analysis-status {
    display: inline-flex;
    align-items: center;
    padding: 10px 16px;
    background: #111827;
    border: 1px solid #334155;
    border-radius: 999px;
    color: #a5f3fc;
    font-size: 15px;
    font-weight: 600;
    margin-bottom: 18px;
}
.status-chip {
    display: inline-flex;
    align-items: center;
    gap: 8px;
    background: #0f172a;
    border: 1px solid #334155;
    border-radius: 999px;
    padding: 8px 14px;
    font-size: 12px;
    color: #cbd5e1;
    margin-top: 10px;
}
.small-chip {
    display: inline-flex;
    align-items: center;
    padding: 6px 10px;
    border-radius: 999px;
    background: rgba(148, 163, 184, 0.12);
    border: 1px solid #334155;
    color: #cbd5e1;
    font-size: 12px;
    margin-right: 6px;
}
</style>
""", unsafe_allow_html=True)

st.markdown('<div class="section-title">Traffic Analysis Dashboard</div>', unsafe_allow_html=True)

if "analysis_history" not in st.session_state:
    st.session_state.analysis_history = []
    st.session_state.analysis_history_loaded = False
    st.session_state.analysis_location_key = None

if "analysis_location_key" not in st.session_state:
    st.session_state.analysis_location_key = None

if "analysis_last_fetch" not in st.session_state:
    st.session_state.analysis_last_fetch = 0

if "analysis_refresh_interval" not in st.session_state:
    st.session_state.analysis_refresh_interval = 3600

lat = st.session_state.get("lat", 19.0760)
lon = st.session_state.get("lon", 72.8777)
current_location_key = (round(lat, 5), round(lon, 5))
if st.session_state.analysis_location_key != current_location_key:
    st.session_state.analysis_history = []
    st.session_state.analysis_history_loaded = False
    st.session_state.analysis_location_key = current_location_key

# ---------------- HELPERS ----------------
def traffic_level(volume):
    if volume < 2000:
        return "Low"
    if volume < 4000:
        return "Medium"
    return "High"


def fetch_history(lat, lon, hours=DEFAULT_HISTORY_HOURS):
    try:
        response = requests.get(
            f"{BACKEND}/history",
            params={"lat": lat, "lon": lon, "hours": hours},
            timeout=10,
        )
        if response.status_code == 200:
            payload = response.json()
            history = []
            for row in payload.get("history", []):
                timestamp = row.get("timestamp", "")
                history.append({
                    "timestamp": timestamp,
                    "time": timestamp[-5:] if timestamp else "",
                    "predicted": row.get("predicted_volume", 0),
                    "actual": row.get("actual_volume", 0),
                    "speed": row.get("speed", 0),
                    "traffic": row.get("traffic_level", "Low"),
                    "source": "history"
                })
            return history
    except Exception as e:
        st.warning(f"Unable to load historical traffic data: {e}")

    current_time = datetime.now()
    history = []
    for i in range(hours, 0, -1):
        h = (current_time.hour - i) % 24
        row = historical_data[historical_data["hour"] == h]
        if not row.empty:
            vol = row["traffic_volume"].iloc[0]
            level = traffic_level(vol)
            speed_est = {"Low": 50, "Medium": 30, "High": 15}[level]
            past_time = (current_time - timedelta(hours=i)).replace(minute=0, second=0, microsecond=0)
            history.append({
                "timestamp": past_time.strftime("%Y-%m-%d %H:%M"),
                "time": past_time.strftime("%H:%M"),
                "predicted": vol,
                "actual": vol,
                "speed": speed_est,
                "traffic": level,
                "source": "history"
            })
    return history


def fetch_data(lat, lon):
    try:
        response = requests.get(f"{BACKEND}/predict", params={"lat": lat, "lon": lon}, timeout=6)
        if response.status_code == 200:
            return response.json()
    except Exception as e:
        st.error(f"Unable to reach backend: {e}")
    return None


try:
    from streamlit import st_autorefresh
except ImportError:
    st_autorefresh = None

# ---------------- INITIAL HISTORY ----------------
if not st.session_state.analysis_history_loaded:
    st.session_state.analysis_history = fetch_history(lat, lon, DEFAULT_HISTORY_HOURS)
    st.session_state.analysis_history_loaded = True

# ---------------- LIVE DATA ----------------
live_data = fetch_data(lat, lon)
if live_data:
    current_time = datetime.now().replace(minute=0, second=0, microsecond=0)
    current_timestamp = current_time.strftime("%Y-%m-%d %H:%M")
    live_entry = {
        "timestamp": current_timestamp,
        "time": current_time.strftime("%H:%M"),
        "predicted": live_data.get("predicted_volume", 0),
        "actual": live_data.get("actual_volume", 0),
        "speed": live_data.get("speed", 0),
        "traffic": live_data.get("traffic_level", "Low"),
        "source": "live"
    }

    if st.session_state.analysis_history and st.session_state.analysis_history[-1].get("timestamp") == current_timestamp:
        st.session_state.analysis_history[-1].update(live_entry)
    else:
        st.session_state.analysis_history.append(live_entry)
    st.session_state.analysis_last_fetch = time.time()
else:
    st.warning("Live backend data is unavailable. Showing cached historical trend.")

searched_location = st.session_state.get('searched_location', 'Mumbai City Center')
if live_data:
    live_place = live_data.get("place") or searched_location
    status_name = live_place if live_place.lower() == searched_location.lower() else f"{live_place} ({searched_location})"
    status_text = f"✅ Analysis complete for {status_name}"
else:
    status_name = searched_location
    status_text = f"⏳ Loading traffic analysis for {status_name}..."
st.markdown(f"<div class='analysis-status'>{status_text}</div>", unsafe_allow_html=True)

history_df = pd.DataFrame(st.session_state.analysis_history)
if not history_df.empty:
    history_df["time_dt"] = pd.to_datetime(history_df["timestamp"], errors="coerce")
    history_df = history_df.sort_values("time_dt")
    history_df["level_value"] = history_df["traffic"].map({"Low": 1, "Medium": 2, "High": 3})
    history_df["level_color"] = history_df["traffic"].map(LEVEL_COLOR)
else:
    history_df = pd.DataFrame(columns=["timestamp", "time", "predicted", "actual", "speed", "traffic", "source", "time_dt", "level_value", "level_color"])

# ---------------- HEADER CARDS ----------------
place = live_data.get("place", "Mumbai") if live_data else "Mumbai"
traffic_label = live_data.get("traffic_level", "--") if live_data else "--"
actual_value = int(live_data.get("actual_volume", 0)) if live_data else 0
speed_value = int(live_data.get("speed", 0)) if live_data else 0
weather = live_data.get("weather", {}) if live_data else {}

col1, col2, col3, col4 = st.columns(4)
col1.markdown(f"""
<div class='card'><div class='card-title'>Location</div><div class='card-value'>{place}</div></div>
""", unsafe_allow_html=True)
col2.markdown(f"""
<div class='card'><div class='card-title'>Traffic Level</div><div class='card-value'>{traffic_label}</div></div>
""", unsafe_allow_html=True)
col3.markdown(f"""
<div class='card'><div class='card-title'>Actual Volume</div><div class='card-value'>{actual_value}</div></div>
""", unsafe_allow_html=True)
col4.markdown(f"""
<div class='card'><div class='card-title'>Speed</div><div class='card-value'>{speed_value} km/h</div></div>
""", unsafe_allow_html=True)

if weather:
    w1, w2, w3, w4 = st.columns(4)
    w1.markdown(f"""
    <div class='card'><div class='card-title'>Temp</div><div class='card-value'>{weather.get('temperature', '--')}°C</div></div>
    """, unsafe_allow_html=True)
    w2.markdown(f"""
    <div class='card'><div class='card-title'>Humidity</div><div class='card-value'>{weather.get('humidity', '--')}%</div></div>
    """, unsafe_allow_html=True)
    w3.markdown(f"""
    <div class='card'><div class='card-title'>Rain</div><div class='card-value'>{weather.get('rain', '--')} mm</div></div>
    """, unsafe_allow_html=True)
    w4.markdown(f"""
    <div class='card'><div class='card-title'>Clouds</div><div class='card-value'>{weather.get('cloudcover', '--')}%</div></div>
    """, unsafe_allow_html=True)

# ---------------- REFRESH CONTROLS ----------------
st.markdown('<div class="section-title">Refresh Controls</div>', unsafe_allow_html=True)
refresh_col, interval_col = st.columns([2, 1])
with refresh_col:
    if st.button("🔄 Refresh Now"):
        st.rerun()
with interval_col:
    interval_choice = st.selectbox("Auto-refresh interval", ["15 sec", "30 sec", "1 min", "1 hour"], index=3)
    st.session_state.analysis_refresh_interval = {"15 sec": 15, "30 sec": 30, "1 min": 60, "1 hour": 3600}[interval_choice]

interval_text = f"Every {interval_choice}"
next_refresh = int(max(0, st.session_state.analysis_refresh_interval - (datetime.now().timestamp() - st.session_state.analysis_last_fetch)))
st.markdown(f"<div class='status-chip'>Auto-refresh: {interval_text} · Next update in ~{next_refresh}s</div>", unsafe_allow_html=True)

if st_autorefresh is not None:
    st_autorefresh(interval=st.session_state.analysis_refresh_interval * 1000, key="analysis_autorefresh")

# ---------------- CHARTS ----------------
if not history_df.empty:
    st.markdown('<div class="section-title">Traffic Volume Trend</div>', unsafe_allow_html=True)
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=history_df["time_dt"],
        y=history_df["actual"],
        name="Actual",
        mode="lines+markers",
        line=dict(color="#22c55e", width=3),
        fill="tozeroy",
        marker=dict(size=6)
    ))
    fig.add_trace(go.Scatter(
        x=history_df["time_dt"],
        y=history_df["predicted"],
        name="Predicted",
        mode="lines+markers",
        line=dict(color="#3b82f6", width=2, dash="dash"),
        marker=dict(size=5)
    ))
    fig.update_layout(
        template="plotly_dark",
        legend=dict(bgcolor="#020617", bordercolor="#334155", borderwidth=1),
        xaxis=dict(title="Time", tickformat="%b %d %H:%M", tickangle=-45),
        yaxis=dict(title="Traffic Volume", rangemode="tozero"),
        hovermode="x unified",
        plot_bgcolor="#020617",
        paper_bgcolor="#020617"
    )
    st.plotly_chart(fig, use_container_width=True)

    st.markdown('<div class="section-title">Speed & Traffic Intensity</div>', unsafe_allow_html=True)
    fig2 = go.Figure()
    fig2.add_trace(go.Bar(
        x=history_df["time_dt"],
        y=history_df["level_value"],
        name="Traffic Level",
        marker_color=history_df["level_color"],
        opacity=0.75,
        yaxis="y2"
    ))
    fig2.add_trace(go.Scatter(
        x=history_df["time_dt"],
        y=history_df["speed"],
        name="Speed",
        mode="lines+markers",
        line=dict(color="#f59e0b", width=3),
        marker=dict(size=6)
    ))
    fig2.update_layout(
        template="plotly_dark",
        xaxis=dict(title="Time", tickformat="%b %d %H:%M", tickangle=-45),
        yaxis=dict(title="Speed (km/h)", side="left", rangemode="tozero"),
        yaxis2=dict(title="Traffic Level", overlaying="y", side="right", range=[0.5, 3.5], tickmode="array", tickvals=[1, 2, 3], ticktext=["Low", "Medium", "High"]),
        legend=dict(bgcolor="#020617", bordercolor="#334155", borderwidth=1),
        hovermode="x unified",
        plot_bgcolor="#020617",
        paper_bgcolor="#020617"
    )
    st.plotly_chart(fig2, use_container_width=True)

    st.markdown('<div class="section-title">Traffic Insights</div>', unsafe_allow_html=True)
    latest = history_df.iloc[-1]
    previous = history_df.iloc[-2] if len(history_df) > 1 else latest
    error_rate = abs(latest["actual"] - latest["predicted"]) / max(latest["actual"], 1) * 100 if latest["actual"] else 0
    momentum = latest["actual"] - previous["actual"]
    comfort = weather.get("humidity", 0)

    i1, i2, i3, i4 = st.columns(4)
    i1.markdown(f"""
    <div class='card'><div class='card-title'>Volume Change</div><div class='card-value'>{"+" if momentum >= 0 else ""}{int(momentum)} vehicles</div></div>
    """, unsafe_allow_html=True)
    i2.markdown(f"""
    <div class='card'><div class='card-title'>Prediction Error</div><div class='card-value'>{error_rate:.1f}%</div></div>
    """, unsafe_allow_html=True)
    i3.markdown(f"""
    <div class='card'><div class='card-title'>Average Volume</div><div class='card-value'>{int(history_df['actual'].mean())}</div></div>
    """, unsafe_allow_html=True)
    i4.markdown(f"""
    <div class='card'><div class='card-title'>Comfort Index</div><div class='card-value'>{100 - abs(45 - comfort):.0f}%</div></div>
    """, unsafe_allow_html=True)

    traffic_counts = history_df["traffic"].value_counts().reindex(["Low", "Medium", "High"], fill_value=0)
    st.markdown('<div class="section-title">Traffic Patterns Overview</div>', unsafe_allow_html=True)
    peak_hour = historical_data.loc[historical_data["traffic_volume"].idxmax()]["hour"]
    peak_volume = max(0, int(historical_data["traffic_volume"].max()))
    st.markdown(f"""
    <div class="card">
        <div class="card-title">Peak Hour Insight</div>
        <div class="card-value">Traffic peaks at {peak_hour:02d}:00 with average volume of {peak_volume} vehicles</div>
    </div>
    """, unsafe_allow_html=True)
    fig3 = go.Figure(go.Bar(
        x=traffic_counts.index,
        y=traffic_counts.values,
        marker_color=[LEVEL_COLOR.get(level, "#64748b") for level in traffic_counts.index]
    ))
    fig3.update_layout(template="plotly_dark", xaxis=dict(title="Traffic Level"), yaxis=dict(title="Observations"), plot_bgcolor="#020617", paper_bgcolor="#020617")
    st.plotly_chart(fig3, use_container_width=True)
    st.markdown("This bar chart shows the distribution of traffic levels (Low, Medium, High) observed throughout the day, highlighting peak congestion times.")
else:
    st.info("Waiting for historical data before rendering trend charts.")
