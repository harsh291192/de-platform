## 📘 The Novice-Friendly Learning Guide

### 🏗️ The Big Picture
**The Flow:** `Producer (Python)` → `Kafka (Broker)` → `Spark (Processor)` → `Snowflake (Warehouse)`

**Analogy:**
Imagine a **Social Media Post** is a letter.
1.  **The Producer** is the person writing the letter and putting it in a mailbox.
2.  **Kafka** is the Post Office. It holds the letters safely until someone comes to read them.
3.  **Spark** is a fast-reading translator. It reads a bundle of letters every 10 seconds, translates them into "Sentiment Scores," and summarizes them.
4.  **Snowflake** is the Grand Library where the summaries are stored forever for people to study.

---

### 1️⃣ The Producer (Python + Faker)
*   **WHAT**: A Python script that runs continuously.
*   **WHY**: We need data! Since we aren't paying for the Twitter API, we use a library called `Faker` to generate fake names, locations, and "tweets."
*   **HOW**:
    *   It creates a JSON message: `{"user": "Alice", "text": "I love this!", "timestamp": "..."}`.
    *   It uses a library called `confluent-kafka` to "Produce" (send) this message to Kafka.

### 2️⃣ The Message Broker (Kafka)
*   **WHAT**: A distributed "Log" system.
*   **WHY**: Why not send data directly from Python to Spark? Because if Spark crashes for 1 minute, the data sent during that minute would be lost forever. Kafka acts as a **Buffer**. It stores the data safely on disk so Spark can catch up if it falls behind.
*   **HOW**:
    *   It stores data in a **Topic** (think of it as a folder) called `social_sentiment`.
    *   It is running inside your **Docker** container.

### 3️⃣ The Stream Processor (PySpark)
*   **WHAT**: The "Engine" of the project.
*   **WHY**: This is where the magic happens. We don't just want to store the text; we want to *understand* it. Spark reads the data in "Micro-batches" (every 10 seconds).
*   **HOW**:
    *   **VADER UDF**: We create a "User Defined Function" (UDF). For every tweet, Spark runs the VADER logic to get a score between -1 (Very Negative) and +1 (Very Positive).
    *   **Aggregation**: It calculates the **Average Sentiment** for those 10 seconds.
    *   **Spark-Snowflake Connector**: It packages the results and sends them to Snowflake.

### 4️⃣ The Warehouse (Snowflake)
*   **WHAT**: A Cloud Data Warehouse.
*   **WHY**: This is where the final, cleaned, and processed data lives. From here, you could connect a dashboard (like Tableau or PowerBI) to see a "Live Sentiment Chart."
*   **HOW**:
    *   We create a table called `SENTIMENT_RESULTS`.
    *   Spark "Appends" new rows to this table every 10 seconds.

---

## Prerequisites
- [ ] Docker & Docker Compose installed and running.
- [ ] Python 3.12+ environment activated.
- [ ] Snowflake Account (Trial works fine).

## Step-by-Step Implementation

### Step 1: Infrastructure
Start the Kafka cluster using Docker Compose:
```bash
docker-compose up -d
```
Verify Kafka UI at [http://localhost:8090](http://localhost:8090).

### Step 2: Synthetic Data Producer
We use a Python producer because real social media APIs (like X/Twitter) are now restricted or expensive.
The script `ingestion/streaming/social_sentiment/kafka_producer.py` will:
- Generate JSON like: `{"user": "johndoe", "text": "I love data engineering!", "timestamp": "2024-05-03T07:50:00"}`
- Send to Kafka topic `social_sentiment`.

### Step 3: PySpark Sentiment Processing
The script `processing/spark/streaming/social_sentiment/sentiment_processor.py` will:
- Read from Kafka.
- Apply `vaderSentiment` to get a score (Positive/Negative/Neutral).
- Aggregate every 10 seconds.

### Step 4: Snowflake Integration
Results are pushed to Snowflake using the Spark-Snowflake connector.

## Live Monitoring (Logs)
- **Producer Logs**: Check terminal output or `logs/producer.log`.
- **Kafka Logs**: Use Kafka UI to see the live feed of messages.
- **Spark Logs**: Spark UI at [http://localhost:4040](http://localhost:4040) during execution.
