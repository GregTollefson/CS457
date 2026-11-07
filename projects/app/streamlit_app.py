
from datetime import date

import plotly.express as px
import streamlit as st

from db import METRICS, METRIC_UNITS, get_observations

st.set_page_config(
    page_title="FRED Energy Research",
    layout="wide",
)

st.title("FRED Energy Research Database")
st.caption("CS457 — PostgreSQL / Python / Streamlit")

# User controls
metric_name = st.selectbox("Select metric", list(METRICS))
metric = METRICS[metric_name]

date_range = st.date_input(
    "Date range",
    value=(date(2002, 1, 1), date.today()),
)

if len(date_range) != 2:
    st.info("Select a start and end date.")
    st.stop()

start_date, end_date = date_range

if start_date > end_date:
    st.error("Start date must be before end date.")
    st.stop()

# Retrieve observations through the Python database layer.
try:
    df = get_observations(metric, start_date, end_date)
except Exception:
    st.error("Database query failed. Check the PostgreSQL connection and view.")
    st.stop()

if df.empty:
    st.warning("No observations found for this date range.")
    st.stop()

# Chart
st.subheader(metric_name)

chart_data = df.dropna(subset=["value"])

if not chart_data.empty:
    fig = px.line(
        chart_data,
        x="date",
        y="value",
        title=f"{metric_name} over time",
        markers=False,
    )

    fig.update_layout(
        xaxis_title="Date",
        yaxis_title=METRIC_UNITS[metric_name],
        hovermode="x unified",
    )

    st.plotly_chart(fig, width="stretch")
else:
    st.info("No numeric observations available for this selection.")

# Data table
st.subheader("Query Results")
st.dataframe(df, width="stretch", hide_index=True)

st.caption(f"{len(df):,} database rows returned")
