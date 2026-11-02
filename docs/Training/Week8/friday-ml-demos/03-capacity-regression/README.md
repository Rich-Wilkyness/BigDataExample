# Capacity regression: steps

[Demo index](../README.md) · [Theory](theory.md) · [Shared setup](../setup.md)

## Before starting

Use the [local Citi Bike export](../data-preparation.md). No SQL database or AWS credentials are required after export. The default file locations are resolved automatically; CSV and Parquet overrides are described in [setup](../setup.md).

## Finalized steps

1. From `friday-ml-demos`, activate the shared environment and install this demo's packages:

   ```bash
   source .venv/bin/activate
   python -m pip install -r 03-capacity-regression/requirements.txt
   cd 03-capacity-regression
   ```

2. Run the recovered script:

   ```bash
   python regression.py
   ```

3. Read MAE and R² in the terminal. Inspect the station-capacity map and actual-versus-predicted scatter plot. Close the plot window when finished.

4. To compare model complexity, change `max_depth` from `10` to `2`, rerun, and compare results. A later run overwrites the PNG.

## Files and outputs

- `station-view.sql`: retained SQL reference; not required for this workflow.
- `regression.py`: complete training, evaluation, and plotting script.
- Generated locally: `regression_results.png`.

## Source and verification

Recovered from the final “Create regression.py” section in `chat.md`; metric explanations come from `chat2.md`. Corrections are incorporated into this guide; troubleshooting exchanges are omitted. These examples now use the local AWS-derived export. See [verification](../verification.md) for current executed checks and their limits.

## Learning checkpoints

**Before running:** Use the local export and this demo’s Python packages; no service or API key is required.

**Expected output:** A terminal MAE/R² pair and `regression_results.png`. Local verification produced approximately MAE 6.32 docks and R² 0.637 on the 2,483 usable stations; these are not the teacher’s earlier values.

**Interpret it:** The split protects held-out examples from fitting. MAE is average error in docks; R² is relative squared-error performance.

**Check your understanding:**

1. Which statement trains the model, and which only makes predictions?
2. Does an average error of six docks guarantee that every prediction is within six?

Record your observed result before moving to another demo. Sample/reported metrics describe their stated data and environment, not a required answer for your machine.
