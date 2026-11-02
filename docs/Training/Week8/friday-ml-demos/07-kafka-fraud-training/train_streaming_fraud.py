"""Fit candidates on growing training data; compare on one fixed validation set."""

import os
import argparse
from pathlib import Path

import mlflow
import mlflow.sklearn
from mlflow.models import infer_signature
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score

from training_data import FEATURES, clean_data, evaluation_sets, snapshot_csv


def classification_metrics(actual, predicted):
    """Use multiple metrics because legitimate transactions dominate the stream."""
    return {
        "accuracy": accuracy_score(actual, predicted),
        "precision": precision_score(actual, predicted, zero_division=0),
        "recall": recall_score(actual, predicted, zero_division=0),
        "f1": f1_score(actual, predicted, zero_division=0),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--trees", type=int, default=100)
    parser.add_argument("--max-depth", type=int, default=8)
    parser.add_argument("--source", type=Path, default=Path("fraud_training_data.csv"))
    args = parser.parse_args()
    if args.trees < 1 or args.max_depth < 1:
        parser.error("trees and max-depth must be positive")

    # Freeze the input under a shared lock. The collector continues appending
    # after this short copy; the rest of this run reads immutable snapshot bytes.
    snapshot, source_sha = snapshot_csv(args.source, "runs")
    frame = clean_data(snapshot)
    train, validation, manifest = evaluation_sets(frame, "evaluation")
    print(f"Snapshot: {snapshot}\nTraining rows: {len(train)}; fixed validation rows: {len(validation)}")
    print("Final test examples are excluded from training and candidate metrics.")

    model = RandomForestClassifier(
        n_estimators=args.trees, max_depth=args.max_depth,
        class_weight="balanced", random_state=42, n_jobs=-1,
    )
    model.fit(train[FEATURES], train["is_fraud"])
    predictions = model.predict(validation[FEATURES])
    metrics = classification_metrics(validation["is_fraud"], predictions)

    mlflow.set_tracking_uri(os.getenv("MLFLOW_TRACKING_URI", "http://127.0.0.1:5000"))
    mlflow.set_experiment("kafka-streaming-fraud-training")
    with mlflow.start_run(run_name=f"candidate-{len(train)}-rows-depth-{args.max_depth}"):
        mlflow.log_params({
            "n_estimators": args.trees, "max_depth": args.max_depth,
            "training_rows": len(train), "validation_rows": len(validation),
            "snapshot_sha256": source_sha,
            "validation_sha256": manifest["sha256"]["validation.csv"],
        })
        # Validation metrics guide candidate selection. No final test scores are
        # logged here, and no alias is moved just because this run is newer.
        mlflow.log_metrics({f"validation_{name}": value for name, value in metrics.items()})
        info = mlflow.sklearn.log_model(
            sk_model=model, name="fraud_classifier",
            signature=infer_signature(train[FEATURES], model.predict(train[FEATURES])),
            input_example=train[FEATURES].head(3),
            skops_trusted_types=["sklearn.tree._tree.Tree"],
        )
        version = mlflow.register_model(info.model_uri, "kafka_fraud_detector")
    print("Validation metrics:", metrics)
    print("Registered candidate version:", version.version)
    print("Compare candidates, then run evaluate-final-model.py --version YOUR_VERSION.")
    print("Training does not change a running model server or promote champion.")


if __name__ == "__main__":
    main()
