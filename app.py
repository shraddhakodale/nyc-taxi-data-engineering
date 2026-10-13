
import os
from contextlib import closing
from datetime import timedelta

import streamlit as st
import pandas as pd
import plotly.express as px
import psycopg2

# --------------------------------------------------
# 1. PAGE CONFIGURATION
# --------------------------------------------------
st.set_page_config(
    page_title="NYC Taxi Data Engineering  2025",
    page_icon="🚕",
    layout="wide"
)

TABLE = "yellow_taxi_data_2025"

PAYMENT_LABELS = {
    0: "0 - Flex Fare",
    1: "1 - Credit Card",
    2: "2 - Cash",
    3: "3 - No Charge",
    4: "4 - Dispute",
    5: "5 - Unknown",
    6: "6 - Voided Trip",
}

# --------------------------------------------------
# 2. DASHBOARD THEME - CSS
# --------------------------------------------------
st.markdown("""
<style>
/* Main background */
.stApp {
    background-color: #111827;
    color: #F9FAFB;
}

/* Main content spacing */
.block-container {
    padding-top: 2rem;
    padding-bottom: 2rem;
}

/* Sidebar */
[data-testid="stSidebar"] {
    background-color: #1F2937;
    border-right: 1px solid #374151;
}

/* Headings */
h1, h2, h3 {
    color: #06B6D4 !important;
}

/* Paragraph and caption */
p, .stCaption {
    color: #CBD5E1;
}

/* KPI cards */
[data-testid="stMetric"] {
    background-color: #1F2937;
    border: 1px solid #374151;
    padding: 18px;
    border-radius: 12px;
}

/* KPI labels */
[data-testid="stMetricLabel"] {
    color: #CBD5E1 !important;
}

/* KPI values */
[data-testid="stMetricValue"] {
    color: #F59E0B !important;
    font-weight: 700;
}

/* Filter labels */
[data-testid="stWidgetLabel"] p {
    color: #67E8F9 !important;
}

/* Select and multiselect controls */
[data-baseweb="select"] > div {
    background-color: #273449;
    border-color: #475569;
    color: #F9FAFB;
}

/* Date input */
[data-testid="stDateInput"] input {
    background-color: #273449;
    color: #F9FAFB;
    border-color: #475569;
}

/* Dataframe border */
[data-testid="stDataFrame"] {
    border: 1px solid #374151;
    border-radius: 10px;
}

/* Horizontal divider */
hr {
    border-color: #374151;
}

/* Buttons */
.stButton > button {
    background-color: #0891B2;
    color: white;
    border-radius: 8px;
    border: none;
}

/* Success message */
[data-testid="stAlert"] {
    border-radius: 10px;
}
</style>
""", unsafe_allow_html=True)

# --------------------------------------------------
# 3. TITLE
# --------------------------------------------------
st.title("🚕 NYC Taxi Data Engineering Dashboard")
st.caption("Data Engineering Project | PostgreSQL | 2025")

# Chart theme colors
BG_COLOR = "#111827"
PLOT_COLOR = "#1F2937"
TEXT_COLOR = "#F9FAFB"
GRID_COLOR = "#374151"
CYAN = "#06B6D4"
AMBER = "#F59E0B"
GREEN = "#10B981"
PURPLE = "#8B5CF6"

CHART_COLORS = [
    CYAN,
    AMBER,
    GREEN,
    PURPLE,
    "#F472B6",
    "#60A5FA",
    "#A3E635",
    "#FB923C",
]

def style_chart(fig, height=400):
    """Apply the shared dark theme to a Plotly figure."""
    fig.update_layout(
        paper_bgcolor=BG_COLOR,
        plot_bgcolor=PLOT_COLOR,
        font=dict(color=TEXT_COLOR, size=12),
        title_font=dict(color=CYAN, size=18),
        height=height,
        margin=dict(l=20, r=20, t=65, b=35),
        legend=dict(
            bgcolor="rgba(31,41,55,0.5)",
            font=dict(color=TEXT_COLOR)
        )
    )

    fig.update_xaxes(
        gridcolor=GRID_COLOR,
        linecolor=GRID_COLOR,
        tickfont=dict(color=TEXT_COLOR),
        title_font=dict(color=TEXT_COLOR)
    )

    fig.update_yaxes(
        gridcolor=GRID_COLOR,
        linecolor=GRID_COLOR,
        tickfont=dict(color=TEXT_COLOR),
        title_font=dict(color=TEXT_COLOR)
    )

    return fig

