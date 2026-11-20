
import streamlit as st
import requests
import folium
from streamlit_folium import st_folium
from html import escape

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


def number(value, default=0):
    """Safely convert API values into numbers."""
    try:
        result = float(value)
        return result if result == result else default
    except (TypeError, ValueError):
        return default


def congestion_level(value):
    if value is None:
        return "Unknown"
    if value < 0.25:
        return "Low"
    if value < 0.50:
        return "Medium"
    return "High"


st.markdown(
    '<div class="page-title">Route Traffic Explorer</div>',
    unsafe_allow_html=True
)

if "routes_data" not in st.session_state:
    st.session_state.routes_data = None
    st.session_state.route_query = None

# ---------------- INPUT ----------------
st.markdown("""
<div class='card overview-card'>
    <h4>Route Overview</h4>
    <p>Compare travel alternatives before you head out. Enter source and destination to view route options, estimated arrival time, congestion levels, and travel suggestions.</p>
</div>
""", unsafe_allow_html=True)

col1, col2, col3 = st.columns([2, 2, 1])

with col1:
    src = st.text_input(
        "Source",
        placeholder="Mulund",
        value=st.session_state.get("route_src", "")
    )

with col2:
    dst = st.text_input(
        "Destination",
        placeholder="Kurla",
        value=st.session_state.get("route_dst", "")
    )

with col3:
    if st.button("Show Route", key="show_route_top"):
        if not src.strip() or not dst.strip():
            st.warning("Please enter both source and destination.")
        else:
            st.session_state.route_src = src.strip()
            st.session_state.route_dst = dst.strip()
            st.session_state.route_query = (
                src.strip().lower(),
                dst.strip().lower()
            )
            st.session_state.routes_data = None

# ---------------- FETCH ----------------
# Results stay attached to the last submitted query while the user edits.
if (
    st.session_state.routes_data is None
    and st.session_state.get("route_query")
):
    try:
        response = requests.get(
            f"{BACKEND}/routes",
            params={
                "src": st.session_state.route_src,
                "dst": st.session_state.route_dst
            },
            timeout=20
        )

        response.raise_for_status()
        st.session_state.routes_data = response.json()

    except requests.RequestException as exc:
        st.error(f"Route lookup error: {exc}")
        st.stop()

if not st.session_state.routes_data:
    st.info(
        "Enter source and destination, then click Show Route "
        "to visualize alternative paths."
    )
    st.stop()

# ---------------- ROUTE DATA ----------------
data = st.session_state.routes_data
routes = data.get("routes", [])

source = data.get(
    "source",
    {"name": src, "lat": 0, "lon": 0}
)
dest = data.get(
    "destination",
    {"name": dst, "lat": 0, "lon": 0}
)

if not routes:
    st.warning("No routes were returned by the backend.")
    st.stop()

# ---------------- ROUTE SELECTION ----------------
# Fastest = minimum travel time
fastest_route = min(
    routes,
    key=lambda r: number(r.get("time"), float("inf"))
)

# Shortest = minimum distance
shortest_route = min(
    routes,
    key=lambda r: number(r.get("distance"), float("inf"))
)

# Lightest traffic = minimum predicted congestion
lightest_route = min(
    routes,
    key=lambda r: number(
            r.get("route_congestion"), float("inf")
    )
)

fastest_index = routes.index(fastest_route) + 1
shortest_index = routes.index(shortest_route) + 1
lightest_index = routes.index(lightest_route) + 1

# ---------------- TRAVEL ADVICE ----------------
fastest_congestion = fastest_route.get("route_congestion")
fastest_congestion = (
    number(fastest_congestion)
    if fastest_congestion is not None else None
)

suggestion_lines = []

if fastest_congestion is None:
    suggestion_lines.append(
        "Congestion information is unavailable. Check live traffic before departure."
    )
elif fastest_congestion >= 0.7:
    suggestion_lines.append(
        "The fastest route may face heavy congestion. Allow extra travel time."
    )
elif fastest_congestion >= 0.4:
    suggestion_lines.append(
        "Moderate congestion is predicted. Monitor traffic updates."
    )
else:
    suggestion_lines.append(
        "The predicted congestion is low. Travel with normal precautions."
    )

if number(fastest_route.get("distance")) / 1000 > 20:
    suggestion_lines.append(
        "This is a longer trip; plan your journey accordingly."
    )

travel_suggestion = " ".join(suggestion_lines)

# ---------------- ROUTE OVERVIEW ----------------
row1_col1, row1_col2 = st.columns(2)

row1_col1.markdown(f"""
<div class='card compact'>
    <h4>Source</h4>
    <p>{escape(str(source.get('name', src)))}</p>
</div>
""", unsafe_allow_html=True)

row1_col2.markdown(f"""
<div class='card compact'>
    <h4>Destination</h4>
    <p>{escape(str(dest.get('name', dst)))}</p>
</div>
""", unsafe_allow_html=True)

row2_col1, row2_col2 = st.columns(2)

row2_col1.markdown(f"""
<div class='card compact'>
    <h4>Fastest Route</h4>
    <p class='detail-value'>{number(fastest_route.get('time')) / 60:.0f} min</p>
</div>
""", unsafe_allow_html=True)

lightest_congestion = lightest_route.get("route_congestion")

if lightest_congestion is None:
    lightest_text = "Unavailable"
else:
    lightest_text = (
        f"{(1 - number(lightest_congestion)) * 100:.0f}% free"
    )

row2_col2.markdown(f"""
<div class='card compact'>
    <h4>Lightest Traffic</h4>
    <p class='detail-value'>{lightest_text}</p>
</div>
""", unsafe_allow_html=True)

# ---------------- MAP ----------------
map_col, info_col = st.columns([2.2, 1])

