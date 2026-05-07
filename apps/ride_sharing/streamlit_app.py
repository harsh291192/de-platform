import os

import pandas as pd
import snowflake.connector
import streamlit as st
from dotenv import load_dotenv

# Set wide layout
st.set_page_config(
    page_title="Ride-Sharing Real-Time Dashboard", layout="wide", page_icon="🚕"
)

st.title("🚕 Real-Time Lakehouse: Ride-Sharing Monitor")
st.markdown(
    "Sub-second GPS telemetry delivered via **Kafka → Snowpipe Streaming**. "
    "Bad pings filtered via **Great Expectations**."
)

# Load Environment Variables
load_dotenv()


# Connect to Snowflake
@st.cache_resource
def init_connection():
    return snowflake.connector.connect(
        user=os.getenv("SNOWFLAKE_USER"),
        password=os.getenv("SNOWFLAKE_PASSWORD"),
        account=os.getenv("SNOWFLAKE_ACCOUNT"),
        warehouse=os.getenv("SNOWFLAKE_WAREHOUSE"),
        database=os.getenv("SNOWFLAKE_DATABASE"),
        schema="RAW",
        role=os.getenv("SNOWFLAKE_ROLE"),
    )


try:
    conn = init_connection()
except Exception as e:
    st.error(f"Failed to connect to Snowflake: {e}")
    st.stop()

# Auto-refresh button (Streamlit native way is a simple button for manual)
col1, col2, col3 = st.columns(3)
with col1:
    if st.button("🔄 Refresh Data"):
        st.rerun()

st.markdown("---")


# Query Data
@st.cache_data(ttl=5)  # Cache for 5 seconds to simulate real-time
def load_data():
    # 1. Total Raw Pings
    raw_df = pd.read_sql("SELECT COUNT(*) AS total FROM VW_RAW_GPS", conn)
    total_pings = int(raw_df.iloc[0]["TOTAL"])

    # 2. Total Clean Pings
    clean_df = pd.read_sql("SELECT COUNT(*) AS total FROM CLEAN_GPS", conn)
    total_clean = int(clean_df.iloc[0]["TOTAL"])

    # 3. Get the latest 500 clean pings for the map
    map_query = """
    SELECT LATITUDE as "lat", LONGITUDE as "lon", SPEED_MPH, DRIVER_ID
    FROM CLEAN_GPS
    ORDER BY PING_TIMESTAMP DESC
    LIMIT 500
    """
    map_df = pd.read_sql(map_query, conn)

    return total_pings, total_clean, map_df


try:
    with st.spinner("Fetching latest telemetry..."):
        total_pings, total_clean, map_df = load_data()
except Exception as e:
    st.error(f"Error querying Snowflake: {e}")
    st.stop()

anomalies_caught = total_pings - total_clean

# Key Metrics
m1, m2, m3 = st.columns(3)
m1.metric("Total Raw Pings Ingested", f"{total_pings:,}")
m2.metric(
    "Great Expectations Anomalies Caught",
    f"{anomalies_caught:,}",
    (
        f"{(anomalies_caught/total_pings)*100:.1f}% Error Rate"
        if total_pings > 0
        else "0%"
    ),
    delta_color="inverse",
)
m3.metric("Clean GPS Pings Served", f"{total_clean:,}")

st.markdown("---")

# Map Visualization
st.subheader("📍 Live Fleet Tracker (Latest 500 Clean Pings)")
if not map_df.empty:
    st.map(map_df, zoom=10, use_container_width=True)
else:
    st.info("No clean GPS data available for the map yet.")

# Data Table
st.subheader("📊 Recent High-Speed Alerts (>60 MPH)")
high_speed_df = map_df[map_df["SPEED_MPH"] > 60].sort_values(
    by="SPEED_MPH", ascending=False
)
if not high_speed_df.empty:
    st.dataframe(high_speed_df.head(10), use_container_width=True)
else:
    st.success("All drivers obeying speed limits!")
