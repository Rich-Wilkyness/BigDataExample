# Kafka fraud inference: steps

[Demo index](../README.md) · [Theory](theory.md) · [Shared setup](../setup.md)

## Before starting

Complete [demo 07](../07-kafka-fraud-training/README.md), choose a model using validation results, and run its final test. Keep local Kafka and MLflow tracking running. Stop the earlier capacity model-serving process before reusing port 5001. No API key is required.

## Finalized steps

1. From `friday-ml-demos`, activate the environment and install the packages:

   ```bash
   source .venv/bin/activate
   python -m pip install -r 08-kafka-fraud-inference/requirements.txt
   cd 08-kafka-fraud-inference
   ```

2. Select the exact version you reviewed in demo 07:

   ```bash
   python select-model.py --version YOUR_SELECTED_VERSION
   ```

   This checks for that version's final-test report, looks up its source run, explicitly assigns `champion`, and writes local `deployment.json`. The file names a numbered model URI, not a moving alias.

3. Create the output topic in a terminal with `KAFKA_HOME` set:

   ```bash
   "$KAFKA_HOME/bin/kafka-topics.sh" \
     --bootstrap-server localhost:9092 --create --if-not-exists \
     --topic fraud-predictions --partitions 1 --replication-factor 1
   ```

4. In this directory with the environment active, start the identity-reporting model server:

   ```bash
   python serve-model.py
   ```

   This local Flask API loads the pinned artifact using MLflow and serves predictions on port 5001. It replaces `mlflow models serve` for the fraud stage so the loaded model's identity can be returned with each prediction. The capacity demo still uses the generic MLflow CLI.

5. In another terminal, inspect the loaded identity and send a prediction:

   ```bash
   curl http://127.0.0.1:5001/metadata
   curl -X POST http://127.0.0.1:5001/invocations \
     -H 'Content-Type: application/json' \
     -d '{"dataframe_records":[{"amount":950.0,"hour":2,"distance_from_home":250.0,"new_device":1,"transactions_last_hour":12}]}'
   ```

   Responses include `predictions` and `model`: the numbered URI, version, and source run from the artifact actually loaded by this process. Prediction 1 means flagged fraud; 0 means predicted legitimate. Actual outcomes depend on your chosen model.

6. In another activated terminal, from this demo directory, start inference:

   ```bash
   python fraud_inference_consumer.py
   ```

   No manual version export is needed. The consumer reads `/metadata` at startup and checks each prediction response against it. A server/model change stops the consumer so it cannot keep publishing predictions with a stale version label.

7. Leave the producer from demo 07 running so new events arrive. Inspect predictions:

   ```bash
   "$KAFKA_HOME/bin/kafka-console-consumer.sh" \
     --bootstrap-server localhost:9092 --topic fraud-predictions
   ```

8. Confirm records contain original `features`, prediction, synthetic label, correctness, `model_version`, `model_uri`, and `source_run_id`. Then continue to the dashboard or monitor. To switch versions, review/select the new version, restart the server, and restart inference and monitoring.

## Why identity matters

A handwritten version field is like labeling a photograph “camera 6” without checking which camera took it. Here, the process holding the model supplies its own identity. The consumer carries that identity with the resulting event, so the dashboard and monitor can attribute results to the actual served version.

## Files and verification

- `select-model.py`: explicit promotion and deployment manifest.
- `serve-model.py`: pinned MLflow model loading, `/metadata`, `/ping`, and `/invocations`.
- `fraud_inference_consumer.py`: input events, HTTP prediction, output acknowledgement, and exact processed-offset commit.
- `deployment.json`: local generated configuration, excluded from Git.

Offline tests check response identity, detection of a model change, and rejection of label leakage at the API boundary. See [verification](../verification.md) for executed local model checks and pending Kafka integration. Output acknowledgement and offset commit are separate operations, so a crash can still duplicate prediction events.

## Learning checkpoints

**Before running:** A candidate has been selected using validation and checked once on final test. The tracking server and local broker are available.

**Expected output:** `/metadata` and `/invocations` identify the same numbered model; prediction events include its version, URI, source run, and original features.

**Interpret it:** The process holding the model supplies its identity. The consumer checks it, publishes a result, then commits exactly the processed input position.

**Check your understanding:**

1. What would be misleading about manually labeling a version-7 prediction as version 6?
2. What happens if the server changes models while this consumer is running?

Record your observed result before moving to another demo. Sample/reported metrics describe their stated data and environment, not a required answer for your machine.
