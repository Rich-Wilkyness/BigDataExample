# MLflow regression serving: steps

[Demo index](../README.md) · [Theory](theory.md) · [Shared setup](../setup.md)

## Before starting

Use the [local Citi Bike export](../data-preparation.md). No SQL database or AWS credentials are required after export. The default file locations are resolved automatically; CSV and Parquet overrides are described in [setup](../setup.md). Install the requirements below, then start the local MLflow tracking server before running the script.

## Finalized steps

1. From `friday-ml-demos`, activate the shared environment and install this demo's packages:

   ```bash
   source .venv/bin/activate
   python -m pip install -r 05-mlflow-regression-serving/requirements.txt
   cd 05-mlflow-regression-serving
   ```

2. Run the recovered script:

   ```bash
   python regression.py
   ```

3. Close the plot window. Open `http://127.0.0.1:5000`, select `citibike-regression`, and inspect parameters `n_estimators`, `max_depth`, `random_state`, metrics `mae` and `r2`, and the logged model. Under Models, find `citibike_capacity_predictor` and its versions. After reviewing a candidate, explicitly assign its `champion` alias in the registry UI.

4. To compare runs, change both the model's `max_depth` and its logged `max_depth` value, rerun, then select the successful runs in the experiment and choose Compare. Compare MAE and R² on the same data. The script no longer moves `champion` automatically. Select the intended version explicitly in the registry before serving. These repeated capacity runs remain an exploratory comparison; demo 07 implements a separate fixed validation set and reserved final test.

5. In a new terminal, from `friday-ml-demos`, start the model server:

   ```bash
   source .venv/bin/activate
   export MLFLOW_TRACKING_URI=http://127.0.0.1:5000
   mlflow models serve \
     -m 'models:/citibike_capacity_predictor@champion' \
     -p 5001 --host 127.0.0.1 --env-manager local
   ```

6. In another terminal, submit coordinates:

   ```bash
   curl -X POST http://127.0.0.1:5001/invocations \
     -H 'Content-Type: application/json' \
     -d '{"dataframe_records":[{"latitude":40.7128,"longitude":-74.0060}]}'
   ```

7. Read the numerical capacity in the response's `predictions` list. If you select another alias version, restart the model-serving process to load it. Stop this serving process before demo 08 uses port 5001.


## Files and outputs

- `station-view.sql`: retained SQL reference; not required for this workflow.
- `regression.py`: final integrated training, logging, registration, alias assignment, and plotting.
- Generated locally: `regression_results.png`.
- Shared tracking storage: `../mlflow.db` and server-managed model artifacts.
- Registry: `citibike_capacity_predictor`; alias: `champion`.

## Source and verification

Combines the final regression script in `chat.md` with the MLflow training block and final serialization correction in `chat2.md`. Corrections are incorporated into this guide; troubleshooting exchanges are omitted. These examples now use the local AWS-derived export. See [verification](../verification.md) for current executed checks and their limits.

## Learning checkpoints

**Before running:** Local station data is available and the MLflow tracking server runs on port 5000.

**Expected output:** A logged run and candidate version, followed by numerical predictions from POST `/invocations` after you select champion and start serving.

**Interpret it:** Tracking, registration, promotion, serving, and prediction are separate activities. Training no longer promotes the latest run automatically.

**Check your understanding:**

1. What changes when you register a model, and what remains unserved?
2. Why does changing an alias require restarting a server that already loaded its artifact?

Record your observed result before moving to another demo. Sample/reported metrics describe their stated data and environment, not a required answer for your machine.
