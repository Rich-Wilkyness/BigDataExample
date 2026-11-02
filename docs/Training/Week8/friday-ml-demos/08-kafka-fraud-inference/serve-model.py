"""Expose one explicit MLflow-loaded version and its identity from one process.

This small local Flask server replaces the generic MLflow serving CLI for the
fraud demo, so each prediction includes metadata from the model actually loaded.
"""

import os
import json
import sys
from pathlib import Path

import pandas as pd
from flask import Flask, jsonify, request

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from shared.fraud_contract import FEATURES, normalize_features


def create_app(model, identity):
    app = Flask(__name__)
    identity = dict(identity)

    @app.get("/metadata")
    def metadata():
        # This identity belongs to the same fixed in-memory model used below.
        return jsonify(identity)

    @app.get("/ping")
    def ping():
        return jsonify(status="ready")

    @app.post("/invocations")
    def invoke():
        body = request.get_json(silent=True)
        records = body.get("dataframe_records") if isinstance(body, dict) else None
        if not isinstance(records, list) or not records or len(records) > 100:
            return jsonify(error="Supply 1–100 dataframe_records."), 400
        try:
            frame = pd.DataFrame([normalize_features(record) for record in records], columns=FEATURES)
        except ValueError as error:
            return jsonify(error=str(error)), 400
        values = [int(value) for value in model.predict(frame)]
        return jsonify(predictions=values, model=identity)

    return app


def main():
    import mlflow
    import mlflow.sklearn

    deployment = json.loads(Path(__file__).with_name("deployment.json").read_text())
    expected_uri = f"models:/{deployment['model_name']}/{deployment['model_version']}"
    if deployment["model_uri"] != expected_uri or deployment["model_name"] != "kafka_fraud_detector":
        raise ValueError("Invalid pinned model deployment.")
    mlflow.set_tracking_uri(os.getenv("MLFLOW_TRACKING_URI", "http://127.0.0.1:5000"))
    version = mlflow.MlflowClient().get_model_version(deployment["model_name"], deployment["model_version"])
    if version.run_id != deployment["source_run_id"]:
        raise ValueError("Deployment file does not match this registry's source run.")
    # Resolve a numbered artifact once; later alias changes cannot replace it.
    model = mlflow.sklearn.load_model(expected_uri)
    print(f"Loaded {expected_uri} from run {version.run_id}")
    create_app(model, deployment).run(host="127.0.0.1", port=5001, debug=False)


if __name__ == "__main__":
    main()
