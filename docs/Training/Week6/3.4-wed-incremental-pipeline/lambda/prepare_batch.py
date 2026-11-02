"""Prepare bounded, frozen Citi Bike batches; never move warehouse progress."""

import hashlib
import json
import os
import re
import time
from datetime import datetime, timedelta, timezone

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError

UTC = timezone.utc
CONTROL = "control/citibike/incremental/"
LOCK_KEY = CONTROL + "active.json"
STAMP = "%Y-%m-%dT%H:%M:%SZ"
FILENAME_STAMP = "%Y%m%dT%H%M%SZ"
MAX_FILES = 128
MAX_BYTES = 64 * 1024 * 1024
MAX_OBJECT_BYTES = 8 * 1024 * 1024
MAX_ROWS = 200_000


class PipelineBusyError(RuntimeError):
    """A different execution owns the run; only preparation may be attempted later."""


def utc(value):
    return datetime.strptime(value, STAMP).replace(tzinfo=UTC)


def encode(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode()


def capture_key(feed, capture):
    return capture.strftime(
        f"bronze/citibike/{feed}/year=%Y/month=%m/day=%d/hour=%H/"
        f"{feed}_%Y%m%dT%H%M%SZ.json"
    )


class BatchPreparer:
    def __init__(self, s3, redshift, bucket, workgroup, database):
        self.s3 = s3
        self.redshift = redshift
        self.bucket = bucket
        self.workgroup = workgroup
        self.database = database

    def read(self, key, **conditions):
        response = self.s3.get_object(Bucket=self.bucket, Key=key, **conditions)
        with response["Body"] as body:
            raw = body.read(MAX_OBJECT_BYTES + 1)
        if len(raw) > MAX_OBJECT_BYTES:
            raise ValueError(f"Object exceeds preparation size limit: {key}")
        return raw, response["ETag"]

    def optional_json(self, key):
        try:
            raw, etag = self.read(key)
        except self.s3.exceptions.NoSuchKey:
            return None, None
        return json.loads(raw), etag

    def acquire(self, owner):
        lock, etag = self.optional_json(LOCK_KEY)
        if lock and lock["state"] == "active":
            if lock["owner"] == owner:
                return
            raise PipelineBusyError(f"Pipeline busy; active owner: {lock['owner']}")
        conditions = {"IfMatch": etag} if etag else {"IfNoneMatch": "*"}
        self.s3.put_object(
            Bucket=self.bucket, Key=LOCK_KEY,
            Body=encode({"state": "active", "owner": owner}),
            ContentType="application/json", **conditions,
        )

    def release(self, owner):
        lock, etag = self.optional_json(LOCK_KEY)
        if lock and lock["state"] == "idle" and lock["released_by"] == owner:
            return {"status": "RELEASED"}
        if not lock or lock["state"] != "active" or lock["owner"] != owner:
            raise RuntimeError("Cannot release a lock owned by another execution")
        self.s3.put_object(
            Bucket=self.bucket, Key=LOCK_KEY, IfMatch=etag,
            Body=encode({"state": "idle", "released_by": owner}),
            ContentType="application/json",
        )
        return {"status": "RELEASED"}

    def checkpoint(self):
        result = self.redshift.execute_statement(
            WorkgroupName=self.workgroup, Database=self.database,
            Sql=("SELECT last_completed_utc FROM "
                 "public.richard_citibike_pipeline_checkpoint "
                 "WHERE pipeline_name = 'richard-citibike'"),
        )
        statement = result["Id"]
        deadline = time.monotonic() + 90
        while time.monotonic() < deadline:
            status = self.redshift.describe_statement(Id=statement)
            if status["Status"] == "FINISHED":
                break
            if status["Status"] in {"FAILED", "ABORTED"}:
                raise RuntimeError(status.get("Error", "Checkpoint read failed"))
            time.sleep(2)
        else:
            self.redshift.cancel_statement(Id=statement)
            raise TimeoutError("Checkpoint read exceeded 90 seconds")
        rows = []
        for page in self.redshift.get_paginator("get_statement_result").paginate(Id=statement):
            rows.extend(page["Records"])
        if len(rows) != 1 or "stringValue" not in rows[0][0]:
            raise ValueError("Expected exactly one non-null checkpoint")
        value = datetime.fromisoformat(rows[0][0]["stringValue"]).replace(tzinfo=UTC)
        if value.microsecond:
            raise ValueError("Checkpoint must use whole capture seconds")
        return value

    def select(self, start, end):
        if end <= start:
            return []
        if end - start > timedelta(days=14):
            raise ValueError("Preparation is bounded to 14 days; use a smaller window_end")
        day = start.replace(hour=0, minute=0, second=0, microsecond=0)
        objects = []
        paginator = self.s3.get_paginator("list_objects_v2")
        while day < end:
            prefix = day.strftime("bronze/citibike/station_status/year=%Y/month=%m/day=%d/")
            for page in paginator.paginate(Bucket=self.bucket, Prefix=prefix):
                for obj in page.get("Contents", []):
                    match = re.search(r"station_status_(\d{8}T\d{6}Z)\.json$", obj["Key"])
                    if not match:
                        continue
                    capture = datetime.strptime(match[1], FILENAME_STAMP).replace(tzinfo=UTC)
                    if start <= capture < end:
                        if obj["Key"] != capture_key("station_status", capture):
                            raise ValueError("Unexpected capture path")
                        objects.append((capture, obj))
                        if len(objects) > MAX_FILES:
                            raise ValueError("More than 128 captures; use a smaller window_end")
            day += timedelta(days=1)
        objects.sort(key=lambda pair: pair[0])
        if sum(obj["Size"] for _, obj in objects) > MAX_BYTES:
            raise ValueError("Source batch exceeds 64 MiB; use a smaller window_end")
        return objects

    def freeze(self, key, raw):
        # Never overwrite a previously frozen object, even on a preparation retry.
        existing, _ = self.optional_json(key)
        value = json.loads(raw)
        if existing is not None:
            if existing != value:
                raise ValueError("Frozen batch input changed; inspect retained lock")
            return
        self.s3.put_object(
            Bucket=self.bucket, Key=key, Body=raw, IfNoneMatch="*",
            ContentType="application/json",
        )

    def completion(self, key):
        match = re.fullmatch(r"bronze/citibike/completed/capture_(\d{8}T\d{6}Z)\.json", key)
        if not match:
            raise ValueError("Invalid completion_key")
        marker, _ = self.optional_json(key)
        if not marker or marker.get("version") != 1 or marker.get("bucket") != self.bucket:
            raise ValueError("Completion marker is missing or belongs to another bucket")
        capture = datetime.strptime(match[1], FILENAME_STAMP).replace(tzinfo=UTC)
        actual = datetime.fromisoformat(marker["snapshot_time"])
        if (actual.tzinfo is None or actual.astimezone(UTC).replace(microsecond=0) != capture
                or marker.get("capture_id") != match[1]):
            raise ValueError("Completion marker capture identity does not match its key")
        expected = {capture_key(feed, capture) for feed in (
            "gbfs_discovery", "station_information", "station_status", "system_information",
        )}
        if (not isinstance(marker.get("objects"), list)
                or set(marker["objects"]) != expected or len(marker["objects"]) != 4):
            raise ValueError("Completion marker must list exactly the four capture objects")
        for object_key in marker["objects"]:
            self.s3.head_object(Bucket=self.bucket, Key=object_key)
        return capture

    def prepare(self, request, owner, now=None):
        if not isinstance(request, dict) or set(request) - {"window_end", "preview", "completion_key"}:
            raise ValueError("Supply {} or optional window_end/preview/completion_key")
        if "completion_key" in request and "window_end" in request:
            raise ValueError("Completion events own their exclusive window_end")
        preview = request.get("preview", False)
        if not isinstance(preview, bool):
            raise ValueError("preview must be a boolean")
        completion = self.completion(request["completion_key"]) if "completion_key" in request else None
        batch = "auto_" + hashlib.sha256(owner.encode()).hexdigest()[:32]
        manifest_key = CONTROL + f"batches/{batch}/manifest.json"
        if not preview:
            try:
                self.acquire(owner)
            except ClientError as error:
                # These S3 conditional-write errors have no modeled SDK exception.
                # Only acquisition races are retryable; source/read conflicts fail.
                if error.response.get("Error", {}).get("Code") in {
                    "PreconditionFailed", "ConditionalRequestConflict",
                }:
                    raise PipelineBusyError("Pipeline busy; lock acquisition raced") from error
                raise
            existing, _ = self.optional_json(manifest_key)
            if existing:
                if existing["owner"] != owner or existing["request"] != request:
                    raise ValueError("Prepared batch context does not match execution")
                return existing["result"]
        start = self.checkpoint()
        now = now or datetime.now(UTC)
        # Exclude the current capture second; callers await ingestion success first.
        cutoff = now.replace(microsecond=0)
        end = utc(request["window_end"]) if "window_end" in request else cutoff
        if completion is not None:
            end = completion + timedelta(seconds=1)
        if (completion is None and end > cutoff) or (completion is not None and completion > cutoff):
            raise ValueError("Requested capture window cannot be in the future")
        selected = self.select(start, end)
        if not selected:
            if not preview:
                self.release(owner)
            return {"status": "NO_DATA", "checkpoint_before": start.strftime(STAMP)}
        source_records = []
        frozen_uris = []
        total = 0
        # Read each selected file conditionally, count business keys, and freeze it.
        for capture, obj in selected:
            if completion is not None:
                # Event-triggered catch-up must not accept an unfinished capture.
                marker_key = f"bronze/citibike/completed/capture_{capture.strftime(FILENAME_STAMP)}.json"
                self.completion(marker_key)
            raw, _ = self.read(obj["Key"], IfMatch=obj["ETag"])
            stations = json.loads(raw)["data"]["stations"]
            if not isinstance(stations, list) or not stations:
                raise ValueError("Empty or malformed station capture")
            seen = {}
            for row in stations:
                station = row.get("station_id")
                if not isinstance(station, (str, int)) or isinstance(station, bool) or not str(station).strip():
                    raise ValueError("Invalid station_id")
                station = str(station)
                if station in seen and seen[station] != row:
                    raise ValueError("Conflicting station observations in source capture")
                seen[station] = row
            total += len(seen)
            if total > MAX_ROWS:
                raise ValueError("Batch exceeds 200,000 observations; use a smaller window_end")
            # Check the corresponding metadata exists for every selected capture.
            info_key = capture_key("station_information", capture)
            self.s3.head_object(Bucket=self.bucket, Key=info_key)
            frozen = CONTROL + f"batches/{batch}/status/station_status_{capture.strftime(FILENAME_STAMP)}.json"
            if not preview:
                self.freeze(frozen, raw)
            frozen_uris.append(f"s3://{self.bucket}/{frozen}")
            source_records.append({"key": obj["Key"], "etag": obj["ETag"], "rows": len(seen)})
        latest = selected[-1][0]
        metadata_source = capture_key("station_information", latest)
        metadata_raw, metadata_etag = self.read(metadata_source)
        metadata = json.loads(metadata_raw)["data"]["stations"]
        if not isinstance(metadata, list) or not metadata:
            raise ValueError("Empty or malformed station metadata")
        metadata_key = CONTROL + f"batches/{batch}/station_information.json"
        if not preview:
            self.freeze(metadata_key, metadata_raw)
        result = {
            "status": "PREVIEW" if preview else "READY",
            "batch_id": batch,
            "window_start": start.strftime(STAMP),
            "window_end": (latest + timedelta(seconds=1)).strftime(STAMP),
            "checkpoint_before": start.strftime(STAMP),
            "expected_rows": total,
            "manifest_key": manifest_key,
            "capture_count": len(selected),
        }
        if not preview:
            manifest = {
                "version": 1, "owner": owner, "request": request, "result": result,
                "status_uris": frozen_uris,
                "metadata_uri": f"s3://{self.bucket}/{metadata_key}",
                "source_objects": source_records,
                "metadata_source": {"key": metadata_source, "etag": metadata_etag},
            }
            self.freeze(manifest_key, encode(manifest))
        return result


def lambda_handler(event, context):
    config = Config(
        connect_timeout=5, read_timeout=15,
        retries={"mode": "standard", "total_max_attempts": 3},
    )
    session = boto3.Session(region_name=os.environ["AWS_REGION"])
    preparer = BatchPreparer(
        session.client("s3", config=config),
        session.client("redshift-data", config=config),
        os.environ["BUCKET"], os.environ["REDSHIFT_WORKGROUP"],
        os.environ["REDSHIFT_DATABASE"],
    )
    owner = event["execution_id"]
    prefix = os.environ["EXECUTION_ARN_PREFIX"]
    if not isinstance(owner, str) or not owner.startswith(prefix):
        raise ValueError("Expected an execution ARN from Richard's workflow")
    action = event.get("action", "prepare")
    if action == "release":
        return preparer.release(owner)
    if action != "prepare":
        raise ValueError("Unknown action")
    try:
        return preparer.prepare(event.get("request", {}), owner)
    except PipelineBusyError:
        return {"status": "BUSY"}
