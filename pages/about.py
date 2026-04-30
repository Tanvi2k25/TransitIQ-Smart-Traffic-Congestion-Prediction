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
<div class="about-subtitle">A location-aware traffic intelligence dashboard powered by weather-informed machine learning and live area data.</div>
""", unsafe_allow_html=True)

st.markdown("""
<div class="about-card">
    <h3>Project Overview</h3>
    <ul>
        <li>Predicts traffic volume and congestion for the selected location using a trained ML model.</li>
        <li>Uses weather features such as temperature, humidity, rain, cloud cover, wind, visibility, and more.</li>
        <li>Links the forecast to the location chosen on the Home page so users see area-specific results.</li>
        <li>Combines weather-driven prediction with local traffic flow data from TomTom to improve realism.</li>
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
        <li><strong>Incidents:</strong> Simulated live incident map and incident summary based on the current location.</li>
        <li><strong>Routes:</strong> Route exploration with weather-aware traffic prediction for source/destination navigation.</li>
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
        <li>Improved incident page layout, marker styling, and auto-refresh behavior.</li>
        <li>Added backend support for forecast and incidents so the app works end-to-end.</li>
    </ul>
</div>
""", unsafe_allow_html=True)
