from pyspark.sql import SparkSession
from pyspark.sql.functions import from_json, col, current_timestamp
from pyspark.sql.types import StructField, StructType, StringType
# from kafka import KafkaConsumer
import json
import base64
import time

# current_timestamp = time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime())

spark = SparkSession.builder \
    .master("local[*]") \
    .appName("spark structured streaming test") \
    .getOrCreate()

    # could use this in future instead of provided spark-submit command
    # .config("spark.jars.packages", "org.apache.spark:spark-sql-kafka-0-10_2.13:3.5.0") \

spark.sparkContext.setLogLevel("ERROR")

df = spark.readStream.format("kafka") \
    .option("kafka.bootstrap.servers", "localhost:9092") \
    .option("subscribe", "test-topic") \
    .load()

json_schema = StructType([
    StructField("joke", StringType(), True),
    StructField("time", StringType(), True)
])

processed_df = df.selectExpr("CAST(key AS STRING)", "CAST(value AS STRING)") \
    .withColumn("json", from_json(col("value"), json_schema)) \
    .select(col("json.joke"), col("json.time")) \
    .withColumn("processed_at", current_timestamp())

def write_to_mongodb(batch_df, batch_id):
    print(f"Writing batch {batch_id} to MongoDB")

    batch_df.write \
    .format("mongodb") \
    .mode("append") \
    .option(
            "spark.mongodb.write.connection.uri",
            "mongodb://localhost:27017/"
        ) \
    .option(
            "spark.mongodb.write.database",
            "streaming_demo"
        ) \
     .option(
            "spark.mongodb.write.collection",
            "jokes"
        ) \
    .save()




query = processed_df.writeStream \
    .foreachBatch(write_to_mongodb) \
    .outputMode("append") \
    .trigger(processingTime="5 seconds") \
    .option("checkpointLocation", "/tmp/kafka-mongodb-checkpoint") \
    .start()

query.awaitTermination()