# Time-series regression: steps

[Demo index](../README.md) · [Theory](theory.md) · [Shared setup](../setup.md)

## Before starting

This demo generates its own synthetic data. It does not need PostgreSQL, Kafka, MLflow, or historical Citi Bike files.

## Finalized steps

1. From `friday-ml-demos`, activate the shared environment and install this demo's packages:

   ```bash
   source .venv/bin/activate
   python -m pip install -r 06-timeseries-regression/requirements.txt
   cd 06-timeseries-regression
   ```

2. Run the recovered script:

   ```bash
   python timeseries_regression.py
   ```

3. Compare the printed MAE and R² for Linear Regression and Random Forest. Read the fitted slope per hour/day and the correlation with elapsed time.

4. Inspect the full-series trend plot and the predictions on the held-out future period. Close the plot window when finished.

## Files and outputs

- `timeseries_regression.py`: generates data, trains two models, evaluates, and plots.
- Generated locally: `timeseries_regression.png`.
- The synthetic DataFrame is held in memory; no input CSV is required.

## Source and verification

Recovered from `chat2.md`, “Create timeseries_regression.py.” Corrections are incorporated into this guide; troubleshooting exchanges are omitted. The script was executed locally with a noninteractive plotting backend. See [verification](../verification.md) for measured outputs and limits.

## Learning checkpoints

**Before running:** No external data or services are needed; NumPy/pandas generate the observations.

**Expected output:** Two model metric pairs, slope/correlation, and `timeseries_regression.png`. Local verification gave MAE roughly 2.84 for the linear model and 1.99 for the forest on the generated future period.

**Interpret it:** The target is explicitly simulated. Earlier rows train; later rows evaluate. Repeating cycles and the overall trend are different patterns.

**Check your understanding:**

1. Why does shuffling the rows change the evaluation question?
2. Why can a forest learn daily patterns yet struggle to extrapolate a continued downward trend?

Record your observed result before moving to another demo. Sample/reported metrics describe their stated data and environment, not a required answer for your machine.
