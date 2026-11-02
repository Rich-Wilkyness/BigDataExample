"""Track recent labeled prediction quality separately from training runs."""

import json
import os
import time
from collections import deque

import mlflow
import requests
from kafka import KafkaConsumer
from sklearn.metrics import (
    accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    confusion_matrix
)

MLFLOW_URI = "http://127.0.0.1:5000"
# Discover the actual loaded server identity rather than asking the learner
# to type a separate version number for monitoring.
response = requests.get("http://127.0.0.1:5001/metadata", timeout=15)
response.raise_for_status()
MODEL_IDENTITY = response.json()
MODEL_VERSION = str(MODEL_IDENTITY["model_version"])
# Retain at most 500 recent matching-version outcomes and update every
# 100 accepted events. The first update uses only 100 available examples.
WINDOW_SIZE = 500
LOG_EVERY = 100

mlflow.set_tracking_uri(MLFLOW_URI)
mlflow.set_experiment("fraud-live-monitoring")

# An independent group reads prediction events without taking work away
# from the dashboard collector. latest affects a new group, not every restart.
# This instructional monitor does not deduplicate repeated event IDs.
consumer = KafkaConsumer(
    "fraud-predictions",
    bootstrap_servers="localhost:9092",
    group_id="fraud-mlflow-monitor-v1",
    auto_offset_reset="latest",
    value_deserializer=lambda v: json.loads(v.decode("utf-8"))
)

# deque(maxlen=...) automatically drops the oldest item as a new one arrives.
# Append to both queues together to preserve prediction/label alignment.
actuals = deque(maxlen=WINDOW_SIZE)
predictions = deque(maxlen=WINDOW_SIZE)

total = 0

# One run collects a time history for this monitoring process. The metric
# step later is an event count, not a timestamp or a new model version.
with mlflow.start_run(run_name=f"deployed-model-v{MODEL_VERSION}-live"):
    mlflow.log_param("model_version", MODEL_VERSION)
    mlflow.log_param("model_uri", MODEL_IDENTITY["model_uri"])
    mlflow.log_param("window_size", WINDOW_SIZE)

    print("Monitoring live fraud predictions...")

    try:
        for message in consumer:
            event = message.value
            # Version strings and integer source versions are compared consistently.
            # Identity is reported by the model server; keep this run on that version.
            if str(event.get("model_version")) != MODEL_VERSION:
                continue

            # The source run distinguishes identical version numbers from a
            # different registry/cohort. Old events without this identity skip.
            if event.get("source_run_id") != MODEL_IDENTITY["source_run_id"]:
                continue

            actuals.append(int(event["actual_fraud"]))
            predictions.append(int(event["predicted_fraud"]))

            total += 1

            # Skip metric calculation between reporting boundaries while continuing
            # to update the rolling queues for every accepted prediction.
            if total % LOG_EVERY != 0:
                continue

            y_true = list(actuals)
            y_pred = list(predictions)

            # Fix label order to legitimate=0, fraud=1, so the 2x2 matrix always has
            # four cells even if one class is absent in a small window. ravel()
            # flattens the cells to TN, FP, FN, TP in row order.
            tn, fp, fn, tp = confusion_matrix(
                y_true, y_pred, labels=[0, 1]
            ).ravel()

            # Zero-division handling avoids undefined values in small/one-class windows.
            # These are classifier quality metrics, not LLM explanation quality scores.
            metrics = {
                "live_accuracy": accuracy_score(y_true, y_pred),
                "live_precision": precision_score(
                    y_true, y_pred, zero_division=0
                ),
                "live_recall": recall_score(
                    y_true, y_pred, zero_division=0
                ),
                "live_f1": f1_score(
                    y_true, y_pred, zero_division=0
                ),
                "false_positives": int(fp),
                "false_negatives": int(fn),
                "true_positives": int(tp),
                "true_negatives": int(tn)
            }

            # All metrics share this processed-count step so their curves line up.
            # A drop warrants investigation; it does not by itself establish drift.
            mlflow.log_metrics(metrics, step=total)

            print(
                f"Processed={total} "
                f"Accuracy={metrics['live_accuracy']:.3f} "
                f"Precision={metrics['live_precision']:.3f} "
                f"Recall={metrics['live_recall']:.3f} "
                f"F1={metrics['live_f1']:.3f}"
            )

    except KeyboardInterrupt:
        print("Stopping monitoring.")

    finally:
        consumer.close()
