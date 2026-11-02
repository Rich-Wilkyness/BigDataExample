# Live fraud model monitoring: steps

[Demo index](../README.md) · [Theory](theory.md) · [Shared setup](../setup.md)

## Before starting

Complete [demo 08](../08-kafka-fraud-inference/README.md). Keep its producer, inference consumer, model server, Kafka, and MLflow tracking server running. Flask and OpenAI are not required.

## Finalized steps

1. From `friday-ml-demos`, activate the shared environment and install this demo's packages:

   ```bash
   source .venv/bin/activate
   python -m pip install -r 10-live-model-monitoring/requirements.txt
   cd 10-live-model-monitoring
   ```

2. Run the monitor; it discovers the loaded version from demo 08’s `/metadata` endpoint:

   ```bash
   python monitor_fraud.py
   ```

3. Allow at least 100 matching-version predictions to arrive. Open `fraud-live-monitoring` in MLflow and select the `deployed-model-v<version>-live` run.

4. Inspect metric histories for live accuracy, precision, recall, F1, false positives, false negatives, true positives, and true negatives. Another update appears after every 100 processed predictions.

5. Compare live results with the selected model's training evaluation, keeping the different datasets and time windows in mind. Stop the monitor with Ctrl+C when finished.


## Files and outputs

- `monitor_fraud.py`: rolling classifier metrics and MLflow history.
- Input topic: `fraud-predictions` from demo 08.
- MLflow experiment: `fraud-live-monitoring`.
- No local CSV or dashboard is created.

## Source and verification

Recovered from `chat2.md`, “Create monitor_fraud.py,” with the fixed classroom version made configurable. Corrections are incorporated into this guide; troubleshooting exchanges are omitted. The monitor now discovers the served model identity instead of requiring a manually typed version. See [verification](../verification.md) for current evidence and pending integrations.

## Learning checkpoints

**Before running:** The identity-reporting model server, prediction stream, Kafka, and MLflow are running.

**Expected output:** A monitoring run for the discovered version and a metric update after each 100 matching events, using at most the latest 500.

**Interpret it:** The window is recent deployed-model behavior, not the fixed validation or final-test population.

**Check your understanding:**

1. Why might rolling accuracy differ from training validation accuracy?
2. Does a decline alone prove the source data distribution changed?

Record your observed result before moving to another demo. Sample/reported metrics describe their stated data and environment, not a required answer for your machine.
