import streamlit as st

st.set_page_config(page_title="TransitIQ - Traffic Dashboard", layout="wide")

home = st.Page("pages/home.py", title="Home", icon="")
analysis = st.Page("pages/analysis.py", title="Analysis")
routes = st.Page("pages/routes.py", title="Routes")
incidents = st.Page("pages/incidents.py", title="Incidents")
about = st.Page("pages/about.py", title="About")
forecast = st.Page("pages/forecast.py", title="Forecast")

pg = st.navigation({
    "Menu": [home, analysis, routes, forecast, incidents, about]
})

pg.run()

st.markdown("""
<style>
.footer {
    position: fixed;
    bottom: 0;
    width: 100%;
    text-align: center;
    color: gray;
    padding: 10px;
}
</style>

<div class="footer">
© 2025 TransitIQ - Traffic Dashboard by MCA Group B2511
</div>
""", unsafe_allow_html=True)