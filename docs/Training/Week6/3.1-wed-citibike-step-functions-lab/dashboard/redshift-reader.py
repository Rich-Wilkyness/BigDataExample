"""Bounded SELECT through the Redshift Data API; no pipeline writes."""
import time

import boto3
from botocore.config import Config


def decode_rows(response):
    """Translate tagged Data API field values into ordinary Python dictionaries."""
    names = [column["name"] for column in response["ColumnMetadata"]]
    rows = []
    for record in response["Records"]:
        values = [None if field.get("isNull") else next(iter(field.values())) for field in record]
        rows.append(dict(zip(names, values)))
    return rows


def read_summary(region, workgroup, database, timeout_seconds=60):
    """Submit fixed read-only SQL, wait for completion, and fetch every result page."""
    client = boto3.Session(region_name=region).client(
        "redshift-data",
        config=Config(connect_timeout=5, read_timeout=10,
                      retries={"mode": "standard", "total_max_attempts": 3}),
    )
    response = client.execute_statement(
        WorkgroupName=workgroup,
        Database=database,
        Sql=("SELECT snapshot_timestamp, operational_stations, bikes_available, "
             "docks_available, empty_stations, full_stations "
             "FROM citibike_v2_lab.station_availability_summary "
             "ORDER BY snapshot_timestamp DESC LIMIT 1000"),
    )
    statement_id = response["Id"]
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        status = client.describe_statement(Id=statement_id)
        if status["Status"] == "FINISHED":
            rows = []
            for page in client.get_paginator("get_statement_result").paginate(Id=statement_id):
                rows.extend(decode_rows(page))
            return rows, statement_id
        if status["Status"] in {"FAILED", "ABORTED"}:
            raise RuntimeError(f"Statement {statement_id}: {status.get('Error', status['Status'])}")
        time.sleep(1)
    raise TimeoutError(f"Stopped polling statement {statement_id}; SQL may still be running")
