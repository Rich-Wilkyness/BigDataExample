from pyspark.sql import SparkSession
from pyspark.sql import functions as F
from pyspark.sql import types as T


spark = SparkSession.builder.appName("week4-kafka-jokes").getOrCreate()
spark.sparkContext.setLogLevel("WARN")

json_schema = T.StructType(
    [
        T.StructField("joke_id", T.StringType(), nullable=False),
        T.StructField("joke", T.StringType(), nullable=False),
        T.StructField("length", T.IntegerType(), nullable=False),
        T.StructField("event_time", T.StringType(), nullable=False),
    ]
)

raw_events = (
    spark.readStream
    .format("kafka")
    .option("kafka.bootstrap.servers", "localhost:9092")
    .option("subscribe", "jokes")
    .option("startingOffsets", "earliest")
    .load()
)

decoded_events = raw_events.select(
    "topic",
    "partition",
    "offset",
    F.col("key").cast("string").alias("event_key"),
    F.col("value").cast("string").alias("value_json"),
)

events = (
    decoded_events
    .withColumn("event", F.from_json("value_json", json_schema))
    .select(
        "topic",
        "partition",
        "offset",
        "event_key",
        F.col("event.joke_id").alias("joke_id"),
        F.col("event.joke").alias("joke"),
        F.col("event.length").alias("length"),
        F.to_timestamp("event.event_time").alias("event_time"),
    )
    .withColumn(
        "is_valid",
        F.col("joke_id").isNotNull()
        & F.col("joke").isNotNull()
        & F.col("length").isNotNull()
        & F.col("event_time").isNotNull(),
    )
    .where(
        F.col("length") > 100
    )
)

query = (
    events.writeStream
    .format("console")
    .outputMode("append")
    .option("truncate", "false")
    .option("checkpointLocation", "data/checkpoints/week4-jokes-console")
    .start()
)

try:
    query.awaitTermination()
finally:
    query.stop()
    spark.stop()