# --------------------------------------------------
# 4. DATABASE CONNECTION
# --------------------------------------------------
def get_connection():
    return psycopg2.connect(
        host=os.getenv("DB_HOST", "localhost"),
        port=int(os.getenv("DB_PORT", "5432")),
        dbname=os.getenv("DB_NAME", "ny_taxi"),
        user=os.getenv("DB_USER", "root"),
        password=os.getenv("DB_PASSWORD", "root")
    )


def run_query(sql, params=()):
    with closing(get_connection()) as conn:
        return pd.read_sql_query(sql, conn, params=params)

# --------------------------------------------------
# 5. FILTER OPTIONS
# --------------------------------------------------
@st.cache_data(ttl=300)
def get_date_bounds():
    result = run_query(f"""
        SELECT MIN(tpep_pickup_datetime)::date AS min_date,
               MAX(tpep_pickup_datetime)::date AS max_date
        FROM {TABLE}
        WHERE tpep_pickup_datetime IS NOT NULL
    """)

    return result.iloc[0]["min_date"], result.iloc[0]["max_date"]


@st.cache_data(ttl=300)
def get_borough_options():
    result = run_query("""
        SELECT DISTINCT "Borough" AS borough
        FROM taxi_zone_lookup
        WHERE "Borough" IS NOT NULL
        ORDER BY "Borough"
    """)

    return result["borough"].tolist()

# --------------------------------------------------
# 6. BUILD SQL FILTERS
# --------------------------------------------------
def make_filters(start_date, end_date, boroughs, payment_types):
    conditions = [
        "t.tpep_pickup_datetime >= %s",
        "t.tpep_pickup_datetime < %s"
    ]

    params = [
        start_date,
        end_date + timedelta(days=1)
    ]

    if boroughs:
        conditions.append("""
            t.pulocationid IN (
                SELECT "LocationID"
                FROM taxi_zone_lookup
                WHERE "Borough" = ANY(%s)
            )
        """)
        params.append(list(boroughs))

    if payment_types:
        conditions.append("t.payment_type = ANY(%s)")
        params.append(list(payment_types))

    return " AND ".join(conditions), tuple(params)

# --------------------------------------------------
# 7. LOAD FILTERED DATA
# --------------------------------------------------
@st.cache_data(ttl=60)
def load_data(start_date, end_date, boroughs, payment_types):
    where_sql, params = make_filters(
        start_date, end_date, boroughs, payment_types
    )

    # KPI metrics
    kpi = run_query(f"""
        SELECT COUNT(*) AS total_trips,
               ROUND(AVG(t.trip_distance)::numeric, 2) AS avg_distance,
               ROUND(AVG(t.fare_amount)::numeric, 2) AS avg_fare,
               ROUND(AVG(t.total_amount)::numeric, 2) AS avg_total
        FROM {TABLE} t
        WHERE {where_sql}
    """, params)

    # Trips by borough
    borough = run_query(f"""
        SELECT COALESCE(z."Borough", 'Unknown') AS borough,
               COUNT(*) AS trips
        FROM {TABLE} t
        LEFT JOIN taxi_zone_lookup z
          ON t.pulocationid = z."LocationID"
        WHERE {where_sql}
        GROUP BY 1
        ORDER BY trips DESC
    """, params)

    # Top 10 pickup zones
    zones = run_query(f"""
        SELECT COALESCE(z."Zone", 'Unknown') AS zone,
               COUNT(*) AS trips
        FROM {TABLE} t
        LEFT JOIN taxi_zone_lookup z
          ON t.pulocationid = z."LocationID"
        WHERE {where_sql}
        GROUP BY 1
        ORDER BY trips DESC
        LIMIT 10
    """, params)

    # Trip distance groups
    distance = run_query(f"""
        SELECT CASE
                 WHEN t.trip_distance < 1 THEN 'Under 1 mi'
                 WHEN t.trip_distance < 3 THEN '1–3 mi'
                 WHEN t.trip_distance < 5 THEN '3–5 mi'
                 WHEN t.trip_distance < 10 THEN '5–10 mi'
                 ELSE '10+ mi'
               END AS distance_range,
               COUNT(*) AS trips
        FROM {TABLE} t
        WHERE {where_sql}
          AND t.trip_distance IS NOT NULL
          AND t.trip_distance >= 0
        GROUP BY 1
        ORDER BY MIN(
            CASE
                WHEN t.trip_distance < 1 THEN 1
                WHEN t.trip_distance < 3 THEN 2
                WHEN t.trip_distance < 5 THEN 3
                WHEN t.trip_distance < 10 THEN 4
                ELSE 5
            END
        )
    """, params)

    # Payment type distribution
    payment = run_query(f"""
        SELECT COALESCE(t.payment_type::text, 'Unknown') AS payment_type,
               COUNT(*) AS trips
        FROM {TABLE} t
        WHERE {where_sql}
        GROUP BY 1
        ORDER BY trips DESC
    """, params)

    return kpi, borough, zones, distance, payment

