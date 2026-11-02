"""Prepare a bounded incremental execution input locally; makes no AWS calls."""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import re


def build_input(batch_id, start_text, end_text, reuse_silver=False, now=None):
    """Validate boundaries once and keep Glue arguments and acceptance SQL aligned."""
    if not re.fullmatch(r"[A-Za-z0-9_-]{1,64}", batch_id):
        raise ValueError("Batch ID must be 1-64 letters, digits, underscores or hyphens")
    values = []
    for text in (start_text, end_text):
        if not re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z", text):
            raise ValueError("Use UTC timestamps in YYYY-MM-DDTHH:MM:SSZ format")
        values.append(datetime.strptime(text, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc))
    start, end = values
    if start >= end:
        raise ValueError("End must be after start")
    if end > (now or datetime.now(timezone.utc)):
        raise ValueError("Close the input window before executing; end is in the future")
    # Inputs above exclude quotes/SQL syntax, so the procedure call is bounded.
    sql = f"CALL citibike_v2_lab.sp_accept_batch('{batch_id}', '{start_text}', '{end_text}');"
    return {"batch_id": batch_id, "start_at_utc": start_text,
            "end_before_utc": end_text, "reuse_silver": reuse_silver, "accept_sql": sql}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--batch-id", required=True)
    parser.add_argument("--start", required=True, help="Inclusive UTC capture timestamp")
    parser.add_argument("--end", required=True, help="Exclusive, already elapsed UTC timestamp")
    parser.add_argument("--reuse-silver", action="store_true", help="Only after published batch validation")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    value = build_input(args.batch_id, args.start, args.end, args.reuse_silver)
    # Refuse to accidentally replace a previously reviewed execution input.
    with args.output.open("x") as output:
        output.write(json.dumps(value, indent=2) + "\n")
    print(f"Prepared {args.output}; no AWS calls made")


if __name__ == "__main__":
    main()
