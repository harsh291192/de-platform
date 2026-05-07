import datetime
import logging
import random
import time
from typing import Any

from confluent_kafka import SerializingProducer
from confluent_kafka.schema_registry import SchemaRegistryClient
from confluent_kafka.schema_registry.avro import AvroSerializer
from confluent_kafka.serialization import StringSerializer

# Configure Logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s | %(levelname)-8s | %(message)s"
)
logger = logging.getLogger(__name__)

TOPIC = "ride_sharing_gps"
SCHEMA_REGISTRY_URL = "http://localhost:8081"
BOOTSTRAP_SERVERS = "localhost:9092"

# 1. Define the Avro Schema
# This enforces strict typing and compresses the payload into tiny binary packets
avro_schema_str = """
{
  "type": "record",
  "name": "GPSPing",
  "namespace": "com.ride_sharing",
  "fields": [
    {"name": "driver_id", "type": "int"},
    {"name": "latitude", "type": "double"},
    {"name": "longitude", "type": "double"},
    {"name": "speed_mph", "type": "double"},
    {"name": "timestamp", "type": "string"}
  ]
}
"""

# 2. Setup the Schema Registry Client and Avro Serializer
schema_registry_conf = {"url": SCHEMA_REGISTRY_URL}
schema_registry_client = SchemaRegistryClient(schema_registry_conf)

avro_serializer = AvroSerializer(
    schema_registry_client,
    avro_schema_str,
    to_dict=lambda obj, ctx: obj,  # Our object is already a dict
)

# 3. Configure the Serializing Producer
producer_conf = {
    "bootstrap.servers": BOOTSTRAP_SERVERS,
    "client.id": "ride-sharing-producer",
    "key.serializer": StringSerializer("utf_8"),
    "value.serializer": avro_serializer,
}

producer = SerializingProducer(producer_conf)


def delivery_report(err: Any, msg: Any) -> None:
    if err is not None:
        logger.error(f"Delivery failed: {err}")
    else:
        # Avoid printing every single message at high velocity
        # to prevent terminal freezing
        pass


logger.info(f"🚀 Starting Avro GPS Producer... sending to topic: {TOPIC}")
logger.info("Press Ctrl+C to stop.")

try:
    message_count = 0
    while True:
        # Simulate 1,000 drivers driving around NYC (approx boundaries)
        driver_id = random.randint(1, 1000)

        # Base realistic data
        lat = random.uniform(40.47, 40.91)
        lon = random.uniform(-74.25, -73.70)
        speed = random.uniform(0.0, 65.0)

        # ⚠️ INJECT ANOMALIES (for Great Expectations to catch later!)
        anomaly_roll = random.random()
        if anomaly_roll < 0.01:
            # 1% chance: Driver teleports to the middle of the Atlantic Ocean
            lat = 0.0
            lon = 0.0
            logger.warning(
                f"🛸 Anomaly Injected: Driver {driver_id} teleported to ocean."
            )
        elif anomaly_roll < 0.02:
            # 1% chance: Impossible speed (300+ MPH)
            speed = random.uniform(300.0, 500.0)
            logger.warning(
                f"🏎️ Anomaly Injected: Driver {driver_id} driving {speed:.0f} MPH."
            )
        elif anomaly_roll < 0.03:
            # 1% chance: Negative speed (Reverse logic error)
            speed = -15.0
            logger.warning(
                f"🔙 Anomaly Injected: Driver {driver_id} has negative speed."
            )

        # Construct the payload matching the Avro schema
        payload = {
            "driver_id": driver_id,
            "latitude": lat,
            "longitude": lon,
            "speed_mph": speed,
            "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        }

        # Send to Kafka with Avro serialization
        producer.produce(
            topic=TOPIC,
            key=str(driver_id),  # Key ensures same driver goes to same partition
            value=payload,
            on_delivery=delivery_report,
        )

        # Poll and occasionally print status
        producer.poll(0)
        message_count += 1

        if message_count % 500 == 0:
            logger.info(f"Sent {message_count} GPS pings so far...")

        # Very short sleep to simulate high velocity
        time.sleep(0.01)

except KeyboardInterrupt:
    logger.info("Stopping Producer...")
finally:
    logger.info("Flushing buffer... please wait.")
    producer.flush()
    logger.info("Producer shut down cleanly.")
