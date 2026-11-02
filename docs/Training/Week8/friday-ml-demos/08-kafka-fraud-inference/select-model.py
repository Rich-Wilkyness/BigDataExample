"""Select a reviewed registered version and write one explicit deployment file."""

import os
import argparse
import json
from pathlib import Path

import mlflow


def verify_report(report, uri, source_run_id):
    # Registry version numbers alone can repeat in a different tracking store.
    # Bind the final evaluation to the exact training run, not just its label.
    if report.get("model_uri") != uri or report.get("source_run_id") != source_run_id:
        raise ValueError("The final-test report does not belong to this registry artifact.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--version", required=True, type=int)
    parser.add_argument("--evaluation-dir", type=Path, default=Path(__file__).resolve().parents[1] / "07-kafka-fraud-training/evaluation")
    parser.add_argument("--output", type=Path, default=Path(__file__).with_name("deployment.json"))
    args = parser.parse_args()
    name = "kafka_fraud_detector"
    uri = f"models:/{name}/{args.version}"
    result_path = args.evaluation_dir / f"final-test-v{args.version}.json"
    if not result_path.exists() or json.loads(result_path.read_text())["model_uri"] != uri:
        raise ValueError("Complete the selected version's final test in demo 07 before deploying it.")
    client = mlflow.MlflowClient(tracking_uri=os.getenv("MLFLOW_TRACKING_URI", "http://127.0.0.1:5000"))
    version = client.get_model_version(name, str(args.version))
    verify_report(json.loads(result_path.read_text()), uri, version.run_id)
    # Promotion is now an explicit learner decision, not a side effect of fitting.
    client.set_registered_model_alias(name, "champion", str(args.version))
    deployment = {"model_name": name, "model_version": str(args.version),
                  "model_uri": uri, "source_run_id": version.run_id}
    path = args.output
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(deployment, indent=2) + "\n")
    temporary.replace(path)
    print(f"Selected {uri}; wrote {path}. Restart serve-model.py to load it.")


if __name__ == "__main__":
    main()
