-- ==========================================
-- Project 3: Real-Time Ride Sharing
-- Snowflake Setup Script
-- ==========================================

-- 1. Set the context using the same environment from the previous project
USE ROLE SENTIMENT_APP_ROLE;
USE WAREHOUSE STREAMING_WH;
USE DATABASE SOCIAL_MEDIA_DB;
USE SCHEMA RAW;

-- 2. Create the RAW_GPS table
-- Note: The Snowflake Kafka Connector automatically dumps the incoming Avro records
-- into a VARIANT column named RECORD_CONTENT, and Kafka metadata into RECORD_METADATA.
-- We pre-create it here to ensure it exists with the correct permissions.
CREATE OR REPLACE TABLE RAW_GPS (
    RECORD_METADATA VARIANT,
    RECORD_CONTENT VARIANT
);

-- 3. (Optional but recommended) Create a View to flatten the Avro data
-- This makes the RAW data instantly queryable like a normal relational table!
CREATE OR REPLACE VIEW VW_RAW_GPS AS
SELECT
    RECORD_CONTENT:driver_id::INT AS driver_id,
    RECORD_CONTENT:latitude::FLOAT AS latitude,
    RECORD_CONTENT:longitude::FLOAT AS longitude,
    RECORD_CONTENT:speed_mph::FLOAT AS speed_mph,
    RECORD_CONTENT:timestamp::TIMESTAMP AS ping_timestamp,
    RECORD_METADATA:CreateTime::TIMESTAMP AS kafka_ingest_time
FROM RAW_GPS;
