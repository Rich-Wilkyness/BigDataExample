"""Reference solution for DV-E23 high-engagement video filtering."""

from __future__ import annotations

from pyspark.sql import DataFrame
from pyspark.sql import functions as F

from big_data_example.labs.content_platform.dv_e23_check import (
    check_high_engagement_videos,
)
from big_data_example.labs.content_platform.dv_e23_contract import (
    HIGH_ENGAGEMENT_OUTPUT_COLUMNS,
    read_video_metadata,
)
from big_data_example.notebook_support import local_spark, project_path


def build_high_engagement_videos(video_stream_df: DataFrame) -> DataFrame:
    """Return recent videos with strictly more than one million views."""

    return (
        video_stream_df.where(
            (F.col("view_count") > F.lit(1_000_000))
            & (F.col("release_year") >= F.lit(2019))
        )
        .select(*HIGH_ENGAGEMENT_OUTPUT_COLUMNS)
        .orderBy(F.col("duration").asc(), F.col("video_id").asc())
    )


def main() -> None:
    """Run and validate the reference solution locally."""

    spark = local_spark("dv-e23-reference-solution", threads=2)
    spark.sparkContext.setLogLevel("ERROR")
    try:
        input_path = project_path(
            "data",
            "samples",
            "interactive-data-engineering-labs",
            "content-platform",
            "source",
            "batch-001",
            "videos.csv",
        )
        input_df = read_video_metadata(spark, input_path)
        result_df = build_high_engagement_videos(input_df)
        check_high_engagement_videos(spark, result_df)
        result_df.show(truncate=False)
    finally:
        spark.stop()


if __name__ == "__main__":
    main()
