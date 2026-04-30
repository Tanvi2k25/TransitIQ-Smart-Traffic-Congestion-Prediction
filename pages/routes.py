import streamlit as st
import requests
import folium
from streamlit_folium import st_folium
from datetime import datetime

BACKEND = "http://127.0.0.1:5000"

# ---------------- STYLE ----------------
st.markdown("""
<style>
.page-title {
    font-size: 34px;
    font-weight: 700;
    margin-bottom: 8px;
}
.card {
    background: linear-gradient(135deg, #0f172a, #111827);
    padding: 10px;
    border-radius: 12px;
    color: white;
    border: 1px solid #334155;
    box-shadow: 0 6px 16px rgba(0, 0, 0, 0.18);
    margin-bottom: 6px;
    min-height: 120px;
    display: flex;
    flex-direction: column;
    justify-content: center;
    align-items: center;
    text-align: center;
}
.card.compact {
    min-height: auto;
    justify-content: flex-start;
    padding: 8px;
    text-align: left;
    align-items: flex-start;
}
.card h4 {
    margin: 0 0 8px;
    color: #94a3b8;
    font-size: 14px;
    letter-spacing: 0.8px;
    text-transform: uppercase;
}
.card p {
    margin: 2px 0;
    line-height: 1.4;
}
.route-badge {
    display: inline-flex;
    align-items: center;
    gap: 8px;
    font-size: 12px;
    padding: 6px 10px;
    border-radius: 999px;
    border: 1px solid rgba(148, 163, 184, 0.3);
    color: #cbd5e1;
    margin-bottom: 10px;
}
.route1 { border-left: 5px solid #22c55e; }
.route2 { border-left: 5px solid #3b82f6; }
.route3 { border-left: 5px solid #f59e0b; }
.route4 { border-left: 5px solid #8b5cf6; }
.route5 { border-left: 5px solid #ec4899; }
.detail-label {
    font-size: 12px;
    color: #94a3b8;
    text-transform: uppercase;
    letter-spacing: 0.8px;
}
.detail-value {
    font-size: 20px;
    font-weight: 700;
    margin-top: 4px;
}
.overview-card {
    min-height: auto;
    padding: 10px;
    margin-bottom: 6px;
    text-align: left;
}
.overview-card h4 {
    margin: 0 0 4px;
}
.overview-card p {
    margin: 0;
    font-size: 14px;
}
.stTextInput input, .stButton button {
    font-size: 14px !important;
}
.stButton button {
    width: 100% !important;
    margin-top: 24px !important;
}
</style>
""", unsafe_allow_html=True)

st.markdown('<div class="page-title">Route Traffic Explorer</div>', unsafe_allow_html=True)

if "routes_data" not in st.session_state:
    st.session_state.routes_data = None
    st.session_state.route_query = None

# ---------------- INPUT ----------------
overview_html = """
<div class='card overview-card'>
    <h4>Route Overview</h4>
    <p>Compare travel alternatives before you head out. Enter source and destination to view route options, estimated arrival time, congestion levels, and travel suggestions.</p>
</div>
"""
st.markdown(overview_html, unsafe_allow_html=True)

col1, col2, col3 = st.columns([2, 2, 1])
with col1:
    src = st.text_input("Source", placeholder="Mulund", value=st.session_state.get("route_src", ""))
with col2:
    dst = st.text_input("Destination", placeholder="Kurla", value=st.session_state.get("route_dst", ""))
with col3:
    if st.button("Show Route", key="show_route_top"):
        if not src or not dst:
            st.warning("Please enter both source and destination.")
        else:
            st.session_state.route_src = src
            st.session_state.route_dst = dst
            st.session_state.route_query = (src.strip().lower(), dst.strip().lower())
            st.session_state.routes_data = None

# ---------------- FETCH ----------------
if st.session_state.get("route_query"):
    current_query = (src.strip().lower(), dst.strip().lower())
    if current_query != st.session_state.route_query:
        st.session_state.routes_data = None
        st.session_state.route_query = current_query

if st.session_state.routes_data is None and st.session_state.get("route_query"):
    try:
        response = requests.get(
            f"{BACKEND}/routes",
            params={"src": src, "dst": dst},
            timeout=15,
        )
        if response.status_code == 200:
            st.session_state.routes_data = response.json()
        else:
            st.error(f"Unable to fetch routes (status {response.status_code}).")
    except Exception as exc:
        st.error(f"Route lookup error: {exc}")

