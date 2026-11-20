# TransitIQ: Smart Traffic Congestion Prediction

TransitIQ is a Streamlit dashboard with a Flask API. It combines a traffic-volume model trained on the Metro Interstate Traffic Volume dataset with current weather and TomTom traffic services. The project is a prototype: its model is trained on Minnesota data, so its volume predictions are not validated Mumbai vehicle counts.

## Features

- Home dashboard with selected location, weather and traffic estimates.
- Twelve-hour weather-informed traffic forecast.
- Analysis page with recent backend estimates and a clearly labeled reference dataset fallback.
- Route alternatives with TomTom route geometry and sampled live traffic flow.
- Nearby incidents from TomTom Traffic Incidents API, with short-lived cached results when connectivity drops.
- Model training and comparison notebook at `notebooks/TransitIQ_Model_Analysis.ipynb`.

## Setup

Use Python 3.11 or newer. From this folder:

```bash
python -m venv .venv
# Windows PowerShell: .venv\Scripts\Activate.ps1
# macOS/Linux: source .venv/bin/activate
python -m pip install -r requirements.txt
Copy-Item .env.example .env  # PowerShell; on macOS/Linux use: cp .env.example .env
```

Add your TomTom developer key to `.env`:

```text
TOMTOM_API_KEY=your_key_here
```

Never commit `.env`. Without the key, model predictions and reference-data analysis still work with fallback values; live routing and incidents are unavailable.

## Run

Open two terminals in the project folder:

```bash
python api/server.py
```

```bash
streamlit run app.py
```

The Flask health endpoint is `http://127.0.0.1:5000/`. The Streamlit app is shown in the URL printed by Streamlit. If `model/model.pkl` is missing, the backend trains it at startup; install all requirements and keep the dataset at `data/Metro_Interstate_Traffic_Volume.csv`.

## Low connectivity behavior

The API uses bounded request timeouts. Weather is cached in memory for five minutes, and recent incident results are cached for one minute. If a provider is unavailable, prediction uses documented fallback weather and traffic estimates; the UI labels live, cached and unavailable incident data. Forecasting needs a weather response and can be unavailable offline. Map tiles also require a network connection. The app itself and the trained model run locally.

## Model and evaluation

Run `python train_model.py` to clean the reference dataset, prepare features, train Linear Regression, Decision Tree, Random Forest, Gradient Boosting and XGBoost, and save the best model plus comparison artifacts under `model/`. The chronological 80/20 split places later records in the test set. See the notebook for cleaning, exploratory plots, metric comparisons, actual-versus-predicted plots and feature importance.

## Limitations

- TomTom and Open-Meteo availability, plan limits and coverage determine live data.
- Fallback weather and traffic values are estimates; they are not observations.
- The training dataset is geographically different from Mumbai and model validation does not establish Mumbai accuracy.
- Incident and weather caches are in memory and clear when the backend restarts.
- Mobile app integration
- Real-time crowd-sourced traffic data

## Future Enhancements

- Mobile Application:
  Develop an Android application for
  accessing traffic predictions on the go.

- Crowd-Sourced Traffic:
  Collect real-time traffic information
  from users to improve prediction quality.

- Advanced ML Models:
  Experiment with XGBoost, LSTM and
  other time-series prediction models.

- Smart Route Recommendation:
  Recommend alternative routes based on
  predicted congestion and travel time.

- Smart Notifications:
  Send alerts about traffic jams,
  road closures and unexpected incidents.

- Historical Traffic Analysis:
  Store historical traffic data to
  identify congestion patterns.

- Weather-Based Prediction:
  Improve prediction using rainfall,
  visibility and other weather conditions.
