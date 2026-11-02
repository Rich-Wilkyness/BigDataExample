"""Offline failure/concurrency checks; no AWS credentials or requests required."""

import copy
import hashlib
import io
import json
import unittest
from datetime import timedelta
from unittest.mock import Mock

from prepare_batch import BatchPreparer, CONTROL, LOCK_KEY, capture_key, encode, utc


class FakeS3:
    class exceptions:
        class NoSuchKey(Exception):
            pass

    def __init__(self):
        self.objects = {}
        self.writes = []

    def put_object(self, Bucket, Key, Body, IfMatch=None, IfNoneMatch=None, **kwargs):
        old = self.objects.get(Key)
        if IfNoneMatch == "*" and old is not None:
            raise RuntimeError("PreconditionFailed")
        if IfMatch is not None and (old is None or old[1] != IfMatch):
            raise RuntimeError("PreconditionFailed")
        raw = Body if isinstance(Body, bytes) else Body.encode()
        etag = '"' + hashlib.md5(raw).hexdigest() + '"'
        self.objects[Key] = (raw, etag)
        self.writes.append(Key)
        return {"ETag": etag}

    def get_object(self, Bucket, Key, IfMatch=None):
        if Key not in self.objects:
            raise self.exceptions.NoSuchKey(Key)
        raw, etag = self.objects[Key]
        if IfMatch is not None and IfMatch != etag:
            raise RuntimeError("PreconditionFailed")
        return {"Body": io.BytesIO(raw), "ETag": etag}

    def head_object(self, Bucket, Key):
        response = self.get_object(Bucket, Key)
        response["Body"].close()
        return {"ETag": response["ETag"]}

    def get_paginator(self, name):
        if name != "list_objects_v2":
            raise AssertionError(name)
        return self

    def paginate(self, Bucket, Prefix):
        objects = [
            {"Key": key, "ETag": etag, "Size": len(raw)}
            for key, (raw, etag) in sorted(self.objects.items())
            if key.startswith(Prefix)
        ]
        # Deliberately use multiple pages, including an empty page.
        yield {"Contents": objects[:1]}
        yield {}
        yield {"Contents": objects[1:]}