if not st.session_state.routes_data:
    st.info("Enter source and destination, then click Show Route to visualize alternative paths.")
    st.stop()

data = st.session_state.routes_data
routes = data.get("routes", [])
source = data.get("source", {"name": src, "lat": 0, "lon": 0})
dest = data.get("destination", {"name": dst, "lat": 0, "lon": 0})

# ---------------- HIGHLIGHTS ----------------
if routes:
    fastest_route = min(routes, key=lambda r: r.get("time", float("inf")))
    fastest_index = routes.index(fastest_route) + 1
    cheapest_route = min(routes, key=lambda r: r.get("predicted_volume", float("inf")))
    safest_route = min(routes, key=lambda r: r.get("actual_congestion", 1.0))

    suggestion_lines = []
    if fastest_route.get("congestion", 0) >= 0.7:
        suggestion_lines.append("The fastest route may still face heavy congestion, so allow extra time.")
    if fastest_route.get("distance", 0) / 1000 > 20:
        suggestion_lines.append("This is a longer trip; check fuel and rest stops before departure.")
    if any(r.get("congestion", 0) > 0.7 for r in routes):
        suggestion_lines.append("Peak traffic is likely on one or more route options. Consider leaving outside rush hour.")
    if not suggestion_lines:
        suggestion_lines.append("Route looks clear. Travel with normal precautions and keep traffic updates handy.")
    travel_suggestion = " ".join(suggestion_lines)

    row1_col1, row1_col2 = st.columns(2)
    row1_col1.markdown(f"""
    <div class='card compact'>
        <h4>Source</h4>
        <p>{source.get('name', src)}</p>
    </div>
    """, unsafe_allow_html=True)
    row1_col2.markdown(f"""
    <div class='card compact'>
        <h4>Destination</h4>
        <p>{dest.get('name', dst)}</p>
    </div>
    """, unsafe_allow_html=True)

    row2_col1, row2_col2 = st.columns(2)
    row2_col1.markdown(f"""
    <div class='card compact'>
        <h4>Fastest Route</h4>
        <p class='detail-value'>{fastest_route.get('time', 0)/60:.0f} min</p>
    </div>
    """, unsafe_allow_html=True)
    row2_col2.markdown(f"""
    <div class='card compact'>
        <h4>Lightest Traffic</h4>
        <p class='detail-value'>{(1 - safest_route.get('actual_congestion', 0))*100:.0f}% free</p>
    </div>
    """, unsafe_allow_html=True)
else:
    st.warning("No routes returned from the backend.")

# ---------------- MAP + ROUTE LIST ----------------
map_col, info_col = st.columns([2.2, 1])

