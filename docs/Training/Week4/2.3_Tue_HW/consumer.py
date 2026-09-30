"""Part 3 starter: console first, then MongoDB. Add your own transformation."""

import argparse

from pyspark.sql import SparkSession, functions as F, types as T

parser = argparse.ArgumentParser()
parser.add_argument("--sink", choices=["console", "mongodb"], default="console")
args = parser.parse_args()

spark = SparkSession.builder.master("local[2]").appName("HomeworkWeather").getOrCreate()
spark.sparkContext.setLogLevel("WARN")

schema = T.StructType([
    T.StructField("city", T.StringType()),
    T.StructField("latitude", T.DoubleType()),
    T.StructField("longitude", T.DoubleType()),
    T.StructField("temperature", T.DoubleType()),
    T.StructField("feels_like", T.DoubleType()),
    T.StructField("humidity", T.IntegerType()),
    T.StructField("precipitation", T.DoubleType()),
    T.StructField("cloud_cover", T.IntegerType()),
    T.StructField("pressure", T.DoubleType()),
    T.StructField("wind_speed", T.DoubleType()),
    T.StructField("wind_direction", T.IntegerType()),
    T.StructField("weather_code", T.IntegerType()),
    T.StructField("event_time", T.StringType()),
])

raw = (spark.readStream.format("kafka")
       .option("kafka.bootstrap.servers", "localhost:9092")
       .option("subscribe", "homework-weather")
       .option("startingOffsets", "earliest")
       .load())

events = (raw.select(
    F.col("key").cast("string").alias("key"),
    "partition", "offset",
    F.from_json(F.col("value").cast("string"), schema).alias("event"),
).select("key", "partition", "offset", "event.*"))

# add transformations here:
coldWeather = events.filter(
    F.col("temperature") < 20.0
)

processed = coldWeather.withColumn("processed_at", F.current_timestamp())


def write_to_mongodb(batch_df, batch_id):
    if batch_df.isEmpty():
        return
    print(f"Writing batch {batch_id} to homework_streaming.weather")
    (batch_df.write.format("mongodb").mode("append")
     .option("connection.uri", "mongodb://localhost:27017/")
     .option("database", "homework_streaming")
     .option("collection", "weather")
     .save())


writer = (processed.writeStream.outputMode("append")
          .trigger(processingTime="5 seconds")
          .option("checkpointLocation", f"data/checkpoints/week4-homework-weather-{args.sink}"))

if args.sink == "console":
    query = writer.format("console").option("truncate", "false").start()
else:
    query = writer.foreachBatch(write_to_mongodb).start()

query.awaitTermination()
