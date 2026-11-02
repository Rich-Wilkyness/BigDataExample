"""Convert two existing GBFS snapshots to small local CSVs and provenance.

Supply downloaded JSON files, or exact S3 object URIs with --from-s3. This
reads existing objects only. It never writes AWS resources or starts compute.
"""

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

import pandas as pd

DEFAULT_OUTPUT = Path(__file__).resolve().parents[4] / "data/raw/week8-friday-citibike"


def read_source(source, s3=None):
    if source.startswith("s3://"):
        parsed = urlparse(source)
        # The caller creates one client and reuses it for the two bounded reads.
        response = s3.get_object(Bucket=parsed.netloc, Key=parsed.path.lstrip("/"))
        with response["Body"] as body:
            content = body.read()
    else:
        content = Path(source).read_bytes()
    payload = json.loads(content)
    rows = payload["data"]["stations"]
    if not isinstance(rows, list) or not rows:
        raise ValueError(f"No stations in {source}")
    return pd.DataFrame(rows), {
        "source": source, "sha256": hashlib.sha256(content).hexdigest(),
        "last_updated": payload.get("last_updated"), "version": payload.get("version"),
    }


def convert(information, status, output, *, s3=None):
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    info, info_source = read_source(information, s3)
    availability, status_source = read_source(status, s3)
    info = info.rename(columns={"name": "station_name", "lat": "latitude", "lon": "longitude"})
    # Keep the complete station network from this snapshot, not every repeated
    # historical metadata capture. Do not manufacture a history from one feed.
    info = info[["station_id", "station_name", "latitude", "longitude", "capacity", "station_type", "region_id"]].copy()
    availability = availability[["station_id", "num_bikes_available", "num_docks_available", "last_reported"]].copy()
    for frame in (info, availability):
        if frame["station_id"].isna().any() or frame["station_id"].duplicated().any():
            raise ValueError("Snapshot has missing or repeated station IDs; inspect the source instead of silently dropping rows.")
        frame.sort_values("station_id", inplace=True)
    paths = [output / "stations.csv", output / "station-status.csv"]
    for frame, path in zip((info, availability), paths):
        frame.to_csv(path, index=False)
    manifest = {
        "exported_at_utc": datetime.now(timezone.utc).isoformat(),
        "grain": "one row per station in each supplied snapshot",
        "station_information": {**info_source, "rows": len(info)},
        "station_status": {**status_source, "rows": len(availability)},
        "outputs": {path.name: {"bytes": path.stat().st_size, "sha256": hashlib.sha256(path.read_bytes()).hexdigest()} for path in paths},
        "data_use_policy": "https://citibikenyc.com/data-sharing-policy",
    }
    (output / "provenance.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(json.dumps(manifest, indent=2))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--information", required=True, help="Local JSON path or exact s3:// object URI")
    parser.add_argument("--status", required=True, help="Matching station-status JSON path or URI")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--profile", help="Existing AWS profile; omit to use the normal credential chain")
    parser.add_argument("--region", default="us-east-2")
    args = parser.parse_args()
    s3 = None
    if any(value.startswith("s3://") for value in (args.information, args.status)):
        import boto3

        # No access keys in code; use an existing authenticated profile/session.
        s3 = boto3.Session(profile_name=args.profile, region_name=args.region).client("s3")
    convert(args.information, args.status, args.output, s3=s3)


if __name__ == "__main__":
    main()
