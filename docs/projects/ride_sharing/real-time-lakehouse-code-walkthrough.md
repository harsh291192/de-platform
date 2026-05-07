# Code Walkthrough: Real-Time Lakehouse

This document breaks down the implementation details of the core components in the Ride-Sharing monitoring pipeline.

---

## 1. The High-Velocity Producer (`gps_producer.py`)
Because we are simulating 1,000 concurrent drivers pinging their location multiple times a second, sending plain JSON over the wire is incredibly inefficient.

### Avro Serialization
We implemented the `confluent_kafka` library to serialize the payloads into **Avro**.
```python
avro_schema_str = """
{
  "type": "record",
  "name": "GPSPing",
  ...
}
"""
avro_serializer = AvroSerializer(schema_registry_client, avro_schema_str...)
```
- **Why Avro?** It is a binary format. It strips out all the repetitive keys (like `"driver_id":`, `"latitude":`) and only sends the raw bytes. This can reduce message size by up to 80%.
- **Schema Registry:** Before sending, the producer registers this schema with the Confluent Schema Registry. This guarantees that no downstream consumer (or Snowflake) will ever break due to a missing column or changed data type.

---

## 2. The Sink Connector (`snowflake-sink.json`)
The Snowflake Kafka Connector natively bridges Kafka and Snowflake.

### The Snowpipe Streaming API
```json
"snowflake.ingestion.method": "SNOWPIPE_STREAMING",
```
Older versions of the connector used internal S3 stages and standard Snowpipe to batch load files every minute. The new `SNOWPIPE_STREAMING` method uses Snowflake's streaming API to push rows directly into the database buffer, achieving sub-second latency without any external cloud storage.

### The Magic Byte Fix
```json
"key.converter": "org.apache.kafka.connect.storage.StringConverter",
"value.converter": "io.confluent.connect.avro.AvroConverter"
```
Because our Python producer serializes the *Key* (Driver ID) as a plain UTF-8 string, but the *Value* (The Payload) as an Avro record, we must configure Kafka Connect to read them differently! If we used `AvroConverter` for the Key, it would crash looking for the Confluent "Magic Byte" (a 5-byte header added to all Avro messages).

---

## 3. Data Quality Validation (`gx_suite.py`)
We use **Great Expectations (v1.x)** programmatically to validate the data that landed in Snowflake.

### Building the Suite
```python
suite.add_expectation(
    gx.expectations.ExpectColumnValuesToBeBetween(column="SPEED_MPH", min_value=0.0, max_value=120.0)
)
```
Instead of writing complex SQL `CASE` statements, we define declarative rules (Expectations). This makes the code self-documenting.

### Routing Clean Data
Great Expectations is purely a validation engine—it doesn't physically delete bad rows for you.
In our script, we use GX to generate the Data Quality report (how many teleportations or impossible speeds occurred), and then we execute standard ELT SQL to route the valid data:
```sql
CREATE OR REPLACE TABLE CLEAN_GPS AS
SELECT * FROM VW_RAW_GPS
WHERE DRIVER_ID IS NOT NULL
  AND SPEED_MPH BETWEEN 0.0 AND 120.0
  AND LATITUDE BETWEEN 40.0 AND 42.0 ...
```
This ensures our Streamlit dashboard (`streamlit_app.py`) only queries pristine, trusted data.
