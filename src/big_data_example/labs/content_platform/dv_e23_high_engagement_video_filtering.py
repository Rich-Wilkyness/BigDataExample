"""Learner implementation for DV-E23 high-engagement video filtering."""

from __future__ import annotations

from pyspark.sql import DataFrame
from pyspark.sql import functions as F

from big_data_example.labs.content_platform.dv_e23_contract import (
    HIGH_ENGAGEMENT_OUTPUT_COLUMNS,
)


def build_high_engagement_videos(video_stream_df: DataFrame) -> DataFrame:
    """Return the DV-E23 result described by the guided notebook."""

    # TODO: Replace this starter result with the required PySpark transformation.
    return video_stream_df
