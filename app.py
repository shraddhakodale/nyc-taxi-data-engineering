
import streamlit as st
import pandas as pd
import plotly.express as px
import psycopg2

st.set_page_config(
    page_title="NYC Taxi Analytics",
    page_icon="🚕",
    layout="wide"
)

st.title("🚕 NYC Taxi Data Analytics Dashboard")
st.caption("Data Engineering Project | Kestra + PostgreSQL | January 2021")


@st.cache_resource
def get_connection():
    import os
    return psycopg2.connect(
        host=os.getenv("DB_HOST", "localhost"),
        port=int(os.getenv("DB_PORT", "5432")),
        dbname=os.getenv("DB_NAME", "ny_taxi"),
        user=os.getenv("DB_USER", "root"),
        password=os.environ["DB_PASSWORD"]
    )

@st.cache_data(ttl=60)
def load_data():
    conn = get_connection()

    kpi = pd.read_sql_query("""
        SELECT
            COUNT(*) AS total_trips,
            ROUND(AVG(trip_distance::numeric), 2) AS avg_distance,
            ROUND(AVG(fare_amount::numeric), 2) AS avg_fare,
            ROUND(AVG(total_amount::numeric), 2) AS avg_total
        FROM yellow_taxi_kestra_2021_01
    """, conn)

    borough = pd.read_sql_query("""
        SELECT
            COALESCE(z."Borough", 'Unknown') AS borough,
            COUNT(*) AS trips
        FROM yellow_taxi_kestra_2021_01 t
        JOIN taxi_zone_lookup z
          ON t.pulocationid::integer = z."LocationID"
        GROUP BY 1
        ORDER BY trips DESC
    """, conn)

    zones = pd.read_sql_query("""
        SELECT
            COALESCE(z."Zone", 'Unknown') AS zone,
            COUNT(*) AS trips
        FROM yellow_taxi_kestra_2021_01 t
        JOIN taxi_zone_lookup z
          ON t.pulocationid::integer = z."LocationID"
        GROUP BY 1
        ORDER BY trips DESC
        LIMIT 10
    """, conn)

    distance = pd.read_sql_query("""
        SELECT
            CASE
                WHEN trip_distance::numeric < 1 THEN 'Under 1 mi'
                WHEN trip_distance::numeric < 3 THEN '1–3 mi'
                WHEN trip_distance::numeric < 5 THEN '3–5 mi'
                WHEN trip_distance::numeric < 10 THEN '5–10 mi'
                ELSE '10+ mi'
            END AS distance_range,
            COUNT(*) AS trips
        FROM yellow_taxi_kestra_2021_01
        WHERE trip_distance IS NOT NULL
          AND trip_distance::numeric >= 0
        GROUP BY 1
        ORDER BY MIN(trip_distance::numeric)
    """, conn)

    payment = pd.read_sql_query("""
        SELECT
            COALESCE(payment_type::text, 'Unknown') AS payment_type,
            COUNT(*) AS trips
        FROM yellow_taxi_kestra_2021_01
        GROUP BY 1
        ORDER BY trips DESC
    """, conn)

    return kpi, borough, zones, distance, payment

try:
    kpi, borough, zones, distance, payment = load_data()

    a = kpi.iloc[0]

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total Trips", f"{int(a['total_trips']):,}")
    c2.metric("Avg Distance", f"{a['avg_distance']} mi")
    c3.metric("Average Fare", f"${a['avg_fare']}")
    c4.metric("Average Total", f"${a['avg_total']}")

    st.divider()

    left, right = st.columns(2)

    with left:
        st.subheader("Trips by Borough")
        fig = px.bar(
            borough,
            x="borough",
            y="trips",
            color="borough",
            title="Number of Trips in Each Borough"
        )
        fig.update_layout(showlegend=False)
        st.plotly_chart(fig, use_container_width=True)

    with right:
        st.subheader("Top 10 Pickup Zones")
        fig = px.bar(
            zones.sort_values("trips"),
            x="trips",
            y="zone",
            orientation="h",
            title="Most Popular Pickup Locations"
        )
        st.plotly_chart(fig, use_container_width=True)

    left, right = st.columns(2)

    with left:
        st.subheader("Trip Distance Distribution")
        fig = px.pie(
            distance,
            names="distance_range",
            values="trips",
            title="Trips by Distance Range",
            hole=0.35
        )
        st.plotly_chart(fig, use_container_width=True)

    with right:
        st.subheader("Trips by Payment Type")
        fig = px.bar(
            payment,
            x="payment_type",
            y="trips",
            color="payment_type",
            title="Payment Type Distribution"
        )
        fig.update_layout(showlegend=False)
        st.plotly_chart(fig, use_container_width=True)

    st.subheader("Borough Summary")
    st.dataframe(borough, use_container_width=True)

    st.success("Dashboard loaded successfully from PostgreSQL.")

except Exception as e:
    st.error("Dashboard could not load data. Check PostgreSQL and table names.")
    st.code(str(e))
