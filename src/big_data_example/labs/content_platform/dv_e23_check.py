"""Student-facing result check for DV-E23."""

from __future__ import annotations

from pyspark.sql import DataFrame, SparkSession

from big_data_example.labs.content_platform.dv_e23_contract import (
    HIGH_ENGAGEMENT_OUTPUT_COLUMNS,
    HIGH_ENGAGEMENT_OUTPUT_SCHEMA,
)
from big_data_example.notebook_support import project_path


def check_high_engagement_videos(spark: SparkSession, actual_df: DataFrame) -> None:
    """Raise a focused assertion when the learner result violates the contract."""

    if actual_df.columns != HIGH_ENGAGEMENT_OUTPUT_COLUMNS:
        raise AssertionError(
            "Output columns or their order do not match the problem contract."
        )

    if actual_df.schema != HIGH_ENGAGEMENT_OUTPUT_SCHEMA:
        raise AssertionError("Output Spark types do not match the problem contract.")

    expected_path = project_path(
        "tests",
        "fixtures",
        "interactive-data-engineering-labs",
        "content-platform",
        "dv-e23",
        "expected",
        "high-engagement-videos.csv",
    )
    expected_df = (
        spark.read.option("header", True)
        .schema(HIGH_ENGAGEMENT_OUTPUT_SCHEMA)
        .csv(str(expected_path))
        .orderBy("duration", "video_id")
    )

    if actual_df.collect() != expected_df.collect():
        raise AssertionError(
            "Output rows do not match the contract. Recheck predicates, null behavior, projection, and deterministic ordering."
        )

    print("PASS: your result matches the DV-E23 contract.")
