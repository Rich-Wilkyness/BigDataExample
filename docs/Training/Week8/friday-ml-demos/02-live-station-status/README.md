# Live station status: steps

[Demo index](../README.md) · [Theory](theory.md) · [Shared setup](../setup.md)

## Before starting

Use the [local Citi Bike export](../data-preparation.md). No SQL database or AWS credentials are required after export. The default file locations are resolved automatically; CSV and Parquet overrides are described in [setup](../setup.md).

## Finalized steps

1. From `friday-ml-demos`, activate the shared environment and install this demo's packages:

   ```bash
   source .venv/bin/activate
   python -m pip install -r 02-live-station-status/requirements.txt
   cd 02-live-station-status
   ```

2. Run the recovered script:

   ```bash
   python live_status.py
   ```

3. Read the API record count, matched station count, and sample bike/dock availability. The script finishes after one request.

## Files and outputs

- `load_citibike.py`: reads the exported station file; `station-view.sql` is an unused historical reference.
- `live_status.py`: downloads status and joins it to metadata.
- No output file is saved. The default status mode reads a saved snapshot; `python live_status.py --live` explicitly requests the public API.

## Source and verification

Recovered from `chat.md`, “Add live station availability.” Corrections are incorporated into this guide; troubleshooting exchanges are omitted. These examples now use the local AWS-derived export. See [verification](../verification.md) for current executed checks and their limits.

## Learning checkpoints

**Before running:** The two local files are from the matching saved capture. Leave `--live` off for the first walkthrough.

**Expected output:** For the supplied export: `Status records: 2519` and `Matched stations: 2519`, plus a sample availability table.

**Interpret it:** The join enriches station metadata; it does not fit a model or collect historical observations.

**Check your understanding:**

1. Why is station_id the join key rather than station name?
2. Does one saved availability snapshot let us evaluate tomorrow’s availability?

Record your observed result before moving to another demo. Sample/reported metrics describe their stated data and environment, not a required answer for your machine.
