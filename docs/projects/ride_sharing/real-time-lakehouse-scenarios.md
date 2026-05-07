# Interview & Troubleshooting Scenarios: Real-Time Lakehouse

This document covers high-level architectural decisions and real-world troubleshooting scenarios encountered while building the Ride-Sharing streaming pipeline. Use this to prepare for Senior Data Engineering interviews.

---

## Scenario 1: The "Magic Byte" Serialization Error
**Q: You deploy a Kafka Sink Connector and it instantly fails with `SerializationException: Unknown magic byte!`. What caused this and how do you fix it?**

**Answer:**
This happens when there is a mismatch between how the Producer serialized the data and how Kafka Connect is trying to deserialize it.
Specifically, the Confluent Schema Registry prepends a 5-byte "Magic Byte" header to all Avro records (it contains the schema ID). If the producer sends a plain UTF-8 string (like a driver ID for the message Key), but the Sink Connector is configured with `"key.converter": "io.confluent.connect.avro.AvroConverter"`, the connector will read the plain string, fail to find the magic byte, and crash.
**The Fix:** Change the connector configuration to use `StringConverter` for the key, and `AvroConverter` for the value.

---

## Scenario 2: Historical Backfilling via Offset Rewinding
**Q: You have a Kafka topic with 100,000 messages. You deployed a Snowflake Sink Connector and it processed them. You accidentally truncate the Snowflake table and lose the data. The producer is still running. How do you get those 100,000 old messages back into Snowflake?**

**Answer:**
Kafka Connect tracks what it has read using "Offsets" (bookmarks) tied to its Consumer Group ID. Truncating the Snowflake table does not rewind this bookmark, so it won't re-read old messages.
To force a backfill, the simplest method is to **rename the connector** (e.g., from `snowflake-sink` to `snowflake-sink-v2`). This forces Kafka Connect to create a brand new consumer group. Since new consumer groups have no committed offsets, they default to `auto.offset.reset: earliest`, reading the entire topic from offset 0 and instantly repopulating the Snowflake table.

---

## Scenario 3: Variant Packing vs. Schematization
**Q: You upgraded your Snowflake Kafka Connector from v3 to v4. Suddenly, your streaming data stops landing in your `RECORD_CONTENT` variant column, and instead, Snowflake starts creating dozens of new columns automatically. What happened?**

**Answer:**
In version 4.0+, the Snowflake Connector changed its default behavior from packing the raw JSON/Avro into a single `VARIANT` column to `snowflake.enable.schematization: true`. Schematization attempts to auto-evolve the table schema to match the Avro fields.
If your downstream ELT pipelines or Views rely on extracting data from the `RECORD_CONTENT` column, you must explicitly set `"snowflake.enable.schematization": "false"` in the connector JSON configuration to restore the legacy behavior.

---

## Scenario 4: Architectural Choice - Avro vs JSON
**Q: Why did you choose to serialize your GPS pings in Avro instead of JSON for this pipeline?**

**Answer:**
1. **Bandwidth / Compression:** JSON includes the field names (`"latitude": 40.71`) in every single message. Avro is binary and only sends the values. For 1,000 drivers pinging sub-second, JSON wastes massive amounts of network bandwidth.
2. **Schema Evolution:** Avro requires a strict schema registered in the Schema Registry. If a downstream software engineer accidentally changes the producer to send `"lat"` instead of `"latitude"`, the producer will fail *before* the bad data enters Kafka. With JSON, the bad data pollutes the warehouse.

---

## Scenario 5: Data Quality Location
**Q: Why did you use Great Expectations to validate the data *after* it landed in Snowflake (Warehouse) instead of doing it using a stream processor (like Flink or Spark) *before* it hit Snowflake?**

**Answer:**
There are valid use cases for both, but validating in the warehouse (ELT) is highly advantageous here:
1. **Auditability:** By landing the raw, anomalous data into Snowflake first, we maintain a permanent, auditable record of the bad data. If we dropped it in the stream, we wouldn't be able to historically analyze *why* the sensors failed.
2. **Compute Separation:** Snowflake's massively parallel processing (MPP) can run Great Expectations against millions of rows in seconds. Evaluating complex rules in a stream processor requires maintaining state and can introduce latency or require expensive compute scaling.
