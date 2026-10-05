"""Supplied setup for Part 2: raw market events to partitioned Parquet, no aggregation."""
from pyspark.sql import SparkSession, functions as F, types as T

schema = T.StructType([
    T.StructField("sequence", T.LongType()),
    T.StructField("symbol", T.StringType()),
    T.StructField("price", T.DoubleType()),
    T.StructField("size", T.IntegerType()),
    T.StructField("side", T.StringType()),
    T.StructField("exchange_ts", T.StringType()),
    T.StructField("api_ts", T.StringType()),
    T.StructField("kafka_ts", T.StringType()),
])

spark = SparkSession.builder.master("local[2]").appName("Market Parquet Setup").getOrCreate()
spark.conf.set("spark.sql.session.timeZone", "UTC")
spark.sparkContext.setLogLevel("WARN")

raw = (spark.readStream.format("kafka")
       .option("kafka.bootstrap.servers", "localhost:9092")
       .option("subscribe", "market_ticks")
       .option("startingOffsets", "latest")
       .load())
ticks = raw.select(F.from_json(F.col("value").cast("string"), schema).alias("tick")).select("tick.*")
stored = (ticks.withColumn("event_time", F.to_timestamp("exchange_ts"))
          .filter(F.col("event_time").isNotNull())
          .withColumn("event_date", F.to_date("event_time"))
          .withColumn("event_hour", F.hour("event_time"))
          .withColumn("processed_ts", F.current_timestamp()))

query = (stored.writeStream.format("parquet")
         .outputMode("append")
         .option("path", "/tmp/market-lake/spark/market_ticks")
         .option("checkpointLocation", "/tmp/market-lake/checkpoints/spark-market-parquet")
         .partitionBy("event_date", "event_hour")
         .trigger(processingTime="2 seconds")
         .start())
query.awaitTermination()
