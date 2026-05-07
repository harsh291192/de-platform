import json
import random
import time
from datetime import datetime
from typing import Any

from confluent_kafka import Producer
from faker import Faker
from loguru import logger

# 1. Configuration
# We use 'localhost:9092' because this script runs on your machine (outside Docker)
KAFKA_CONFIG = {
    "bootstrap.servers": "localhost:9092",
    "client.id": "sentiment-producer",
}
TOPIC = "social_sentiment"

# 2. Setup
fake = Faker()
producer = Producer(KAFKA_CONFIG)


def delivery_report(err: Any, msg: Any) -> None:
    """
    Callback function: Kafka calls this when a message is successfully sent
    or when it fails. This is how we get "Live Logs" of the success.
    """
    if err is not None:
        logger.error(f"Message delivery failed: {err}")
    else:
        # This will show up in your terminal as the producer runs
        logger.info(
            f"Tweet Sent! Topic: {msg.topic()} | "
            f"Partition: {msg.partition()} | Offset: {msg.offset()}"
        )


def generate_tweet() -> dict:
    """Generates a synthetic tweet-like message using Faker"""
    return {
        "user": fake.user_name(),
        "text": fake.sentence(nb_words=random.randint(5, 15)),
        "location": fake.city(),
        "timestamp": datetime.now().isoformat(),
    }


# 3. Main Loop
logger.info(f"🚀 Starting Producer... sending to topic: {TOPIC}")
logger.info("Press Ctrl+C to stop.")

try:
    while True:
        tweet = generate_tweet()
        # Convert dict to JSON string (Kafka only understands bytes/strings)
        message = json.dumps(tweet)

        # Send to Kafka
        print(f"🐦 Generating Tweet: {tweet['user']} - {tweet['text']}")
        # Send the message!
        # We encode it to utf-8 to turn it into bytes
        producer.produce(TOPIC, value=message.encode("utf-8"), callback=delivery_report)

        # 'poll' triggers the delivery_report callback
        producer.poll(0)

        # Wait a bit between tweets to simulate real people posting
        time.sleep(random.uniform(1, 4))

except KeyboardInterrupt:
    logger.info("Stopping Producer...")
finally:
    # Ensure all messages in the buffer are sent before closing
    producer.flush()
    logger.info("Producer shut down cleanly.")
