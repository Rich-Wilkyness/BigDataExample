"""Offline checks for fixed evaluation data, local inputs, and model identity."""

import csv
import importlib.util
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

import numpy as np
import pandas as pd

BASE = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE))
sys.path.insert(0, str(BASE / "07-kafka-fraud-training"))
from training_data import FEATURES, clean_data, evaluation_sets, snapshot_csv
from fraud_training_consumer import FIELDS, append_message
from shared.station_data import load_stations


def load_file(name, relative):
    spec = importlib.util.spec_from_file_location(name, BASE / relative)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


server = load_file("fraud_model_server", "08-kafka-fraud-inference/serve-model.py")
inference = load_file("fraud_inference", "08-kafka-fraud-inference/fraud_inference_consumer.py")
selection = load_file("fraud_selection", "08-kafka-fraud-inference/select-model.py")


def transactions(count=500, start=0):
    # A transparent fixture with distinct IDs; not a model-quality benchmark.
    return pd.DataFrame([{
        "transaction_id": f"transaction-{index:05d}", "event_time": "2026-10-30T00:00:00Z",
        "amount": float(index + 1), "hour": index % 24,
        "distance_from_home": float(index % 100), "new_device": index % 2,
        "transactions_last_hour": index % 10, "is_fraud": int(index % 10 == 0),
    } for index in range(start, start + count)])


class WorkflowTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.work = Path(self.temporary.name)

    def test_csv_and_parquet_preserve_station_identity(self):
        frame = pd.DataFrame({"station_id": ["001", "002"], "station_name": ["First", "Second"],
                              "latitude": [40.7, 40.8], "longitude": [-74., -73.9], "capacity": [0, 20]})
        for extension in ("csv", "parquet"):
            path = self.work / f"stations.{extension}"
            if extension == "csv":
                frame.to_csv(path, index=False)
            else:
                frame.to_parquet(path, index=False)
            with patch.dict(os.environ, {"CITIBIKE_STATIONS_PATH": str(path)}):
                self.assertEqual(list(load_stations()["station_id"]), ["001", "002"])
                self.assertEqual(list(load_stations(require_capacity=True)["station_id"]), ["002"])

    def test_duplicate_station_keys_fail_instead_of_inflating_examples(self):
        path = self.work / "stations.csv"
        pd.DataFrame({"station_id": ["001", "001"]}).to_csv(path, index=False)
        with patch.dict(os.environ, {"CITIBIKE_STATIONS_PATH": str(path)}), self.assertRaises(ValueError):
            load_stations()

    def test_snapshot_does_not_change_when_collection_continues(self):
        source = self.work / "source.csv"
        transactions().to_csv(source, index=False)
        frozen, digest = snapshot_csv(source, self.work / "runs")
        before = frozen.read_bytes()
        transactions(100, 500).to_csv(source, mode="a", header=False, index=False)
        self.assertEqual(frozen.read_bytes(), before)
        self.assertNotEqual(snapshot_csv(source, self.work / "runs")[1], digest)

    def test_fixed_validation_and_test_never_enter_growing_training_set(self):
        directory = self.work / "evaluation"
        first_train, first_validation, first_manifest = evaluation_sets(transactions(), directory)
        test = pd.read_csv(directory / "test.csv")
        larger = pd.concat([transactions(), transactions(100, 500)], ignore_index=True)
        train, validation, manifest = evaluation_sets(larger, directory)
        self.assertEqual(len(first_train), 300)
        self.assertEqual(len(train), 400)
        self.assertEqual(first_validation["transaction_id"].tolist(), validation["transaction_id"].tolist())
        self.assertEqual(first_manifest, manifest)
        self.assertFalse(set(train["transaction_id"]) & set(test["transaction_id"]))
        self.assertFalse(set(train["transaction_id"]) & set(validation["transaction_id"]))

    def test_changed_evaluation_paper_is_rejected(self):
        directory = self.work / "evaluation"
        evaluation_sets(transactions(), directory)
        with (directory / "validation.csv").open("a") as stream:
            stream.write("unexpected change\n")
        with self.assertRaises(ValueError):
            evaluation_sets(transactions(), directory)

    def test_conflicting_replay_is_rejected(self):
        frame = transactions()
        duplicate = frame.iloc[[0]].copy()
        duplicate["amount"] = 9999
        path = self.work / "conflict.csv"
        pd.concat([frame, duplicate]).to_csv(path, index=False)
        with self.assertRaises(ValueError):
            clean_data(path)

    def test_csv_is_durable_before_exact_offset_commit(self):
        event = transactions(1).iloc[0].to_dict()
        consumer = Mock()
        path = self.work / "collected.csv"
        message = SimpleNamespace(value=event, topic="fraud-transactions", partition=2, offset=19)

        def on_commit(offsets):
            # A separate file read can already see the complete stored row.
            self.assertEqual(pd.read_csv(path).iloc[0]["transaction_id"], event["transaction_id"])
            partition, offset = next(iter(offsets.items()))
            self.assertEqual((partition.partition, offset.offset), (2, 20))

        consumer.commit.side_effect = on_commit
        with path.open("a+", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=FIELDS)
            writer.writeheader()
            append_message(stream, writer, message, consumer)
        consumer.commit.assert_called_once()

    def test_model_response_identity_comes_from_the_loaded_model_server(self):
        identity = {"model_name": "kafka_fraud_detector", "model_version": "7",
                    "model_uri": "models:/kafka_fraud_detector/7", "source_run_id": "run-seven"}
        model = Mock()
        model.predict.return_value = np.array([1])
        client = server.create_app(model, identity).test_client()
        row = transactions(1).iloc[0].to_dict()
        result = client.post("/invocations", json={"dataframe_records": [{name: row[name] for name in FEATURES}]}).get_json()
        self.assertEqual(result["model"], client.get("/metadata").get_json())
        session = Mock()
        session.post.return_value.json.return_value = result
        event = inference.predict_event(row, identity, session)
        self.assertEqual(event["model_version"], "7")
        self.assertEqual(event["source_run_id"], "run-seven")
        with self.assertRaises(RuntimeError):
            inference.predict_event(row, {**identity, "model_version": "6"}, session)

    def test_label_leakage_is_rejected_at_model_api(self):
        model = Mock()
        client = server.create_app(model, {}).test_client()
        self.assertEqual(client.post("/invocations", json={"dataframe_records": [transactions(1).iloc[0].to_dict()]}).status_code, 400)
        model.predict.assert_not_called()

    def test_promotion_rejects_same_version_number_from_another_registry_run(self):
        report = {"model_uri": "models:/kafka_fraud_detector/7", "source_run_id": "original-run"}
        selection.verify_report(report, report["model_uri"], "original-run")
        with self.assertRaises(ValueError):
            selection.verify_report(report, report["model_uri"], "different-run")


if __name__ == "__main__":
    unittest.main()
