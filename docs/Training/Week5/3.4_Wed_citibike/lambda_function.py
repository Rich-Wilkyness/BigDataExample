import json
import os
import urllib.request
from datetime import datetime, timezone

import boto3

GBFS_URL = "https://gbfs.citibikenyc.com/gbfs/gbfs.json"
BUCKET = os.environ["CITIBIKE_BUCKET"]
WANTED_FEEDS = {"station_information", "station_status", "system_information"}
s3 = boto3.client("s3")


def get_json(url):
    print(f"Downloading: {url}")
    request = urllib.request.Request(
        url, headers={"User-Agent": "NYC-DOT-DataEngineering-Demo/1.0"}
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.loads(response.read())


def write_json_to_s3(dataset_name, data, snapshot_time):
    key = (
        f"bronze/citibike/{dataset_name}/"
        f"year={snapshot_time:%Y}/month={snapshot_time:%m}/"
        f"day={snapshot_time:%d}/hour={snapshot_time:%H}/"
        f"{dataset_name}_{snapshot_time:%Y%m%dT%H%M%SZ}.json"
    )
    body = json.dumps(data, separators=(",", ":")).encode("utf-8")
    s3.put_object(Bucket=BUCKET, Key=key, Body=body, ContentType="application/json")
    print(f"Uploaded {len(body):,} bytes -> s3://{BUCKET}/{key}")
    return key


def lambda_handler(event, context):
    snapshot_time = datetime.now(timezone.utc)
    discovery = get_json(GBFS_URL)
    feed_urls = {
        feed["name"]: feed["url"]
        for feed in discovery["data"]["en"]["feeds"]
        if feed["name"] in WANTED_FEEDS
    }
    missing = WANTED_FEEDS - set(feed_urls)
    if missing:
        raise RuntimeError(f"Missing expected feeds: {missing}")

    uploaded = [write_json_to_s3("gbfs_discovery", discovery, snapshot_time)]
    for dataset_name, url in feed_urls.items():
        uploaded.append(write_json_to_s3(dataset_name, get_json(url), snapshot_time))

    result = {
        "statusCode": 200,
        "snapshot_time": snapshot_time.isoformat(),
        "files_uploaded": len(uploaded),
        "objects": uploaded,
    }
    print(json.dumps(result))
    return result