# --------------------------------------------------
# 8. SIDEBAR FILTERS
# --------------------------------------------------
try:
    min_date, max_date = get_date_bounds()

    if pd.isna(min_date) or pd.isna(max_date):
        st.warning("No pickup dates were found in the database.")
        st.stop()

    st.sidebar.header("🔎 Dashboard Filters")

    selected_dates = st.sidebar.date_input(
        "Pickup Date Range",
        value=(min_date, max_date),
        min_value=min_date,
        max_value=max_date,
        help="Select the start date and end date."
    )

    borough_options = get_borough_options()

    selected_boroughs = st.sidebar.multiselect(
        "Pickup Borough",
        options=borough_options,
        default=[],
        help="Leave empty to include all boroughs."
    )

    available_payment_codes = sorted(PAYMENT_LABELS.keys())

    selected_payment_labels = st.sidebar.multiselect(
        "Payment Type",
        options=[PAYMENT_LABELS[c] for c in available_payment_codes],
        default=[PAYMENT_LABELS[c] for c in [0, 1, 2, 3, 4, 5]],
        help="Clear the selection to include all payment types."
    )

    selected_payment_types = tuple(
        code for code in available_payment_codes
        if PAYMENT_LABELS[code] in selected_payment_labels
    )

    st.sidebar.caption(
        "Borough is based on pickup location. "
        "Changing filters updates all dashboard results."
    )

    if not isinstance(selected_dates, (tuple, list)) or len(selected_dates) != 2:
        st.info("Please select both a start date and an end date.")
        st.stop()

    start_date, end_date = selected_dates

    if start_date > end_date:
        st.error("Start date must be before or equal to end date.")
        st.stop()

    # Load data using current filter selections
    kpi, borough, zones, distance, payment = load_data(
        start_date,
        end_date,
        tuple(selected_boroughs),
        selected_payment_types
    )

    a = kpi.iloc[0]

    # --------------------------------------------------
    # 9. KPI CARDS
    # --------------------------------------------------
    st.subheader("📊 Key Performance Indicators")

    c1, c2, c3, c4 = st.columns(4)

    c1.metric(
        "🚕 Total Trips",
        f"{int(a['total_trips']):,}"
    )

    c2.metric(
        "📍 Avg Distance",
        "N/A" if pd.isna(a["avg_distance"])
        else f"{a['avg_distance']} mi"
    )

    c3.metric(
        "💵 Average Fare",
        "N/A" if pd.isna(a["avg_fare"])
        else f"${a['avg_fare']}"
    )

    c4.metric(
        "💳 Average Total",
        "N/A" if pd.isna(a["avg_total"])
        else f"${a['avg_total']}"
    )

    st.divider()

    # --------------------------------------------------
    # 10. CHART 1 AND CHART 2
    # --------------------------------------------------
    left, right = st.columns(2)

    with left:
        st.subheader("🏙️ Trips by Borough")

        if not borough.empty:
            fig = px.bar(
                borough,
                x="borough",
                y="trips",
                color="borough",
                title="Number of Trips by Borough",
                color_discrete_sequence=CHART_COLORS,
                labels={
                    "borough": "Pickup Borough",
                    "trips": "Number of Trips"
                }
            )

            fig.update_layout(showlegend=False)
            fig.update_traces(
                marker_line_color=BG_COLOR,
                marker_line_width=1
            )

            st.plotly_chart(
                style_chart(fig),
                width="stretch"
            )
        else:
            st.info("No borough data for the selected filters.")

    with right:
        st.subheader("📌 Top 10 Pickup Zones")

        if not zones.empty:
            fig = px.bar(
                zones.sort_values("trips"),
                x="trips",
                y="zone",
                orientation="h",
                title="Most Popular Pickup Zones",
                color="trips",
                color_continuous_scale=["#164E63", CYAN, AMBER],
                labels={
                    "zone": "Pickup Zone",
                    "trips": "Number of Trips"
                }
            )

            fig.update_coloraxes(colorbar_title="Trips")

            st.plotly_chart(
                style_chart(fig),
                width="stretch"
            )
        else:
            st.info("No pickup-zone data for the selected filters.")

    # --------------------------------------------------
    # 11. CHART 3 AND CHART 4
    # --------------------------------------------------
    left, right = st.columns(2)

    with left:
        st.subheader("🛣️ Trip Distance Distribution")

        if not distance.empty:
            fig = px.pie(
                distance,
                names="distance_range",
                values="trips",
                title="Trips by Distance Range",
                hole=0.45,
                color_discrete_sequence=CHART_COLORS
            )

            fig.update_traces(
                textposition="inside",
                textinfo="percent+label",
                marker=dict(
                    line=dict(color=BG_COLOR, width=2)
                )
            )

            st.plotly_chart(
                style_chart(fig),
                width="stretch"
            )
        else:
            st.info("No distance data for the selected filters.")

    with right:
        st.subheader("💳 Trips by Payment Type")

        if not payment.empty:
            def payment_label(value):
                text_value = str(value)

                if text_value.isdigit():
                    code = int(text_value)
                    return PAYMENT_LABELS.get(
                        code, f"{code} - Other/Unknown"
                    )

                return text_value

            payment["payment_label"] = payment["payment_type"].apply(
                payment_label
            )

            fig = px.bar(
                payment,
                x="payment_label",
                y="trips",
                color="payment_label",
                title="Payment Type Distribution",
                color_discrete_sequence=CHART_COLORS,
                labels={
                    "payment_label": "Payment Type",
                    "trips": "Number of Trips"
                }
            )

            fig.update_layout(showlegend=False)
            fig.update_traces(
                marker_line_color=BG_COLOR,
                marker_line_width=1
            )

            st.plotly_chart(
                style_chart(fig),
                width="stretch"
            )
        else:
            st.info("No payment data for the selected filters.")

    # --------------------------------------------------
    # 12. BOROUGH SUMMARY
    # --------------------------------------------------
    st.subheader("📋 Borough Summary")

    st.dataframe(
        borough,
        width="stretch",
        hide_index=True
    )

    st.caption(
        f"Selected pickup dates: {start_date} to {end_date} | "
        f"Selected boroughs: "
        f"{len(selected_boroughs) if selected_boroughs else 'All'} | "
        f"Selected payment types: "
        f"{len(selected_payment_types) if selected_payment_types else 'All'}"
    )

    if int(a["total_trips"]) == 0:
        st.warning("No trips match the selected filters.")
    else:
        st.success("Dashboard loaded successfully from PostgreSQL.")

except Exception as e:
    st.error("Dashboard could not load data.")
    st.exception(e)
