import streamlit as st
import requests
import pandas as pd

st.title("Live Incidents")

lat = st.session_state.get("lat", 19.0760)
lon = st.session_state.get("lon", 72.8777)

data = requests.get(
    f"http://127.0.0.1:5000/predict?lat={lat}&lon={lon}"
).json()

incidents = data.get("incidents", [])

df = pd.DataFrame(incidents)

if not df.empty:
    st.table(df)
else:
    st.success("No incidents nearby")