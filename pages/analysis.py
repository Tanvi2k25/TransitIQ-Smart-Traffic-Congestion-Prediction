
import streamlit as st
import requests
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta
import time

BACKEND = "http://127.0.0.1:5000"
DEFAULT_HISTORY_HOURS = 12

LEVEL_COLOR = {
    "Low": "#22c55e",
    "Medium": "#f59e0b",
    "High": "#ef4444"
}


# ---------------- HISTORICAL DATA ----------------
@st.cache_data
def load_historical_data():
    df = pd.read_csv("data/Metro_Interstate_Traffic_Volume.csv")
    df["date_time"] = pd.to_datetime(df["date_time"], errors="coerce")
    df["traffic_volume"] = pd.to_numeric(
        df["traffic_volume"], errors="coerce"
    )

    df = df.dropna(subset=["date_time", "traffic_volume"])
    df["hour"] = df["date_time"].dt.hour

    return (
        df.groupby("hour")["traffic_volume"]
        .mean()
        .reset_index()
    )


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

.card-title {
    font-size: 12px;
    color: #94a3b8;
    text-transform: uppercase;
    letter-spacing: 1px;
}

.card-value {
    font-size: 26px;
    font-weight: 700;
    margin-top: 10px;
    color: #f8fafc;
}

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
</style>
""", unsafe_allow_html=True)


st.markdown(
    '<div class="section-title">Traffic Analysis Dashboard</div>',
    unsafe_allow_html=True
)


# ---------------- SESSION STATE ----------------
defaults = {
    "analysis_history": [],
    "analysis_history_loaded": False,
    "analysis_location_key": None,
    "analysis_last_fetch": 0,
    "analysis_refresh_interval": 3600
}

for key, value in defaults.items():
    if key not in st.session_state:
        st.session_state[key] = value


lat = st.session_state.get("lat", 19.0760)
lon = st.session_state.get("lon", 72.8777)

location_key = (round(lat, 5), round(lon, 5))

if st.session_state.analysis_location_key != location_key:
    st.session_state.analysis_history = []
    st.session_state.analysis_history_loaded = False
    st.session_state.analysis_location_key = location_key


# ---------------- HELPERS ----------------
def traffic_level(volume):
    if volume < 2000:
        return "Low"
    elif volume < 4000:
        return "Medium"
    return "High"


def fetch_history(lat, lon, hours=DEFAULT_HISTORY_HOURS):
    try:
        response = requests.get(
            f"{BACKEND}/history",
            params={
                "lat": lat,
                "lon": lon,
                "hours": hours
            },
            timeout=20
        )

        response.raise_for_status()
        payload = response.json()

        history = []

        for row in payload.get("history", []):
            timestamp = row.get("timestamp", "")

            history.append({
                "timestamp": timestamp,
                "time": timestamp[-5:] if timestamp else "",
                "predicted": row.get("predicted_volume"),
                "estimated": row.get("estimated_volume", row.get("actual_volume")),
                "speed": row.get("speed"),
                "traffic": row.get("traffic_level", "Low"),
                "source": "backend_estimate"
            })

        if history:
            return history

    except Exception as e:
        st.warning(
            f"Backend history unavailable. "
            f"Using reference dataset instead. Details: {e}"
        )

    # Fallback: Metro Interstate reference data
    current_time = datetime.now()
    history = []

    for i in range(hours, 0, -1):
        past_time = (
            current_time - timedelta(hours=i)
        ).replace(minute=0, second=0, microsecond=0)

        hour = past_time.hour

        row = historical_data[
            historical_data["hour"] == hour
        ]

        if not row.empty:
            volume = float(row["traffic_volume"].iloc[0])
            level = traffic_level(volume)

            speed_est = {
                "Low": 50,
                "Medium": 30,
                "High": 15
            }[level]

            history.append({
                "timestamp": past_time.strftime("%Y-%m-%d %H:%M"),
                "time": past_time.strftime("%H:%M"),
                "predicted": volume,
                "estimated": volume,
                "speed": speed_est,
                "traffic": level,
                "source": "reference_dataset"
            })

    return history


def fetch_data(lat, lon):
    try:
        response = requests.get(
            f"{BACKEND}/predict",
            params={"lat": lat, "lon": lon},
            timeout=6
        )

        response.raise_for_status()
        return response.json()

    except Exception as e:
        st.error(f"Unable to reach backend: {e}")
        return None


# ---------------- AUTO REFRESH ----------------
try:
    from streamlit import st_autorefresh
except ImportError:
    st_autorefresh = None


# ---------------- INITIAL HISTORY ----------------
if not st.session_state.analysis_history_loaded:
    st.session_state.analysis_history = fetch_history(
        lat, lon, DEFAULT_HISTORY_HOURS
    )
    st.session_state.analysis_history_loaded = True


# ---------------- LIVE DATA ----------------
live_data = fetch_data(lat, lon)

if live_data:
    current_time = datetime.now().replace(
        minute=0, second=0, microsecond=0
    )

    current_timestamp = current_time.strftime("%Y-%m-%d %H:%M")

    live_entry = {
        "timestamp": current_timestamp,
        "time": current_time.strftime("%H:%M"),
        "predicted": live_data.get("predicted_volume"),
        "estimated": live_data.get("estimated_volume", live_data.get("actual_volume")),
        "speed": live_data.get("speed"),
        "traffic": live_data.get("traffic_level", "Low"),
        "source": "live_estimate"
    }

    if (
        st.session_state.analysis_history
        and st.session_state.analysis_history[-1].get("timestamp")
        == current_timestamp
    ):
        st.session_state.analysis_history[-1].update(live_entry)
    else:
        st.session_state.analysis_history.append(live_entry)

    st.session_state.analysis_last_fetch = time.time()

else:
    st.warning(
        "Live backend data is unavailable. "
        "Showing previously loaded data where available."
    )


# ---------------- LOCATION STATUS ----------------
searched_location = st.session_state.get(
    "searched_location", "Mumbai City Center"
)

if live_data:
    live_place = live_data.get("place") or searched_location

    status_name = (
        live_place
        if live_place.lower() == searched_location.lower()
        else f"{live_place} ({searched_location})"
    )

    status_text = f"✅ Analysis complete for {status_name}"
else:
    status_text = f"⏳ Loading traffic analysis for {searched_location}..."


st.markdown(
    f"<div class='analysis-status'>{status_text}</div>",
    unsafe_allow_html=True
)


# ---------------- PREPARE HISTORY ----------------
history_df = pd.DataFrame(st.session_state.analysis_history)

if not history_df.empty:

    history_df["time_dt"] = pd.to_datetime(
        history_df["timestamp"], errors="coerce"
    )

    # Convert numeric columns safely
    for column in ["predicted", "estimated", "speed"]:
        history_df[column] = pd.to_numeric(
            history_df[column], errors="coerce"
        )

    # Remove rows with invalid timestamps or missing volume
    history_df = history_df.dropna(
        subset=["time_dt", "estimated"]
    )

    history_df = history_df.sort_values("time_dt")

    history_df["level_value"] = history_df["traffic"].map({
        "Low": 1,
        "Medium": 2,
        "High": 3
    })

    history_df["level_color"] = history_df["traffic"].map(
        LEVEL_COLOR
    )

else:
    history_df = pd.DataFrame(
        columns=[
            "timestamp", "time", "predicted", "estimated",
            "speed", "traffic", "source", "time_dt",
            "level_value", "level_color"
        ]
    )


# ---------------- HEADER CARDS ----------------
place = live_data.get("place", "Mumbai") if live_data else "Mumbai"

traffic_label = (
    live_data.get("traffic_level", "--") if live_data else "--"
)

estimated_value = (
    pd.to_numeric(
        live_data.get("estimated_volume", live_data.get("actual_volume")), errors="coerce"
    ) if live_data else None
)

speed_value = (
    pd.to_numeric(
        live_data.get("speed"), errors="coerce"
    ) if live_data else None
)

weather = live_data.get("weather", {}) if live_data else {}


def display_number(value):
    if value is None or pd.isna(value):
        return "--"
    return str(int(value))


col1, col2, col3, col4 = st.columns(4)

col1.markdown(f"""
<div class='card'>
    <div class='card-title'>Location</div>
    <div class='card-value'>{place}</div>