with map_col:
    center_lat = (source.get("lat", 0) + dest.get("lat", 0)) / 2
    center_lon = (source.get("lon", 0) + dest.get("lon", 0)) / 2
    m = folium.Map(location=[center_lat, center_lon], zoom_start=12)

    colors = ["#22c55e", "#3b82f6", "#f59e0b", "#8b5cf6", "#ec4899"]
    bounds = []

    for idx, route in enumerate(routes):
        points = route.get("points", [])
        if not points or len(points) < 2:
            continue

        if len(points) > 80:
            points = points[::4]

        bounds.extend(points)
        predicted_congestion = route.get("predicted_congestion", 0)
        actual_congestion = route.get("actual_congestion", 0)

        level = "Unknown"
        if actual_congestion is not None:
            if actual_congestion < 0.25:
                level = "Low"
            elif actual_congestion < 0.5:
                level = "Medium"
            else:
                level = "High"

        route_color = colors[idx % len(colors)]
        tooltip = (
            f"Route {idx+1}\n"
            f"Traffic: {level}\n"
            f"Distance: {route.get('distance', 0)/1000:.1f} km\n"
            f"Time: {route.get('time', 0)/60:.0f} min\n"
            f"Predicted Volume: {int(route.get('predicted_volume', 0))}\n"
            f"Predicted Congestion: {predicted_congestion:.2f}\n"
            f"Actual Congestion: {actual_congestion:.2f}\n"
            f"Speed: {route.get('speed', '--')}"
        )

        folium.PolyLine(
            locations=points,
            color=route_color,
            weight=6,
            opacity=0.9,
            tooltip=tooltip,
        ).add_to(m)

    folium.Marker(
        [source.get("lat", 0), source.get("lon", 0)],
        tooltip=f"Source: {source.get('name', src)}",
        icon=folium.Icon(color="green", icon="play"),
    ).add_to(m)

    folium.Marker(
        [dest.get("lat", 0), dest.get("lon", 0)],
        tooltip=f"Destination: {dest.get('name', dst)}",
        icon=folium.Icon(color="red", icon="stop"),
    ).add_to(m)

    if bounds:
        m.fit_bounds(bounds)

    st_folium(m, height=560, use_container_width=True)

    st.markdown("### Routes found")
    max_columns = min(4, len(routes))
    for row_start in range(0, len(routes), max_columns):
        row_routes = routes[row_start:row_start + max_columns]
        cols = st.columns(len(row_routes))
        for local_idx, (col, route) in enumerate(zip(cols, row_routes)):
            route_idx = row_start + local_idx
            distance = route.get('distance', 0) / 1000
            duration = route.get('time', 0) / 60
            volume = route.get('predicted_volume', 0)
            predicted_congestion = route.get('predicted_congestion', 0)
            actual_congestion = route.get('actual_congestion', 0)

            # Determine congestion level based on actual congestion
            if actual_congestion is None:
                level = 'Unknown'
            elif actual_congestion < 0.25:
                level = 'Low'
            elif actual_congestion < 0.5:
                level = 'Medium'
            else:
                level = 'High'

            # Calculate model accuracy indicator
            accuracy_diff = abs(predicted_congestion - actual_congestion)
            if accuracy_diff < 0.1:
                accuracy = "Accurate"
            elif accuracy_diff < 0.3:
                accuracy = "Moderate"
            else:
                accuracy = "Inaccurate"

            col.markdown(f"""
            <div class="card route{(route_idx % 5) + 1}">
                <div class="route-badge">Route {route_idx+1} • {route.get('type', 'Route')}</div>
                <p><strong>Traffic:</strong> {level}</p>
                <p><strong>Distance:</strong> {distance:.2f} km</p>
                <p><strong>Duration:</strong> {duration:.1f} min</p>
                <p><strong>Predicted Volume:</strong> {int(volume)}</p>
                <p><strong>Predicted Congestion:</strong> {predicted_congestion:.2f}</p>
                <p><strong>Actual Congestion:</strong> {actual_congestion:.2f}</p>
                <p><strong>Model Accuracy:</strong> {accuracy}</p>
            </div>
            """, unsafe_allow_html=True)

with info_col:
    st.markdown(f"""
    <div class='card'>
        <h4>Fastest Arrival</h4>
        <p class='detail-value'>{fastest_route.get('time', 0)/60:.0f} min</p>
        <p>{fastest_route.get('distance', 0)/1000:.1f} km via the quickest route.</p>
    </div>
    """, unsafe_allow_html=True)

    chosen_reason = "This route is chosen because it offers the shortest estimated travel time among all alternatives."
    if fastest_route.get('actual_congestion', 0) >= 0.7:
        chosen_reason = "It is still the quickest but may face heavy traffic, so expect some delay and consider leaving outside peak hours."
    elif fastest_route.get('actual_congestion', 0) >= 0.4:
        chosen_reason = "Fast and relatively steady traffic, but monitor congestion updates to avoid slowdowns."

    predicted_congestion = fastest_route.get('predicted_congestion', 0)
    actual_congestion = fastest_route.get('actual_congestion', 0)
    accuracy_diff = abs(predicted_congestion - actual_congestion)
    model_accuracy = "Accurate" if accuracy_diff < 0.1 else "Moderate" if accuracy_diff < 0.3 else "Inaccurate"

    st.markdown(f"""
    <div class='card'>
        <h4>Shortest Route</h4>
        <p class='detail-value'>Route {fastest_index} • {fastest_route.get('type', 'Fastest')}</p>
        <p>{fastest_route.get('distance', 0)/1000:.1f} km, {fastest_route.get('time', 0)/60:.0f} min</p>
        <p><strong>Predicted Congestion:</strong> {predicted_congestion:.2f}</p>
        <p><strong>Actual Congestion:</strong> {actual_congestion:.2f}</p>
        <p><strong>Model Accuracy:</strong> {model_accuracy}</p>
        <p>{chosen_reason}</p>
    </div>
    """, unsafe_allow_html=True)

    st.markdown(f"""
    <div class='card'>
        <h4>Travel Advice</h4>
        <p>{travel_suggestion}</p>
    </div>
    """, unsafe_allow_html=True)
