🚦 TransitIQ: Smart Traffic Congestion Prediction System

📌 Overview

TransitIQ is a real-time traffic congestion prediction system that combines machine learning, weather data, and live traffic APIs to estimate traffic conditions across Mumbai. The system provides users with interactive maps, traffic insights, weather conditions, and future predictions.

🎯 Objectives
- Predict traffic congestion using ML models
- Integrate real-time weather data
- Visualize traffic conditions on maps
- Provide route-based traffic insights
- Display live incidents and congestion levels

⚙️ Tech Stack
Frontend
- Streamlit
- Folium (Maps)
- Plotly (Visualization)
Backend
- Flask API
- Machine Learning
- Random Forest Regressor (Scikit-learn)
APIs Used
- Open-Meteo (Weather Data)
- TomTom API (Traffic & Incidents)
- OSRM API (Routing)

🧠 Features
🏠 Home Dashboard
- Live traffic prediction (Low / Medium / High)
- Weather details (Temperature, Humidity, Wind, UV Index)
- Interactive map (location selection)
- Traffic volume estimation

📊 Analysis Page
- Real-time prediction vs actual graph
- Traffic trend visualization
- Model performance (R² score)
- Traffic intensity gauge

🛣 Routes Page
- Route visualization between locations
- Traffic-based route coloring
- Nearby route insights

🚨 Incidents Page
- Real-time traffic incidents
- Delay and severity information

🔍 How It Works
1. User selects a location (map or search)
2. Backend fetches:
    - Weather data (Open-Meteo)
    - Traffic data (TomTom)
3. Features are generated (time + weather)
4. ML model predicts traffic volume
5. Result is displayed on dashboard

📊 Machine Learning Model
- Algorithm: Random Forest Regressor
- Dataset: Metro Interstate Traffic Volume Dataset + Weather Data
- Features:
  - Hour, Day, Month
  - Temperature, Humidity, Wind
  - Cloud Cover, Rain
- Output:
  - Traffic Volume
  - Congestion Level (Low / Medium / High)

🚀 Installation & Setup
1️⃣ Clone the repository
```bash
git clone https://github.com/Tanvi2k25/TransitIQ-Smart-Traffic-Congestion-Prediction.git
cd project
```
2️⃣ Install dependencies
```bash
pip install -r requirements.txt
```
3️⃣ Run Backend (Flask)
```bash
cd api
python server.py
```
4️⃣ Run Frontend (Streamlit)
```bash
cd ..
streamlit run app.py
```
📍 Usage
- Search or select a location on the map
- View real-time traffic and weather
- Analyze trends in the analysis page
- Check routes and incidents

⚠️ Limitations
- Real-time traffic depends on API availability
- Weather API has limited free data fields
- Model trained on non-Mumbai dataset (adapted)


Mobile app integration
Real-time crowd-sourced traffic data
