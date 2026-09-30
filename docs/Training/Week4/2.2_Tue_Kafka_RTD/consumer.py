from pyspark.sql import SparkSession
from pyspark.sql.functions import from_json, col
from pyspark.sql.types import StructField, StructType, StringType
# from kafka import KafkaConsumer
import json
import base64

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
    .select(col("json.joke"), col("json.time"))

query = processed_df.writeStream \
    .format("console") \
    .outputMode("append") \
    .start()

query.awaitTermination()