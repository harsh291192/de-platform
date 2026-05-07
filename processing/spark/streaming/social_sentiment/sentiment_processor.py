import os

from dotenv import load_dotenv
from pyspark.sql import DataFrame, SparkSession
from pyspark.sql.functions import col, current_timestamp, from_json, udf
from pyspark.sql.types import DoubleType, StringType, StructField, StructType
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

# 0. Load environment variables
load_dotenv()

# 1. Initialize VADER
analyzer = SentimentIntensityAnalyzer()


def get_sentiment_score(text: str) -> float:
    if not text:
        return 0.0
    scores = analyzer.polarity_scores(text)
    return float(scores["compound"])


sentiment_udf = udf(get_sentiment_score, DoubleType())

# 2. Setup Spark Session
spark = (
    SparkSession.builder.appName("SocialMediaSentimentProcessor")
    .config(
        "spark.jars.packages",
        "org.apache.spark:spark-sql-kafka-0-10_2.12:3.5.0,"
        "net.snowflake:spark-snowflake_2.12:2.12.0-spark_3.4",
    )
    .getOrCreate()
)

spark.sparkContext.setLogLevel("WARN")

# 3. Snowflake Options
sf_options = {
    "sfURL": f"{os.getenv('SNOWFLAKE_ACCOUNT')}.snowflakecomputing.com",
    "sfUser": os.getenv("SNOWFLAKE_USER"),
    "sfPassword": os.getenv("SNOWFLAKE_PASSWORD"),
    "sfDatabase": os.getenv("SNOWFLAKE_DATABASE"),
    "sfSchema": "RAW",
    "sfWarehouse": os.getenv("SNOWFLAKE_WAREHOUSE"),
    "sfRole": os.getenv("SNOWFLAKE_ROLE"),
}

# 4. Define Schema
schema = StructType(
    [
        StructField("user", StringType(), True),
        StructField("text", StringType(), True),
        StructField("location", StringType(), True),
        StructField("timestamp", StringType(), True),
    ]
)

# 5. Read Stream from Kafka
df = (
    spark.readStream.format("kafka")
    .option("kafka.bootstrap.servers", "localhost:9092")
    .option("subscribe", "social_sentiment")
    .option("startingOffsets", "latest")
    .load()
)

# 6. Transform Data
sentiment_df = (
    df.selectExpr("CAST(value AS STRING)")
    .select(from_json(col("value"), schema).alias("data"))
    .select("data.*")
    .withColumn("sentiment_score", sentiment_udf(col("text")))
    .select(
        col("user").alias("USER_NAME"),
        col("text").alias("TWEET_TEXT"),
        col("location").alias("LOCATION"),
        col("timestamp").cast("timestamp").alias("TWEET_TIMESTAMP"),
        col("sentiment_score").alias("SENTIMENT_SCORE"),
        current_timestamp().alias("PROCESSED_AT"),
    )
)


# 7. Function to write each batch to Snowflake
def write_to_snowflake(batch_df: DataFrame, batch_id: int) -> None:
    if batch_df.count() > 0:
        print(f"❄️ Writing batch {batch_id} to Snowflake...")
        batch_df.write.format("snowflake").options(**sf_options).option(
            "dbtable", "SENTIMENT_RESULTS"
        ).mode("append").save()


# 8. Start the Streaming Query using foreachBatch
query = (
    sentiment_df.writeStream.foreachBatch(write_to_snowflake)
    .option("checkpointLocation", "/tmp/spark_checkpoint/sentiment")
    .start()
)

print("🚀 Pipeline LIVE: Processing tweets and writing to Snowflake...")
query.awaitTermination()
