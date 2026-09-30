from pyspark.sql import SparkSession

from pyspark.sql.functions import (
    from_json,
    col,
    current_timestamp,
    round
)

from pyspark.sql.types import (
    StructType,
    StructField,
    StringType,
    DoubleType,
    IntegerType
)


# -------------------------------------------------
# Spark
# -------------------------------------------------

spark = SparkSession.builder \
    .master("local[*]") \
    .appName("WeatherStreaming") \
    .getOrCreate()

spark.sparkContext.setLogLevel("ERROR")


# -------------------------------------------------
# Kafka
# -------------------------------------------------

df = spark.readStream \
    .format("kafka") \
    .option(
        "kafka.bootstrap.servers",
        "localhost:9092"
    ) \
    .option(
        "subscribe",
        "weather"
    ) \
    .option(
        "startingOffsets",
        "latest"
    ) \
    .load()


# -------------------------------------------------
# JSON schema
# -------------------------------------------------

json_schema = StructType([

    StructField(
        "city",
        StringType(),
        True
    ),

    StructField(
        "latitude",
        DoubleType(),
        True
    ),

    StructField(
        "longitude",
        DoubleType(),
        True
    ),

    StructField(
        "temperature",
        DoubleType(),
        True
    ),

    StructField(
        "feels_like",
        DoubleType(),
        True
    ),

    StructField(
        "humidity",
        IntegerType(),
        True
    ),

    StructField(
        "precipitation",
        DoubleType(),
        True
    ),

    StructField(
        "cloud_cover",
        IntegerType(),
        True
    ),

    StructField(
        "pressure",
        DoubleType(),
        True
    ),

    StructField(
        "wind_speed",
        DoubleType(),
        True
    ),

    StructField(
        "wind_direction",
        IntegerType(),
        True
    ),

    StructField(
        "event_time",
        StringType(),
        True
    )
])


# -------------------------------------------------
# Parse Kafka messages
# -------------------------------------------------

processed_df = df.selectExpr(

    "CAST(key AS STRING) AS kafka_key",
    "CAST(value AS STRING) AS value",

    "partition AS kafka_partition",
    "offset AS kafka_offset"

).withColumn(

    "json",
    from_json(
        col("value"),
        json_schema
    )

).select(

    "kafka_key",
    "kafka_partition",
    "kafka_offset",

    "json.*"

).withColumn(

    "processed_at",
    current_timestamp()

)


# -------------------------------------------------
# Example Spark transformation
#
# Fahrenheit gives us something obvious to show
# students that Spark actually transformed the data.
# -------------------------------------------------

processed_df = processed_df.withColumn(

    "temperature_f",

    round(
        (col("temperature") * 9 / 5) + 32,
        1
    )

)


# -------------------------------------------------
# Write each Spark micro-batch to MongoDB
# -------------------------------------------------

def write_to_mongodb(batch_df, batch_id):

    print(
        f"Writing Spark batch {batch_id} "
        f"to MongoDB"
    )

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
            "weather"
        ) \
        .save()


# -------------------------------------------------
# Start stream
# -------------------------------------------------

query = processed_df.writeStream \
    .foreachBatch(write_to_mongodb) \
    .outputMode("append") \
    .trigger(
        processingTime="5 seconds"
    ) \
    .option(
        "checkpointLocation",
        "/tmp/weather-mongodb-checkpoint"
    ) \
    .start()


query.awaitTermination()