</div>
""", unsafe_allow_html=True)

col2.markdown(f"""
<div class='card'>
    <div class='card-title'>Traffic Level</div>
    <div class='card-value'>{traffic_label}</div>
</div>
""", unsafe_allow_html=True)

col3.markdown(f"""
<div class='card'>
    <div class='card-title'>Estimated Volume</div>
    <div class='card-value'>{display_number(estimated_value)}</div>
</div>
""", unsafe_allow_html=True)

col4.markdown(f"""
<div class='card'>
    <div class='card-title'>Speed</div>
    <div class='card-value'>{display_number(speed_value)} km/h</div>
</div>
""", unsafe_allow_html=True)


# ---------------- WEATHER CARDS ----------------
if weather:
    w1, w2, w3, w4 = st.columns(4)

    w1.markdown(f"""
    <div class='card'>
        <div class='card-title'>Temperature</div>
        <div class='card-value'>{weather.get('temperature', '--')}°C</div>
    </div>
    """, unsafe_allow_html=True)

    w2.markdown(f"""
    <div class='card'>
        <div class='card-title'>Humidity</div>
        <div class='card-value'>{weather.get('humidity', '--')}%</div>
    </div>
    """, unsafe_allow_html=True)

    w3.markdown(f"""
    <div class='card'>
        <div class='card-title'>Rain</div>
        <div class='card-value'>{weather.get('rain', '--')} mm</div>
    </div>
    """, unsafe_allow_html=True)

    w4.markdown(f"""
    <div class='card'>
        <div class='card-title'>Clouds</div>
        <div class='card-value'>{weather.get('cloudcover', '--')}%</div>
    </div>
    """, unsafe_allow_html=True)
    if weather.get("source") == "Fallback estimate":
        st.caption("Weather provider is unavailable; these weather values are backend fallbacks, not current readings.")

# ---------------- REFRESH CONTROLS ----------------
st.markdown(
    '<div class="section-title">Refresh Controls</div>',
    unsafe_allow_html=True
)

refresh_col, interval_col = st.columns([2, 1])

with refresh_col:
    if st.button("🔄 Refresh Now"):
        st.rerun()

with interval_col:
    interval_choice = st.selectbox(
        "Auto-refresh interval",
        ["15 sec", "30 sec", "1 min", "1 hour"],
        index=3
    )

    st.session_state.analysis_refresh_interval = {
        "15 sec": 15,
        "30 sec": 30,
        "1 min": 60,
        "1 hour": 3600
    }[interval_choice]


interval_text = f"Every {interval_choice}"

next_refresh = int(max(
    0,
    st.session_state.analysis_refresh_interval
    - (time.time() - st.session_state.analysis_last_fetch)
))

st.markdown(
    f"<div class='status-chip'>"
    f"Auto-refresh: {interval_text} · "
    f"Next update in ~{next_refresh}s"
    f"</div>",
    unsafe_allow_html=True
)

if st_autorefresh is not None:
    st_autorefresh(
        interval=st.session_state.analysis_refresh_interval * 1000,
        key="analysis_autorefresh"
    )


# ---------------- CHARTS AND INSIGHTS ----------------
if not history_df.empty:

    st.markdown(
        '<div class="section-title">Estimated Traffic Volume Trend</div>',
        unsafe_allow_html=True
    )

    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=history_df["time_dt"],
        y=history_df["estimated"],
        name="Estimated Volume",
        mode="lines+markers",
        line=dict(color="#22c55e", width=3),
        fill="tozeroy",
        marker=dict(size=6)
    ))

    fig.add_trace(go.Scatter(
        x=history_df["time_dt"],
        y=history_df["predicted"],
        name="Predicted Volume",
        mode="lines+markers",
        line=dict(color="#3b82f6", width=2, dash="dash"),
        marker=dict(size=5)
    ))

    fig.update_layout(
        template="plotly_dark",
        xaxis=dict(
            title="Time",
            tickformat="%b %d %H:%M",
            tickangle=-45
        ),
        yaxis=dict(
            title="Estimated Traffic Volume",
            rangemode="tozero"
        ),
        hovermode="x unified",
        plot_bgcolor="#020617",
        paper_bgcolor="#020617"
    )

    st.plotly_chart(fig, use_container_width=True)


    # ---------------- SPEED AND TRAFFIC ----------------
    st.markdown(
        '<div class="section-title">Speed & Traffic Intensity</div>',
        unsafe_allow_html=True
    )

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
        xaxis=dict(
            title="Time",
            tickformat="%b %d %H:%M",
            tickangle=-45
        ),
        yaxis=dict(
            title="Speed (km/h)",
            side="left",
            rangemode="tozero"
        ),
        yaxis2=dict(
            title="Traffic Level",
            overlaying="y",
            side="right",
            range=[0.5, 3.5],
            tickmode="array",
            tickvals=[1, 2, 3],
            ticktext=["Low", "Medium", "High"]
        ),
        hovermode="x unified",
        plot_bgcolor="#020617",
        paper_bgcolor="#020617"
    )

    st.plotly_chart(fig2, use_container_width=True)


    # ---------------- TRAFFIC INSIGHTS ----------------
    st.markdown(
        '<div class="section-title">Traffic Insights</div>',
        unsafe_allow_html=True
    )

    # Use only valid numeric observations
    valid_volumes = history_df["estimated"].dropna()

    if not valid_volumes.empty:

        latest = history_df.iloc[-1]

        previous = (
            history_df.iloc[-2]
            if len(history_df) > 1
            else latest
        )

        volume_change = float(
            latest["estimated"] - previous["estimated"]
        )

        average_volume = float(valid_volumes.mean())

    else:
        volume_change = 0
        average_volume = 0

    humidity = pd.to_numeric(
        weather.get("humidity", 45), errors="coerce"
    )

    if pd.isna(humidity):
        humidity = 45

    comfort_index = max(
        0,
        100 - abs(45 - float(humidity))
    )

    i1, i2, i3, i4 = st.columns(4)

    i1.markdown(f"""
    <div class='card'>
        <div class='card-title'>Change since previous estimate</div>
        <div class='card-value'>
            {"↑" if volume_change > 0 else "↓" if volume_change < 0 else "→"}
            {abs(int(volume_change)):,} vehicles
        </div>
        <div>Estimated change between samples</div>
    </div>
    """, unsafe_allow_html=True)

    i2.markdown("""
    <div class='card'>
        <div class='card-title'>Data Basis</div>
        <div class='card-value'>Estimated</div>
    </div>
    """, unsafe_allow_html=True)

    i3.markdown(f"""
    <div class='card'>
        <div class='card-title'>Average Estimated Volume</div>
        <div class='card-value'>{int(average_volume)}</div>
    </div>
    """, unsafe_allow_html=True)

    i4.markdown(f"""
    <div class='card'>
        <div class='card-title'>Humidity Comfort (Approx.)</div>
        <div class='card-value'>{comfort_index:.0f}%</div>
    </div>
    """, unsafe_allow_html=True)


    # ---------------- PEAK HOUR ----------------
    st.markdown(
        '<div class="section-title">Traffic Patterns Overview</div>',
        unsafe_allow_html=True
    )

    if not historical_data.empty:

        peak_hour_row = historical_data.loc[
            historical_data["traffic_volume"].idxmax()
        ]

        peak_hour = int(peak_hour_row["hour"])
        peak_volume = int(peak_hour_row["traffic_volume"])

        st.markdown(f"""
        <div class="card">
            <div class="card-title">
                Reference Dataset Peak-Hour Insight
            </div>
            <div class="card-value">
                Busiest average hour: {peak_hour:02d}:00
                ({peak_volume} vehicles)
            </div>
        </div>
        """, unsafe_allow_html=True)


    # ---------------- TRAFFIC DISTRIBUTION ----------------
    traffic_counts = history_df["traffic"].value_counts().reindex(
        ["Low", "Medium", "High"],
        fill_value=0
    )

    fig3 = go.Figure(go.Bar(
        x=traffic_counts.index,
        y=traffic_counts.values,
        marker_color=[
            LEVEL_COLOR[level]
            for level in traffic_counts.index
        ]
    ))

    fig3.update_layout(
        template="plotly_dark",
        xaxis=dict(title="Traffic Level"),
        yaxis=dict(title="Observations"),
        plot_bgcolor="#020617",
        paper_bgcolor="#020617"
    )

    st.plotly_chart(fig3, use_container_width=True)

else:
    st.info(
        "Waiting for valid historical data before rendering charts."
    )