class PrepareTests(unittest.TestCase):
    def setUp(self):
        self.s3 = FakeS3()
        self.job = BatchPreparer(self.s3, Mock(), "bucket", "workgroup", "dev")
        self.job.checkpoint = Mock(return_value=utc("2026-10-19T10:00:00Z"))
        self.now = utc("2026-10-19T10:20:00Z")
        self.owner = "arn:aws:states:us-east-2:866934333672:execution:workflow:one"

    def capture(self, stamp, rows=None, metadata=True):
        capture = utc(stamp)
        key = capture_key("station_status", capture)
        self.s3.put_object(Bucket="bucket", Key=key,
                           Body=encode({"data": {"stations": rows if rows is not None else [{"station_id": "a"}, {"station_id": "b"}]}}))
        if metadata:
            self.s3.put_object(Bucket="bucket", Key=capture_key("station_information", capture),
                               Body=encode({"data": {"stations": [{"station_id": "a", "name": "A"}]}}))
        return key

    def run_prepare(self, request=None):
        return self.job.prepare(request or {}, self.owner, self.now)

    def test_half_open_window_pagination_and_business_key_count(self):
        self.capture("2026-10-19T09:59:59Z")
        self.capture("2026-10-19T10:00:00Z", [{"station_id": "a"}, {"station_id": "a"}])
        self.capture("2026-10-19T10:10:00Z")
        self.capture("2026-10-19T10:15:00Z")
        result = self.run_prepare({"window_end": "2026-10-19T10:15:00Z"})
        self.assertEqual(result["expected_rows"], 3)
        self.assertEqual(result["capture_count"], 2)
        self.assertEqual(result["window_end"], "2026-10-19T10:10:01Z")
        manifest, _ = self.job.optional_json(result["manifest_key"])
        self.assertEqual(len(manifest["status_uris"]), 2)
        self.assertTrue(all(CONTROL in uri for uri in manifest["status_uris"]))

    def test_preview_does_not_write_or_lock(self):
        self.capture("2026-10-19T10:10:00Z")
        before = copy.deepcopy(self.s3.objects)
        self.assertEqual(self.run_prepare({"preview": True})["status"], "PREVIEW")
        self.assertEqual(before, self.s3.objects)

    def test_empty_input_releases_lock_without_moving_checkpoint(self):
        self.assertEqual(self.run_prepare()["status"], "NO_DATA")
        self.assertEqual(self.job.optional_json(LOCK_KEY)[0]["state"], "idle")
        self.job.redshift.execute_statement.assert_not_called()

    def test_competing_owner_cannot_prepare_or_release(self):
        self.job.acquire("another-execution")
        with self.assertRaisesRegex(RuntimeError, "Pipeline busy"):
            self.run_prepare()
        with self.assertRaisesRegex(RuntimeError, "another execution"):
            self.job.release(self.owner)
        self.job.checkpoint.assert_not_called()

    def test_lock_compare_and_swap_rejects_race(self):
        self.job.acquire("first")
        self.job.release("first")
        _, old_etag = self.job.optional_json(LOCK_KEY)
        self.job.acquire("second")
        with self.assertRaisesRegex(RuntimeError, "PreconditionFailed"):
            self.s3.put_object(Bucket="bucket", Key=LOCK_KEY, Body=b'{}', IfMatch=old_etag)

    def test_release_is_idempotent_but_cannot_clear_new_owner(self):
        self.job.acquire(self.owner)
        self.job.release(self.owner)
        self.job.release(self.owner)
        self.job.acquire("new-owner")
        with self.assertRaises(RuntimeError):
            self.job.release(self.owner)

    def test_duplicate_preparation_returns_same_frozen_manifest(self):
        source = self.capture("2026-10-19T10:10:00Z")
        result = self.run_prepare()
        self.s3.put_object(Bucket="bucket", Key=source, Body=b'{"changed":true}')
        self.assertEqual(self.run_prepare(), result)
        self.assertEqual(self.job.checkpoint.call_count, 1)

    def test_changed_request_cannot_reuse_prepared_batch(self):
        self.capture("2026-10-19T10:10:00Z")
        self.run_prepare()
        with self.assertRaisesRegex(ValueError, "context"):
            self.run_prepare({"window_end": "2026-10-19T10:15:00Z"})

    def test_incomplete_capture_fails_and_retains_lock(self):
        self.capture("2026-10-19T10:10:00Z", metadata=False)
        with self.assertRaises(self.s3.exceptions.NoSuchKey):
            self.run_prepare()
        self.assertEqual(self.job.optional_json(LOCK_KEY)[0]["state"], "active")

    def test_conflicting_source_rows_fail_and_retain_lock(self):
        self.capture("2026-10-19T10:10:00Z", [{"station_id": "a", "n": 1}, {"station_id": "a", "n": 2}])
        with self.assertRaisesRegex(ValueError, "Conflicting"):
            self.run_prepare()
        self.assertEqual(self.job.optional_json(LOCK_KEY)[0]["state"], "active")

    def test_invalid_station_id_is_rejected(self):
        self.capture("2026-10-19T10:10:00Z", [{"station_id": None}])
        with self.assertRaisesRegex(ValueError, "station_id"):
            self.run_prepare()

    def test_frozen_input_cannot_be_changed(self):
        self.job.freeze("frozen", b'{"a":1}')
        self.job.freeze("frozen", b'{"a":1}')
        with self.assertRaisesRegex(ValueError, "changed"):
            self.job.freeze("frozen", b'{"a":2}')

    def test_future_window_and_legacy_inputs_rejected(self):
        for request in [{"window_end": "2026-10-19T10:30:00Z"}, {"batch_id": "old"}, {"preview": "true"}]:
            with self.subTest(request=request), self.assertRaises(ValueError):
                self.run_prepare(request)

    def test_catchup_is_bounded(self):
        self.job.checkpoint.return_value = utc("2026-10-01T10:00:00Z")
        with self.assertRaisesRegex(ValueError, "14 days"):
            self.run_prepare()

    def test_source_changed_since_listing_fails(self):
        key = self.capture("2026-10-19T10:10:00Z")
        original = self.job.select

        def changed(start, end):
            selected = original(start, end)
            self.s3.put_object(Bucket="bucket", Key=key, Body=b'{"changed":true}')
            return selected

        self.job.select = changed
        with self.assertRaisesRegex(RuntimeError, "PreconditionFailed"):
            self.run_prepare()


class CheckpointTests(unittest.TestCase):
    def test_readonly_query_polls_and_requires_one_row(self):
        redshift = Mock()
        redshift.execute_statement.return_value = {"Id": "statement"}
        redshift.describe_statement.return_value = {"Status": "FINISHED"}
        redshift.get_paginator.return_value.paginate.return_value = [
            {"Records": [[{"stringValue": "2026-10-19 10:00:00"}]]}
        ]
        job = BatchPreparer(Mock(), redshift, "bucket", "workgroup", "dev")
        self.assertEqual(job.checkpoint(), utc("2026-10-19T10:00:00Z"))
        self.assertTrue(redshift.execute_statement.call_args.kwargs["Sql"].startswith("SELECT "))
        redshift.get_paginator.return_value.paginate.return_value = [{"Records": []}]
        with self.assertRaisesRegex(ValueError, "exactly one"):
            job.checkpoint()


if __name__ == "__main__":
    unittest.main()
