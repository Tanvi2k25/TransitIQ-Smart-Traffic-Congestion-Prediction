import streamlit as st

st.markdown("""
<style>
.about-title {
    font-size: 32px;
    font-weight: 700;
    margin-bottom: 16px;
}
.about-subtitle {
    font-size: 16px;
    margin-bottom: 24px;
}
.about-card {
    background: linear-gradient(135deg, #0b1120, #111827);
    border: 1px solid rgba(148, 163, 184, 0.18);
    border-radius: 20px;
    padding: 24px;
    box-shadow: 0 16px 40px rgba(15, 23, 42, 0.30);
    color: #e2e8f0;
    margin-bottom: 20px;
}
.about-card h3 {
    margin-top: 0;
    margin-bottom: 12px;
    font-size: 18px;
    color: #f8fafc;
}
.about-card ul {
    margin: 0;
    padding-left: 18px;
}
.about-card li {
    margin-bottom: 10px;
    line-height: 1.7;
}
</style>
<div class="about-title">About the Mumbai Traffic Forecast Project</div>
<div class="about-subtitle">Live Mumbai traffic context alongside a Minnesota-trained traffic-volume model.</div>
""", unsafe_allow_html=True)

st.markdown("""
<div class="about-card">
    <h3>Project Overview</h3>
    <ul>
        <li>Provides a traffic dashboard for a selected Mumbai location using live weather, traffic-flow, and incident data when available.</li>
        <li>Includes a reference traffic-volume regression model trained on the Minnesota Metro Interstate dataset.</li>
        <li>Uses the selected Mumbai coordinates to request local weather and TomTom information.</li>
        <li>Shows live TomTom flow and incidents separately from the Minnesota-trained model estimate.</li>
    </ul>
</div>
""", unsafe_allow_html=True)

st.markdown("""
<div class="about-card">
    <h3>Data Scope and Model Limitations</h3>
    <ul>
        <li>The supervised traffic-volume model is trained on Minnesota data, not measured Mumbai vehicle counts.</li>
        <li>Its evaluation scores describe the Minnesota holdout dataset and should not be presented as Mumbai accuracy.</li>
        <li>Selected-location weather is passed to the model, but it does not replace Mumbai traffic training data or validate Mumbai accuracy.</li>
    </ul>
</div>
""", unsafe_allow_html=True)

st.markdown("""
<div class="about-card">
    <h3>Key Pages</h3>
    <ul>
        <li><strong>Home:</strong> Search and select a Mumbai neighborhood, then sync the location across the app.</li>
        <li><strong>Analysis:</strong> Summary cards and trend insights for current traffic and weather at the chosen area.</li>
        <li><strong>Forecast:</strong> Hourly weather and traffic volume forecast cards for the next 9 hours.</li>
        <li><strong>Incidents:</strong> TomTom incident map and live incident summary when API access is available.</li>
        <li><strong>Routes:</strong> Route exploration with sampled TomTom traffic flow for source/destination alternatives.</li>
    </ul>
</div>
""", unsafe_allow_html=True)

st.markdown("""
<div class="about-card">
    <h3>Backend & Data Flow</h3>
    <ul>
        <li>Flask API provides endpoints for <code>/predict</code>, <code>/forecast</code>, <code>/history</code>, <code>/routes</code>, and <code>/incidents</code>.</li>
        <li>Open-Meteo supplies hourly weather data for the selected coordinates.</li>
        <li>TomTom traffic APIs provide flow segment data and routing support.</li>
        <li>ML model uses combined time and weather features to estimate traffic volume.</li>
    </ul>
</div>
""", unsafe_allow_html=True)

st.markdown("""
<div class="about-card">
    <h3>Why Weather Matters</h3>
    <ul>
        <li>Weather affects driver behavior, visibility, and road capacity.</li>
        <li>Rain, wind, humidity, and cloudiness can increase congestion and slow traffic.</li>
        <li>The forecast page explains how these factors are used in the prediction pipeline.</li>
        <li>Location-specific values are shown by using the coordinates selected on the Home page.</li>
    </ul>
</div>
""", unsafe_allow_html=True)

st.markdown("""
<div class="about-card">
    <h3>What Was Improved</h3>
    <ul>
        <li>Cleaned up UI for cards, spacing, and forecast readability.</li>
        <li>Ensured the forecast page updates with the selected home location.</li>
        <li>Improved incident page layout, marker styling, and cached live incident handling.</li>
        <li>Added backend support for forecast and incidents so the app works end-to-end.</li>
    </ul>
</div>
""", unsafe_allow_html=True)
