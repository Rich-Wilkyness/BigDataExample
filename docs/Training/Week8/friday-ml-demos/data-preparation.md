# Prepare Citi Bike data as local files

[Demo index](README.md) · [Local requirements](local-requirements.md)

## What is already available here

A read-only inspection of the existing AWS account found matching raw GBFS snapshots captured at `20261019T173257Z`. Both were downloaded and converted locally. The exported station network contains 2,519 station-information rows and 2,519 station-status rows; all IDs match one-to-one. Capacity-based demos retain 2,483 positive-capacity stations. The source's zero capacities remain unchanged in the export and are excluded only by the model task's filter.

Files live under `data/raw/week8-friday-citibike/` at the repository root. `stations.csv` is 230,015 bytes and `station-status.csv` is 121,420 bytes in this export. This is one saved network snapshot, not the entire AWS history, a trip dataset, or enough observations to evaluate forecasting. Demo 06 continues to generate explicitly synthetic hourly data.

The original feed update times are stored in `provenance.json`. The raw files were captured on October 19 and exported locally on November 1, 2026 UTC (October 31 in the user's timezone). Current availability can differ from these saved values.

## Schema and ownership

| File | Grain | Columns |
| --- | --- | --- |
| `stations.csv` | One row per station in the information snapshot | `station_id`, `station_name`, `latitude`, `longitude`, `capacity`, `station_type`, `region_id` |
| `station-status.csv` | One row per station in the status snapshot | `station_id`, `num_bikes_available`, `num_docks_available`, `last_reported` |
| `provenance.json` | One export | Original payload hashes, feed metadata, output sizes/hashes, and source policy |

The code preserves identifiers as strings, checks duplicate keys, and validates numeric values. It does not replace unknown values with zero or infer capacity from available bikes plus docks. The station reader accepts CSV or Parquet; Parquet is optional and requires PyArrow, already included in the full local requirements.

## Recreate the existing export from S3

Use your existing authorized AWS profile/credential chain; do not put access keys in code. From `friday-ml-demos`, with the shared environment active:

```bash
python -m pip install boto3 pandas
python export-station-data.py \
  --information 's3://richard-wilkerson-citibike-pipeline-866934333672-us-east-2-an/bronze/citibike/station_information/year=2026/month=10/day=19/hour=17/station_information_20261019T173257Z.json' \
  --status 's3://richard-wilkerson-citibike-pipeline-866934333672-us-east-2-an/bronze/citibike/station_status/year=2026/month=10/day=19/hour=17/station_status_20261019T173257Z.json'
```

If you use a named profile, add `--profile YOUR_EXISTING_PROFILE`. The script reads those exact objects and writes local files only. It does not start Glue, Redshift, or another paid compute service. S3 request/data-transfer charges may apply under the account's existing terms. No upload, IAM change, new deployment, or database is required.

For already downloaded JSON files, supply their local paths instead. No AWS SDK or credentials are needed in that mode:

```bash
python export-station-data.py \
  --information '/absolute/path/to/station_information.json' \
  --status '/absolute/path/to/station_status.json'
```

The downloader used for this workspace was the connected AWS tool; the conversion script was executed against the downloaded JSON. Its local-file conversion and downstream readers were verified. Its optional direct Boto3 download branch has not been executed against AWS here.

## Keep working data local

This dataset remains in the Git-ignored `data/raw/` area. Citi Bike's [data-use policy](https://citibikenyc.com/data-sharing-policy) allows analysis but restricts standalone dataset publication. The repository versions the conversion and lessons rather than redistributing the saved network data. The [official system-data page](https://citibikenyc.com/system-data) identifies the GBFS feed. No rider/customer records, credentials, or presigned URLs are included in the export.

## Check before proceeding

1. Run demo 01 and confirm it prints 2,519 loaded stations for this saved export.
2. Run demo 02 and confirm 2,519 matched station IDs. This is a local snapshot join, not live forecasting.
3. Run demo 03 and confirm it uses 2,483 rows after capacity filtering. Your metrics can differ from the teacher's because this dataset and package versions differ.
