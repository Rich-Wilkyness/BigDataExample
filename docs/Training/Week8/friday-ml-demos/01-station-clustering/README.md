# Station clustering: steps

[Demo index](../README.md) · [Theory](theory.md) · [Shared setup](../setup.md)

## Before starting

Use the [local Citi Bike export](../data-preparation.md). No SQL database or AWS credentials are required after export. The default file locations are resolved automatically; CSV and Parquet overrides are described in [setup](../setup.md).

## Finalized steps

1. From `friday-ml-demos`, activate the shared environment and install this demo's packages:

   ```bash
   source .venv/bin/activate
   python -m pip install -r 01-station-clustering/requirements.txt
   cd 01-station-clustering
   ```

2. Run the recovered script:

   ```bash
   python clustering.py
   ```

3. Read the station counts for clusters 0–4 and the mean latitude/longitude for each group.

## Files and outputs

- `station-view.sql`: retained historical SQL reference; not used by the current file-based workflow.
- `load_citibike.py`: reads the local station export through the shared file contract.
- `clustering.py`: fits five clusters and prints summaries.
- No output file is saved.

## Source and verification

Recovered from `chat.md`, “Create a clean station table,” “Load the PostgreSQL station view,” and “Start with clustering.” Corrections are incorporated into this guide; troubleshooting exchanges are omitted. These examples now use the local AWS-derived export. See [verification](../verification.md) for current executed checks and their limits.

## Learning checkpoints

**Before running:** The exported station file exists; no database or running server is needed.

**Expected output:** For the current export: `Loaded 2519 stations`, then five cluster counts totaling 2,519. Cluster numbers/counts are model output, not fixed neighborhood names.

**Interpret it:** The algorithm groups coordinates without supplied target labels.

**Check your understanding:**

1. Why would changing the number of clusters change the result?
2. Does cluster 4 mean a better or larger station than cluster 0?

Record your observed result before moving to another demo. Sample/reported metrics describe their stated data and environment, not a required answer for your machine.
