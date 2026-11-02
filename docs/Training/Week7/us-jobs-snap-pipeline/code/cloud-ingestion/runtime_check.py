"""
Check the Cloud Run runtime identity and secret configuration.

Writes one small, nonsecret object to the existing Bronze bucket.
Never prints or saves the BLS key.
"""

from datetime import datetime, timezone
import json
import os
from uuid import uuid4

from google.cloud import storage


def main():
    if not os.environ.get("CLOUD_RUN_JOB"):
        raise RuntimeError("Run this check as a Cloud Run Job")

    # Cloud Run injects this value from Secret Manager at startup.
    if not os.environ.get("BLS_API_KEY", "").strip():
        raise RuntimeError("BLS_API_KEY was not injected")

    project_id = os.environ["PROJECT_ID"]
    bucket_name = os.environ["BRONZE_BUCKET"]

    now = datetime.now(timezone.utc)
    run_id = uuid4().hex
    object_name = (
        "practice/runtime-check/"
        f"ingestion_date={now.date().isoformat()}/"
        f"run_id={run_id}/check.json"
    )

    record = {
        "checked_at": now.isoformat(),
        "job": os.environ["CLOUD_RUN_JOB"],
        "execution": os.environ.get("CLOUD_RUN_EXECUTION"),
        "bls_key_present": True,
    }

    # Application Default Credentials use the attached service account.
    # No downloaded credential file is needed.
    client = storage.Client(project=project_id)
    blob = client.bucket(bucket_name).blob(object_name)

    # Create only: refuse to overwrite an existing object.
    blob.upload_from_string(
        json.dumps(record, indent=2),
        content_type="application/json",
        if_generation_match=0,
        timeout=60,
    )

    print(json.dumps({
        "status": "passed",
        "secret_injected": True,
        "object_created": f"gs://{bucket_name}/{object_name}",
    }))


if __name__ == "__main__":
    main()