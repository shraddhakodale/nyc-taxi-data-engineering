# NYC Taxi Data Engineering Project

An end-to-end data engineering and analytics project using NYC Taxi data.

## Tech Stack
- Python
- PostgreSQL
- Docker
- Kestra
- Streamlit
- Plotly

## Dashboard Features
- Total trips and average distance
- Average fare and total amount
- Trips by borough
- Top pickup zones
- Trip distance distribution
- Trips by payment type
- Borough summary

## Project Files
- app.py: Streamlit analytics dashboard
- taxi_pipeline.py: Python pipeline
- requirements.txt: Python dependencies

## Run Locally
1. Start PostgreSQL using your configured Docker Compose setup.
2. Install dependencies:

   pip install -r requirements.txt

3. Set the database environment variables, including DB_PASSWORD.
4. Start the dashboard:

   streamlit run app.py

## Security
Do not commit passwords, API keys, environment files, or raw datasets.
