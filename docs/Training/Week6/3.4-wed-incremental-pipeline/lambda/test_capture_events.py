"""Offline completion publication and duplicate/out-of-order event checks."""

import copy
import json
import os
import unittest
from unittest.mock import Mock, patch

from botocore.exceptions import ClientError

import ingestion
import prepare_batch
from prepare_batch import CONTROL, LOCK_KEY, PipelineBusyError, capture_key, encode, utc
import test_prepare_batch as baseline

FakeS3 = baseline.FakeS3


class IngestionTests(unittest.TestCase):
    def setUp(self):
        self.s3 = FakeS3()
        self.now = utc("2026-10-19T10:10:00Z")
        self.discovery = {"data": {"en": {"feeds": [
            {"name": feed, "url": feed} for feed in sorted(ingestion.FEEDS)
        ]}}}

    def download(self, url):
        if url == ingestion.GBFS_URL:
            return self.discovery
        return {"data": {"stations": [{"station_id": "a"}]}}

    def test_completion_is_last_and_lists_exact_capture_objects(self):
        result = ingestion.capture(self.s3, "bucket", self.download, self.now)
        self.assertEqual(result["files_uploaded"], 5)
        self.assertEqual(result["data_files_uploaded"], 4)
        self.assertEqual(self.s3.writes[-1], result["completion_key"])
        marker = json.loads(self.s3.objects[result["completion_key"]][0])
        self.assertEqual(marker["objects"], result["objects"][:-1])
        self.assertTrue(all(key in self.s3.objects for key in marker["objects"]))

    def test_failed_download_publishes_nothing(self):
        def fail(url):
            if url == "station_status":
                raise TimeoutError("API unavailable")
            return self.download(url)

        with self.assertRaises(TimeoutError):
            ingestion.capture(self.s3, "bucket", fail, self.now)
        self.assertEqual(self.s3.writes, [])

    def test_partial_upload_never_publishes_completion(self):
        original = self.s3.put_object

        def fail(**kwargs):
            if "/station_status/" in kwargs["Key"]:
                raise RuntimeError("Upload failed")
            return original(**kwargs)

        self.s3.put_object = fail
        with self.assertRaises(RuntimeError):
            ingestion.capture(self.s3, "bucket", self.download, self.now)
        self.assertFalse(any("/completed/" in key for key in self.s3.objects))

    def test_same_second_capture_cannot_overwrite_existing_objects(self):
        ingestion.capture(self.s3, "bucket", self.download, self.now)
        original = copy.deepcopy(self.s3.objects)
        with self.assertRaisesRegex(RuntimeError, "PreconditionFailed"):
            ingestion.capture(self.s3, "bucket", self.download, self.now)
        self.assertEqual(self.s3.objects, original)

    def test_missing_feed_leaves_no_marker(self):
        self.discovery["data"]["en"]["feeds"] = []
        with self.assertRaisesRegex(ValueError, "feeds"):
            ingestion.capture(self.s3, "bucket", self.download, self.now)
        self.assertEqual(self.s3.objects, {})


