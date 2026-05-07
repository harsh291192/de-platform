# Code Walkthrough: Social Media Sentiment Pipeline (Interview Prep)

If you are asked to explain this project in an interview, the interviewer will want to see that you understand *why* the code is written a certain way, not just *what* it does. This document breaks down the two main scripts line-by-line with interview-focused explanations.

---

## 1. The Producer: `kafka_producer.py`
**Location:** `ingestion/streaming/social_sentiment/kafka_producer.py`

This script simulates a real-world API streaming data into our system.

### Key Concepts to highlight in an interview:
*   **Asynchronous Messaging:** We use `poll(0)` to handle delivery reports asynchronously without blocking the main loop.
*   **Serialization:** We convert Python dictionaries to JSON strings, and then encode them as UTF-8 bytes before sending to Kafka.

### Code Breakdown:

```python
# The Configuration
conf = {
    'bootstrap.servers': 'localhost:9092',
    'client.id': 'sentiment-producer'
}
producer = Producer(conf)
```
*   **Interview Talking Point:** `bootstrap.servers` is the entry point to the Kafka cluster. In production, we provide multiple brokers here (e.g., `broker1:9092,broker2:9092`) so if one is down, the producer can still connect to the cluster.

```python
def delivery_report(err, msg):
    if err is not None:
        logger.error(f"Message delivery failed: {err}")
    else:
        logger.info(f"Tweet Sent! Topic: {msg.topic()} | Partition: {msg.partition()} | Offset: {msg.offset()}")
```
*   **Interview Talking Point:** This is a **Callback Function**. Kafka operates asynchronously. When we send a message, we don't wait for Kafka to say "got it". Instead, Kafka triggers this function in the background when it finally saves the message. This makes the producer incredibly fast.

```python
producer.produce(
    TOPIC,
    value=message.encode('utf-8'),
    callback=delivery_report
)
producer.poll(0)
```
*   **Interview Talking Point:** `produce()` sends the data to a local memory buffer, not directly to the network. `poll(0)` tells the producer to quickly check if any callbacks (from previous messages) need to be triggered, but the `0` means "don't block/wait".

```python
finally:
    producer.flush()
```
*   **Interview Talking Point:** In a production shutdown sequence (like handling a `SIGTERM`), `flush()` is critical. It forces the producer to wait and push any lingering messages in the local memory buffer to Kafka before the script exits, preventing data loss.

---

## 2. The Processor: `sentiment_processor.py`
**Location:** `processing/spark/streaming/social_sentiment/sentiment_processor.py`

This is a PySpark Structured Streaming application.

### Key Concepts to highlight in an interview:
*   **Micro-batching:** Spark Streaming doesn't process 1 message at a time; it processes small batches of messages every few seconds.
*   **UDFs (User Defined Functions):** We bring Python ML libraries into Spark's distributed JVM environment using UDFs.
*   **Idempotency / Reliability:** We use `foreachBatch` to ensure atomic writes to Snowflake.

### Code Breakdown:

```python
def get_sentiment_score(text):
    scores = analyzer.polarity_scores(text)
    return float(scores['compound'])

sentiment_udf = udf(get_sentiment_score, DoubleType())
```
*   **Interview Talking Point:** Spark is built on Scala/Java (JVM). VADER is a pure Python library. By wrapping VADER in a Spark `udf`, Spark knows how to serialize this Python function and distribute it to all the worker nodes in the cluster so they can run it in parallel.

```python
df = spark.readStream \
    .format("kafka") \
    .option("kafka.bootstrap.servers", "localhost:9092") \
    .option("subscribe", "social_sentiment") \
    .option("startingOffsets", "latest") \
    .load()
```
*   **Interview Talking Point:** This creates a continuous, unbounded DataFrame. `startingOffsets: latest` means when the job starts, it ignores historical data in Kafka and only processes new tweets arriving from that moment forward. (In production, we might use `earliest` for backfilling).

```python
sentiment_df = df.selectExpr("CAST(value AS STRING)") \
    .select(from_json(col("value"), schema).alias("data")) \
    .select("data.*")
```
*   **Interview Talking Point:** Data arrives from Kafka as raw bytes in a `value` column. We must first cast it to a String, and then parse that String using `from_json` against a predefined Schema. This expands the single JSON string into distinct columns (`user`, `text`, `location`, `timestamp`).

```python
def write_to_snowflake(batch_df, batch_id):
    if batch_df.count() > 0:
        batch_df.write \
            .format("snowflake") \
            .options(**sf_options) \
            .option("dbtable", "SENTIMENT_RESULTS") \
            .mode("append") \
            .save()
```
*   **Interview Talking Point:** Why use `foreachBatch` instead of native Snowflake streaming? `foreachBatch` gives us access to the exact DataFrame of the current micro-batch. It allows us to use traditional, robust batch-writing logic (which uses Username/Password) rather than dealing with the complex RSA Keypairs required by Snowflake's native Snowpipe Streaming API.

```python
query = sentiment_df.writeStream \
    .foreachBatch(write_to_snowflake) \
    .option("checkpointLocation", "/tmp/spark_checkpoint/sentiment") \
    .start()
```
*   **Interview Talking Point:** Checkpointing is the most important part of a streaming job. Spark writes its current progress (the Kafka offset) to this directory. If the executor dies and Kubernetes restarts it, Spark reads this directory to resume exactly where it left off, guaranteeing **Exactly-Once** or **At-Least-Once** semantics.
