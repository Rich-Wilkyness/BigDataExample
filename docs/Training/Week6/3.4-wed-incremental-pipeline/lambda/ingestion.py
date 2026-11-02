"""Download a complete capture, publish its feeds, then create its ready marker."""

import json
import os
import urllib.request
from datetime import datetime, timezone

import boto3
from botocore.config import Config

GBFS_URL = "https://gbfs.citibikenyc.com/gbfs/gbfs.json"
FEEDS = {"station_information", "station_status", "system_information"}


def get_json(url):
    request = urllib.request.Request(
        url, headers={"User-Agent": "NYC-DOT-DataEngineering-Demo/1.0"},
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.loads(response.read())


def capture(s3, bucket, download=get_json, now=None):
    snapshot = now or datetime.now(timezone.utc)
    stamp = snapshot.strftime("%Y%m%dT%H%M%SZ")
    discovery = download(GBFS_URL)
    urls = {
        feed["name"]: feed["url"]
        for feed in discovery["data"]["en"]["feeds"]
        if feed["name"] in FEEDS
    }
    if FEEDS - urls.keys():
        raise ValueError("Required GBFS feeds are missing")
    # Fetch every feed first. Any failed download leaves no published capture.
    documents = {"gbfs_discovery": discovery}
    documents.update({name: download(urls[name]) for name in sorted(FEEDS)})
    uploaded = []
    for name, document in documents.items():
        key = snapshot.strftime(
            f"bronze/citibike/{name}/year=%Y/month=%m/day=%d/hour=%H/"
            f"{name}_%Y%m%dT%H%M%SZ.json"
        )
        s3.put_object(
            Bucket=bucket, Key=key, Body=json.dumps(document).encode(),
            ContentType="application/json", IfNoneMatch="*",
        )
        uploaded.append(key)
    marker_key = f"bronze/citibike/completed/capture_{stamp}.json"
    marker = {
        "version": 1, "bucket": bucket, "capture_id": stamp,
        "snapshot_time": snapshot.isoformat(), "objects": uploaded,
    }
    # This is the only object prefix matched by the EventBridge rule.
    s3.put_object(
        Bucket=bucket, Key=marker_key, Body=json.dumps(marker).encode(),
        ContentType="application/json", IfNoneMatch="*",
    )
    return {
        "statusCode": 200, "snapshot_time": snapshot.isoformat(),
        "capture_id": stamp, "completion_key": marker_key,
        "data_files_uploaded": len(uploaded), "files_uploaded": len(uploaded) + 1,
        "objects": uploaded + [marker_key],
    }


def lambda_handler(event, context):
    config = Config(
        connect_timeout=5, read_timeout=15,
        retries={"mode": "standard", "total_max_attempts": 3},
    )
    s3 = boto3.Session(region_name=os.environ["AWS_REGION"]).client("s3", config=config)
    result = capture(s3, os.environ["CITIBIKE_BUCKET"])
    print(json.dumps(result))
    return result
