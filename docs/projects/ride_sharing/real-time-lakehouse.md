# Project 3: Real-Time Lakehouse (Ride-Sharing Monitor)

## Overview & Business Value
This project demonstrates an enterprise-grade, ultra-low latency streaming pipeline.

The goal is to monitor 1,000 ride-sharing drivers across a city in real-time. Because GPS telemetry is high-velocity (sub-second pings), we must use efficient serialization and direct-to-warehouse streaming. Additionally, because IoT sensors can glitch (e.g., impossible speeds or teleportation), we implemented a rigorous Data Quality layer to catch anomalies before they reach the final dashboard.

## Architectural Flow
The pipeline follows a direct `Streaming -> Lakehouse` pattern, completely bypassing traditional batch layers like S3:

1. **Generation (`gps_producer.py`)**: A Python producer simulates 1,000 drivers and intentionally injects bad data (e.g., negative speeds, jumping across the ocean).
2. **Serialization (Avro & Schema Registry)**: To save bandwidth and enforce strict typing, the raw JSON is compressed into binary `Avro` format using the Confluent Schema Registry.
3. **Ingestion (Kafka Connect)**: A dedicated Kafka Connect worker listens to the topic.
4. **Sub-Second Streaming (Snowflake Sink Connector)**: Using Snowflake's Snowpipe Streaming API, the connector pushes the Avro packets directly into the `RAW_GPS` table in Snowflake with sub-second latency.
5. **Data Quality (`gx_suite.py`)**: **Great Expectations (v1.x)** evaluates the `RAW_GPS` table, catches the anomalies, and routes the valid records into the final `CLEAN_GPS` table via SQL.
6. **Visualization (`streamlit_app.py`)**: A Streamlit dashboard visualizes the live fleet and error rates.

## Step-by-Step Execution Guide

### Step 1: Start the Infrastructure
Ensure Docker is running and boot up the entire data platform (Kafka, Schema Registry, Kafka Connect, etc.).
```bash
docker compose up -d
```
*Note: Kafka Connect will automatically download the official Snowflake Kafka Plugin during the build.*

### Step 2: Prepare Snowflake
Execute the `scripts/snowflake/setup_ride_sharing.sql` script in your Snowflake Worksheet to create the `RAW_GPS` table and the `VW_RAW_GPS` flattened view.

### Step 3: Deploy the Sink Connector
Deploy the JSON configuration to the Kafka Connect REST API:
```bash
curl -s -X POST -H "Content-Type: application/json" --data @infrastructure/docker/connectors/snowflake-sink.json http://localhost:8083/connectors
```

### Step 4: Start the Producer
Activate your virtual environment and start generating the sub-second GPS telemetry.
```bash
source .venv/bin/activate
python ingestion/streaming/ride_sharing/gps_producer.py
```
*Let this run in the background. You can query `SELECT * FROM VW_RAW_GPS` in Snowflake to watch the data arrive instantly!*

### Step 5: Run Data Quality Checks
Evaluate the tens of thousands of rows using Great Expectations.
```bash
python data_quality/ride_sharing/gx_suite.py
```
This will print a report of the anomalies caught and create the final `CLEAN_GPS` table.

### Step 6: Launch the Dashboard
Finally, visualize the clean data and error metrics on a real-time dashboard.
```bash
streamlit run apps/ride_sharing/streamlit_app.py
```
