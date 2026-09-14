from __future__ import annotations

import contextlib
import io
import unittest

from pyspark.sql import Row

from big_data_example.labs.content_platform.dv_e23_check import (
    check_high_engagement_videos,
)
from big_data_example.labs.content_platform.dv_e23_contract import (
    HIGH_ENGAGEMENT_OUTPUT_COLUMNS,
    HIGH_ENGAGEMENT_OUTPUT_SCHEMA,
    VIDEO_INPUT_SCHEMA,
    read_video_metadata,
)
from big_data_example.reference_solutions.content_platform.dv_e23_high_engagement_video_filtering import (
    build_high_engagement_videos,
)
from big_data_example.notebook_support import local_spark, project_path


class HighEngagementVideoFilteringTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.spark = local_spark("dv-e23-test", threads=2)
        cls.spark.sparkContext.setLogLevel("ERROR")
        cls.input_df = read_video_metadata(
            cls.spark,
            project_path(
                "data",
                "samples",
                "interactive-data-engineering-labs",
                "content-platform",
                "source",
                "batch-001",
                "videos.csv",
            ),
        )

    @classmethod
    def tearDownClass(cls) -> None:
        cls.spark.stop()

    def test_fixture_uses_the_declared_schema(self) -> None:
        self.assertEqual(VIDEO_INPUT_SCHEMA, self.input_df.schema)
        self.assertEqual(10, self.input_df.count())

    def test_result_matches_expected_schema_and_ordered_rows(self) -> None:
        expected_df = (
            self.spark.read.option("header", True)
            .schema(HIGH_ENGAGEMENT_OUTPUT_SCHEMA)
            .csv(
                str(
                    project_path(
                        "tests",
                        "fixtures",
                        "interactive-data-engineering-labs",
                        "content-platform",
                        "dv-e23",
                        "expected",
                        "high-engagement-videos.csv",
                    )
                )
            )
            .orderBy("duration", "video_id")
        )

        actual_df = build_high_engagement_videos(self.input_df)

        self.assertEqual(HIGH_ENGAGEMENT_OUTPUT_COLUMNS, actual_df.columns)
        self.assertEqual(HIGH_ENGAGEMENT_OUTPUT_SCHEMA, actual_df.schema)
        self.assertEqual(expected_df.collect(), actual_df.collect())

    def test_view_threshold_is_strict_and_release_threshold_is_inclusive(self) -> None:
        boundary_df = self.spark.createDataFrame(
            [
                Row(101, "At view threshold", "Test", 2024, 10, 1_000_000),
                Row(102, "Before release threshold", "Test", 2018, 20, 1_000_001),
                Row(103, "At release threshold", "Test", 2019, 30, 1_000_001),
            ],
            VIDEO_INPUT_SCHEMA,
        )

        result_ids = [row.video_id for row in build_high_engagement_videos(boundary_df).collect()]

        self.assertEqual([103], result_ids)

    def test_student_checker_accepts_the_reference_result(self) -> None:
        with contextlib.redirect_stdout(io.StringIO()):
            check_high_engagement_videos(
                self.spark,
                build_high_engagement_videos(self.input_df),
            )

    def test_student_checker_rejects_an_untransformed_input(self) -> None:
        with self.assertRaisesRegex(AssertionError, "Output columns"):
            check_high_engagement_videos(self.spark, self.input_df)


if __name__ == "__main__":
    unittest.main()
