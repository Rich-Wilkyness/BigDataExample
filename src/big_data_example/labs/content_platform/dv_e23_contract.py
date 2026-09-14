"""Data contract and fixture reader for DV-E23."""

from __future__ import annotations

from pathlib import Path

from pyspark.sql import DataFrame, SparkSession
from pyspark.sql.types import IntegerType, LongType, StringType, StructField, StructType


VIDEO_INPUT_SCHEMA = StructType(
    [
        StructField("video_id", IntegerType(), True),
        StructField("title", StringType(), True),
        StructField("genre", StringType(), True),
        StructField("release_year", IntegerType(), True),
        StructField("duration", IntegerType(), True),
        StructField("view_count", LongType(), True),
    ]
)

HIGH_ENGAGEMENT_OUTPUT_COLUMNS = [
    "duration",
    "genre",
    "release_year",
    "title",
    "video_id",
    "view_count",
]

HIGH_ENGAGEMENT_OUTPUT_SCHEMA = StructType(
    [VIDEO_INPUT_SCHEMA[field_name] for field_name in HIGH_ENGAGEMENT_OUTPUT_COLUMNS]
)


def read_video_metadata(spark: SparkSession, path: str | Path) -> DataFrame:
    """Read the synthetic CSV delivery using the declared input contract."""

    return spark.read.option("header", True).schema(VIDEO_INPUT_SCHEMA).csv(str(path))