class EventPreparationTests(unittest.TestCase):
    setUp = baseline.PrepareTests.setUp
    run_prepare = baseline.PrepareTests.run_prepare

    def capture(self, stamp):
        baseline.PrepareTests.capture(self, stamp)
        capture = utc(stamp)
        for feed in ["gbfs_discovery", "system_information"]:
            self.s3.put_object(Bucket="bucket", Key=capture_key(feed, capture), Body=b'{}')
        key = f"bronze/citibike/completed/capture_{capture.strftime('%Y%m%dT%H%M%SZ')}.json"
        self.s3.put_object(Bucket="bucket", Key=key, Body=encode({
            "version": 1, "bucket": "bucket",
            "capture_id": capture.strftime('%Y%m%dT%H%M%SZ'),
            "snapshot_time": capture.isoformat(),
            "objects": [capture_key(feed, capture) for feed in [
                "gbfs_discovery", "station_information", "station_status", "system_information",
            ]],
        }))
        return key

    def test_event_bounds_processing_to_its_completed_capture(self):
        first = self.capture("2026-10-19T10:10:00Z")
        self.capture("2026-10-19T10:15:00Z")
        result = self.run_prepare({"completion_key": first})
        self.assertEqual(result["capture_count"], 1)
        self.assertEqual(result["expected_rows"], 2)
        self.assertEqual(result["window_end"], "2026-10-19T10:10:01Z")

    def test_duplicate_event_after_acceptance_does_not_publish_another_batch(self):
        key = self.capture("2026-10-19T10:10:00Z")
        result = self.run_prepare({"completion_key": key})
        self.job.release(self.owner)
        self.job.checkpoint.return_value = utc(result["window_end"])
        original = {k for k in self.s3.objects if k.startswith(CONTROL + "batches/")}
        duplicate = self.job.prepare({"completion_key": key}, "duplicate", self.now)
        self.assertEqual(duplicate["status"], "NO_DATA")
        self.assertEqual(original, {k for k in self.s3.objects if k.startswith(CONTROL + "batches/")})

    def test_overlapping_event_waits_then_can_prepare_remaining_capture(self):
        first = self.capture("2026-10-19T10:10:00Z")
        second = self.capture("2026-10-19T10:15:00Z")
        result = self.run_prepare({"completion_key": first})
        with self.assertRaises(PipelineBusyError):
            self.job.prepare({"completion_key": second}, "second", self.now)
        self.job.release(self.owner)
        self.job.checkpoint.return_value = utc(result["window_end"])
        pending = self.job.prepare({"completion_key": second}, "second", self.now)
        self.assertEqual(pending["capture_count"], 1)
        self.assertEqual(pending["expected_rows"], 2)

    def test_earlier_marker_missing_stops_acceptance_of_later_capture(self):
        baseline.PrepareTests.capture(self, "2026-10-19T10:05:00Z")
        later = self.capture("2026-10-19T10:10:00Z")
        with self.assertRaisesRegex(ValueError, "missing"):
            self.run_prepare({"completion_key": later})
        self.assertEqual(self.job.optional_json(LOCK_KEY)[0]["state"], "active")

    def test_wrong_bucket_marker_is_rejected_before_locking(self):
        key = self.capture("2026-10-19T10:10:00Z")
        marker = json.loads(self.s3.objects[key][0])
        marker["bucket"] = "someone-else"
        self.s3.put_object(Bucket="bucket", Key=key, Body=encode(marker))
        with self.assertRaisesRegex(ValueError, "bucket"):
            self.run_prepare({"completion_key": key})
        self.assertNotIn(LOCK_KEY, self.s3.objects)

    def test_event_cannot_supply_a_different_window_end(self):
        key = self.capture("2026-10-19T10:10:00Z")
        with self.assertRaisesRegex(ValueError, "window_end"):
            self.run_prepare({"completion_key": key, "window_end": "2026-10-19T10:15:00Z"})

    def test_preview_with_completion_does_not_write(self):
        key = self.capture("2026-10-19T10:10:00Z")
        original = copy.deepcopy(self.s3.objects)
        result = self.run_prepare({"preview": True, "completion_key": key})
        self.assertEqual(result["status"], "PREVIEW")
        self.assertEqual(original, self.s3.objects)

    def test_conditional_lock_race_is_busy_but_other_errors_propagate(self):
        def error(code):
            return ClientError({"Error": {"Code": code}}, "PutObject")

        self.job.acquire = Mock(side_effect=error("PreconditionFailed"))
        with self.assertRaises(PipelineBusyError):
            self.run_prepare()
        self.job.acquire = Mock(side_effect=error("AccessDenied"))
        with self.assertRaises(ClientError):
            self.run_prepare()


class HandlerTests(unittest.TestCase):
    def test_busy_owner_becomes_waitable_status(self):
        environment = {
            "AWS_REGION": "us-east-2", "BUCKET": "bucket",
            "REDSHIFT_WORKGROUP": "workgroup", "REDSHIFT_DATABASE": "dev",
            "EXECUTION_ARN_PREFIX": "arn:aws:states:us-east-2:866934333672:execution:workflow:",
        }
        event = {"execution_id": environment["EXECUTION_ARN_PREFIX"] + "one", "request": {}}
        with patch.dict(os.environ, environment), patch("prepare_batch.boto3.Session"), patch("prepare_batch.BatchPreparer") as factory:
            factory.return_value.prepare.side_effect = PipelineBusyError("busy")
            self.assertEqual(prepare_batch.lambda_handler(event, None), {"status": "BUSY"})
            factory.return_value.prepare.side_effect = ClientError(
                {"Error": {"Code": "PreconditionFailed"}}, "GetObject",
            )
            # A changed source is a real failure, not an ownership wait.
            with self.assertRaises(ClientError):
                prepare_batch.lambda_handler(event, None)


if __name__ == "__main__":
    unittest.main()