with map_col:
    center_lat = (
        number(source.get("lat")) + number(dest.get("lat"))
    ) / 2

    center_lon = (
        number(source.get("lon")) + number(dest.get("lon"))
    ) / 2

    m = folium.Map(
        location=[center_lat, center_lon],
        zoom_start=12
    )

    colors = [
        "#22c55e", "#3b82f6", "#f59e0b",
        "#8b5cf6", "#ec4899"
    ]

    bounds = []

    for idx, route in enumerate(routes):
        points = route.get("points", [])

        if not points or len(points) < 2:
            continue

        if len(points) > 80:
            points = points[::4]

        bounds.extend(points)

        predicted_congestion = route.get("route_congestion")
        predicted_congestion = (
            number(predicted_congestion)
            if predicted_congestion is not None else None
        )

        level = congestion_level(predicted_congestion)

        distance = number(route.get("distance")) / 1000
        duration = number(route.get("time")) / 60
        volume = number(route.get("predicted_volume"))

        congestion_text = (
            f"{predicted_congestion:.2f}"
            if predicted_congestion is not None
            else "Unavailable"
        )

        tooltip = (
            f"Route {idx + 1} | {level} | "
            f"Distance: {distance:.2f} km | "
            f"Time: {duration:.1f} min | "
            f"Predicted Volume: {volume:.0f} | "
            f"Predicted Congestion: {congestion_text}"
        )

        folium.PolyLine(
            locations=points,
            color=colors[idx % len(colors)],
            weight=6,
            opacity=0.9,
            tooltip=tooltip
        ).add_to(m)

    folium.Marker(
        [number(source.get("lat")), number(source.get("lon"))],
        tooltip=f"Source: {source.get('name', src)}",
        icon=folium.Icon(color="green", icon="play")
    ).add_to(m)

    folium.Marker(
        [number(dest.get("lat")), number(dest.get("lon"))],
        tooltip=f"Destination: {dest.get('name', dst)}",
        icon=folium.Icon(color="red", icon="stop")
    ).add_to(m)

    if bounds:
        m.fit_bounds(bounds)

    st_folium(m, height=560, use_container_width=True)

    # ---------------- ROUTE CARDS ----------------
    st.markdown("### Routes found")

    colors_count = min(4, len(routes))

    for row_start in range(0, len(routes), colors_count):
        row_routes = routes[row_start:row_start + colors_count]
        cols = st.columns(len(row_routes))

        for local_idx, (col, route) in enumerate(
            zip(cols, row_routes)
        ):
            route_idx = row_start + local_idx

            distance = number(route.get("distance")) / 1000
            duration = number(route.get("time")) / 60
            volume = number(route.get("predicted_volume"))

            predicted_congestion = route.get("route_congestion")

            if predicted_congestion is not None:
                predicted_congestion = number(
                    predicted_congestion
                )

            level = congestion_level(predicted_congestion)

            congestion_display = (
                f"{predicted_congestion:.2f}"
                if predicted_congestion is not None
                else "Unavailable"
            )

            route_type = escape(str(route.get("type", "Route")))

            col.markdown(f"""
            <div class="card route{(route_idx % 5) + 1}">
                <div class="route-badge">
                    Route {route_idx + 1} • {route_type}
                </div>
                <p><strong>Traffic:</strong> {level}</p>
                <p><strong>Distance:</strong> {distance:.2f} km</p>
                <p><strong>Duration:</strong> {duration:.1f} min</p>
                <p><strong>Predicted Volume:</strong> {volume:.0f}</p>
                <p><strong>Predicted Congestion:</strong> {congestion_display}</p>
            </div>
            """, unsafe_allow_html=True)

# ---------------- ROUTE INFORMATION ----------------
with info_col:

    st.markdown(f"""
    <div class='card'>
        <h4>Fastest Arrival</h4>
        <p class='detail-value'>
            {number(fastest_route.get('time')) / 60:.0f} min
        </p>
        <p>
            {number(fastest_route.get('distance')) / 1000:.1f} km
            via Route {fastest_index}.
        </p>
    </div>
    """, unsafe_allow_html=True)

    shortest_congestion = shortest_route.get(
        "predicted_congestion"
    )

    shortest_congestion_text = (
        f"{number(shortest_congestion):.2f}"
        if shortest_congestion is not None
        else "Unavailable"
    )

    st.markdown(f"""
    <div class='card'>
        <h4>Shortest Route</h4>
        <p class='detail-value'>
            Route {shortest_index} •
            {escape(str(shortest_route.get('type', 'Route')))}
        </p>
        <p>
            {number(shortest_route.get('distance')) / 1000:.2f} km,
            {number(shortest_route.get('time')) / 60:.1f} min
        </p>
        <p>
            <strong>Predicted Congestion:</strong>
            {shortest_congestion_text}
        </p>
        <p>This route is selected because it has the
        shortest estimated distance.</p>
    </div>
    """, unsafe_allow_html=True)

    st.markdown(f"""
    <div class='card'>
        <h4>Lightest Traffic</h4>
        <p class='detail-value'>Route {lightest_index}</p>
        <p>
            {number(lightest_route.get('distance')) / 1000:.2f} km,
            {number(lightest_route.get('time')) / 60:.1f} min
        </p>
        <p>{lightest_text} according to predicted congestion.</p>
    </div>
    """, unsafe_allow_html=True)

    st.markdown(f"""
    <div class='card'>
        <h4>Travel Advice</h4>
        <p>{travel_suggestion}</p>
    </div>
    """, unsafe_allow_html=True)

st.caption(
    "© 2026 TransitIQ | Smart Traffic Congestion Prediction System | MCA Group B2511"
)
