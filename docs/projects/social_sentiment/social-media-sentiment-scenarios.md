# Social Media Sentiment Pipeline: Scenarios & Troubleshooting

As a Data Engineer, writing the code is only 20% of the job. The other 80% is understanding what happens when things inevitably break, pause, or surge.

Here are the most common scenarios and questions regarding our Kafka + Spark Streaming architecture.

---

### 1. How many messages can a Kafka broker hold?

**The short answer:** As many as your hard drive can fit!

**The detailed answer:**
Unlike a traditional message queue (like RabbitMQ) which deletes a message as soon as it's read, Kafka is essentially a "Log Book". It writes every message to the disk and keeps it there based on a **Retention Policy**.

By default, Kafka's retention policy is **7 days**. This means Kafka will hold millions (or billions) of messages until they are exactly 7 days old, and then it automatically deletes them to free up disk space. You can also configure Kafka to delete data based on size (e.g., "Keep a maximum of 50GB of messages").

> **Pro Tip:** Because Kafka stores data on disk, you can actually have *multiple* different processors reading the exact same data at different speeds without them interfering with each other.

---

### 2. If the processor is off, but the producer keeps running, how does Spark catch up? Will there be lag?

**Scenario:** Your producer runs all night, generating 100,000 tweets. You wake up and turn on the Spark Processor.

**What happens:**
Yes, there will be **Consumer Lag**. When you start the Spark Processor, the data arriving in Snowflake will initially be the old data from the night before.

However, Spark is incredibly fast. While your producer is generating maybe 5 tweets per second, Spark can process *thousands* of tweets per second. Spark will read large "chunks" (micro-batches) of the old data, process it rapidly, and push it to Snowflake.

The lag will steadily decrease until Spark completely catches up to the "live" data. Once caught up, the lag drops to near-zero.

> **Backpressure:** If there are 10 million old messages in Kafka, Spark might crash trying to load them all into memory at once. To prevent this, Data Engineers use a setting called `maxOffsetsPerTrigger`. This tells Spark: *"No matter how far behind you are, never read more than 10,000 messages at a time."*

---

### 3. If the processor crashes, where does it restart from?

**Scenario:** Spark is happily processing tweets. Suddenly, your laptop runs out of battery and the processor crashes. The producer is still sending data to Kafka. When you turn your laptop back on and start Spark, does it skip the tweets that were sent while it was off? Does it re-process the old ones?

**What happens:**
It will start **exactly where it left off!** No data is skipped, and no data is duplicated.

**How it works:**
If you look at `processing/social_sentiment/sentiment_processor.py`, you will see this line:
`.option("checkpointLocation", "/tmp/spark_checkpoint/sentiment")`

Every time Spark successfully reads a batch of messages and saves them to Snowflake, it writes a tiny note in this `checkpoint` folder. The note says: *"I have successfully processed up to message #45,291"*. (This number is called an **Offset**).

When Spark crashes and turns back on, the very first thing it does is read that checkpoint file. It sees #45,291, goes to Kafka, and says: *"Give me everything starting from message #45,292."*

> **Exactly-Once Processing:** This is exactly why Kafka + Spark is the industry standard. It guarantees that you never lose data even during severe hardware failures.

---

### 4. What if Snowflake goes down for maintenance?

**Scenario:** The producer is running. Spark reads a batch of tweets from Kafka, calculates the sentiment, but when it tries to write to Snowflake, Snowflake is offline.

**What happens:**
Spark will throw an error and crash. But because of the **Checkpointing** mechanism mentioned above, Spark will *not* update its checkpoint file. The data remains safely stored in Kafka.
Once Snowflake comes back online, you simply restart Spark. It will read the exact same batch from Kafka again and successfully push it to Snowflake.

---

### 5. What if the Producer sends "bad" data (Malformed JSON)?

**Scenario:** A bug in the producer causes it to send `{"user": "Alice", text: I forgot quotes!}` instead of valid JSON.

**What happens:**
Spark expects a specific schema. In our script, we use the `from_json()` function. By default, if Spark encounters bad JSON, it won't crash. Instead, it will output `null` for all the columns of that specific bad message.
As a Data Engineer, you can configure Spark's `mode` to `PERMISSIVE` (put bad records in a special 'corrupt' column), `DROPMALFORMED` (ignore bad records completely), or `FAILFAST` (crash the pipeline so you can fix the bug immediately).

---

### 6. What if Kafka crashes? Where do the Producer's messages go?

**Scenario:** Your Python producer is running perfectly, generating tweets. Suddenly, the Kafka server completely crashes and goes offline. The producer keeps generating tweets. Where do they go?

**What happens:**
Believe it or not, the Python producer *does not* crash immediately! It will keep running, but the messages are stored in its **Local Memory Buffer**.

When you call `producer.produce()` in Python, you are not sending the data over the internet to Kafka. You are actually just dropping it into a bucket in your computer's RAM. A hidden background thread in the Kafka library is responsible for taking batches of messages from that bucket and sending them to the Kafka server.

If Kafka is down:
1. The background thread will keep trying to connect and will print errors to your terminal (like `Connection refused`—exactly what you saw earlier!).
2. Your Python script keeps dropping tweets into the local RAM bucket.
3. If Kafka comes back online quickly, the producer will automatically reconnect and flush the entire bucket to Kafka at lightning speed.

**The Danger (Data Loss):**
If Kafka is down for too long, the bucket fills up. By default, the producer can hold about 100,000 messages in RAM. If it hits that limit, the next time your code calls `produce()`, it will throw a `BufferError: Local: Queue full` and your script will crash, causing the tweets in the bucket to be permanently lost. (Messages also have a default 5-minute timeout; if they sit in the bucket longer than 5 minutes waiting for Kafka to wake up, they are dropped).
