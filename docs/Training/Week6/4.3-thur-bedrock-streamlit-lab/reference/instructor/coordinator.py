import os
import re
import time
from datetime import datetime, timezone, timedelta

import boto3

client = boto3.client("redshift-data")
WORKGROUP = os.environ["REDSHIFT_WORKGROUP"]
DATABASE = os.environ["REDSHIFT_DATABASE"]
BATCH_RE = re.compile(r"[A-Za-z0-9_-]{1,60}\Z")


def execute_and_wait(sql, expect_records=False):
    statement = client.execute_statement(
        WorkgroupName=WORKGROUP, Database=DATABASE, Sql=sql
    )
    statement_id = statement["Id"]
    for _ in range(105):
        result = client.describe_statement(Id=statement_id)
        status = result["Status"]
        if status == "FINISHED":
            if expect_records:
                return client.get_statement_result(Id=statement_id)["Records"]
            return statement_id
        if status in ("FAILED", "ABORTED"):
            raise RuntimeError(
                f"Redshift statement {statement_id} {status}: {result.get('Error', '')}"
            )
        time.sleep(2)
    raise TimeoutError(f"Redshift statement {statement_id} did not finish within 210s")


def handler(event, context):
    phase = event.get("phase")

    if phase == "prepare":
        execution_name = event.get("execution_name", "")
        if not isinstance(execution_name, str) or not BATCH_RE.fullmatch(execution_name):
            raise ValueError("Invalid execution_name; use 1-60 letters, numbers, _ or -")
        records = execute_and_wait(
            "SELECT TO_CHAR(last_completed_utc, 'YYYY-MM-DD HH24:MI:SS') "
            "FROM public.citibike_pipeline_checkpoint "
            "WHERE pipeline_name = 'citibike_incremental'",
            expect_records=True,
        )
        if len(records) != 1 or not records[0][0].get("stringValue"):
            raise RuntimeError("Expected exactly one populated checkpoint row")
        checkpoint = datetime.strptime(
            records[0][0]["stringValue"], "%Y-%m-%d %H:%M:%S"
        ).replace(tzinfo=timezone.utc)
        start = checkpoint - timedelta(hours=2)
        end = (datetime.now(timezone.utc) - timedelta(minutes=10)).replace(
            second=0, microsecond=0
        )
        if end <= checkpoint:
            raise RuntimeError("No safe new batch window yet; wait before rerunning")
        return {
            "batch_id": execution_name,
            "start_after_utc": start.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "end_before_utc": end.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "window_end_sql": end.strftime("%Y-%m-%d %H:%M:%S"),
            "checkpoint_before": checkpoint.strftime("%Y-%m-%dT%H:%M:%SZ"),
        }

    if phase == "complete":
        batch_id = event.get("batch_id", "")
        window_end_sql = event.get("window_end_sql", "")
        if not isinstance(batch_id, str) or not BATCH_RE.fullmatch(batch_id):
            raise ValueError("Invalid batch_id")
        if not isinstance(window_end_sql, str) or not re.fullmatch(
            r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}", window_end_sql
        ):
            raise ValueError("Invalid window_end_sql")
        datetime.strptime(window_end_sql, "%Y-%m-%d %H:%M:%S")
        sql = (
            "CALL public.sp_complete_citibike_batch("
            f"'{batch_id}', TIMESTAMP '{window_end_sql}');"
        )
        statement_id = execute_and_wait(sql)
        return {"batch_id": batch_id, "redshift_statement_id": statement_id, "status": "FINISHED"}

    raise ValueError("phase must be prepare or complete")
