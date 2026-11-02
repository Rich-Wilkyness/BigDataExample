"""Evaluate a chosen version on the untouched test paper, once per selection.

Choose using validation metrics first. Do not try versions against the test
paper to choose a winner; that would turn the test set into validation data.
"""

import os
import argparse
import hashlib
import json
from pathlib import Path

import mlflow
import mlflow.sklearn
import pandas as pd

from train_streaming_fraud import classification_metrics
from training_data import FEATURES


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--version", required=True)
    args = parser.parse_args()
    directory = Path("evaluation")
    manifest = json.loads((directory / "manifest.json").read_text())
    content = (directory / "test.csv").read_bytes()
    if hashlib.sha256(content).hexdigest() != manifest["sha256"]["test.csv"]:
        raise ValueError("The reserved test file changed; do not report this as the same benchmark.")
    result_path = directory / f"final-test-v{args.version}.json"
    if result_path.exists():
        raise ValueError(f"Final test already recorded for this version: {result_path}")
    test = pd.read_csv(directory / "test.csv", dtype={"transaction_id": "string"})
    mlflow.set_tracking_uri(os.getenv("MLFLOW_TRACKING_URI", "http://127.0.0.1:5000"))
    model_uri = f"models:/kafka_fraud_detector/{args.version}"
    client = mlflow.MlflowClient()
    version = client.get_model_version("kafka_fraud_detector", args.version)
    source_run = client.get_run(version.run_id)
    if source_run.data.params.get("validation_sha256") != manifest["sha256"]["validation.csv"]:
        raise ValueError("This candidate belongs to a different validation cohort; use its original evaluation files.")
    model = mlflow.sklearn.load_model(model_uri)
    metrics = classification_metrics(test["is_fraud"], model.predict(test[FEATURES]))
    mlflow.set_experiment("fraud-final-evaluation")
    with mlflow.start_run(run_name=f"selected-version-{args.version}"):
        mlflow.log_params({"model_uri": model_uri, "test_sha256": manifest["sha256"]["test.csv"], "test_rows": len(test)})
        mlflow.log_metrics({f"test_{name}": value for name, value in metrics.items()})
    result_path.write_text(json.dumps({"model_uri": model_uri, "source_run_id": version.run_id,
                                      "test_sha256": manifest["sha256"]["test.csv"], "metrics": metrics}, indent=2) + "\n")
    print(json.dumps(metrics, indent=2))
    print("If the final check is acceptable, select this version in demo 08. Do not select again using test scores.")


if __name__ == "__main__":
    main()
