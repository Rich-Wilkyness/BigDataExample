"""Offline contract checks; no broker, tracking server, or paid requests."""

import copy
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

from app import create_app
from collector import collect
from storage import dashboard_data, save_prediction


class DemoTests(unittest.TestCase):
    # Each test gets an isolated SQLite database and provider double. Temporary
    # files are removed after the test, leaving the learning databases untouched.
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.database = Path(self.directory.name) / "test.sqlite3"
        self.event = json.loads(Path(__file__).with_name("sample-predictions.json").read_text())[0]
        self.provider = Mock()
        self.provider.responses.create.return_value = SimpleNamespace(output_text="Review the supplied evidence.")
        self.app = create_app({
            "TESTING": True, "DATABASE": self.database,
            "TRACING_ENABLED": False, "OPENAI_MODEL": "test-model",
        }, openai_client=self.provider)
        self.client = self.app.test_client()

    def stored_id(self):
        save_prediction(self.database, self.event)
        return dashboard_data(self.database)["predictions"][0]["id"]

    def test_preview_renders_assets_and_empty_state_without_provider_calls(self):
        self.assertEqual(self.client.get("/").status_code, 200)
        for asset in ("dashboard.js", "dashboard.css"):
            response = self.client.get(f"/static/{asset}")
            self.assertEqual(response.status_code, 200)
            response.close()
        data = self.client.get("/api/predictions").get_json()
        self.assertEqual(data["stats"]["processed"], 0)
        self.assertIsNone(data["stats"]["accuracy"])
        self.provider.responses.create.assert_not_called()

    # Verify an observable delivery requirement: replayed Kafka events must not
    # inflate dashboard metrics. The fixtures include both kinds of mistake.
    def test_replayed_events_do_not_inflate_statistics(self):
        fixtures = json.loads(Path(__file__).with_name("sample-predictions.json").read_text())
        for event in fixtures:
            self.assertTrue(save_prediction(self.database, event))
            self.assertFalse(save_prediction(self.database, event))
        data = dashboard_data(self.database)
        self.assertEqual(data["stats"], {"processed": 4, "flagged": 2, "correct": 2, "accuracy": 0.5})
        self.assertEqual(data["predictions"][0]["features"], fixtures[-1]["features"])

    def test_different_model_versions_are_distinct_and_correct_is_recomputed(self):
        self.event["correct"] = False
        self.stored_id()
        self.event["model_version"] = "another-version"
        save_prediction(self.database, self.event)
        data = dashboard_data(self.database)
        self.assertEqual(data["stats"]["processed"], 2)
        self.assertTrue(all(event["correct"] for event in data["predictions"]))

    def test_old_event_without_features_displays_but_cannot_be_explained(self):
        del self.event["features"]
        prediction_id = self.stored_id()
        result = self.client.post(f"/api/predictions/{prediction_id}/explain")
        self.assertEqual(result.status_code, 422)
        self.assertFalse(dashboard_data(self.database)["predictions"][0]["can_explain"])
        self.provider.responses.create.assert_not_called()

    # Check the API boundary: viewing the app never requests an explanation;
    # the explicit POST sends model features while withholding ground truth.
    def test_explanation_is_on_demand_and_excludes_ground_truth(self):
        prediction_id = self.stored_id()
        self.client.get("/")
        self.client.get("/api/predictions")
        self.provider.responses.create.assert_not_called()
        response = self.client.post(f"/api/predictions/{prediction_id}/explain")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["explanation"], "Review the supplied evidence.")
        arguments = self.provider.responses.create.call_args.kwargs
        evidence = json.loads(arguments["input"])
        self.assertEqual(evidence["features"], self.event["features"])
        self.assertNotIn("actual_fraud", evidence)
        self.assertNotIn("correct", evidence)
        self.assertFalse(arguments["store"])

    # Use the installed OpenAI SDK with an in-memory HTTP transport. This
    # checks request/response parsing without network access or a paid API call.
    def test_real_openai_sdk_with_mock_http_transport(self):
        from openai import OpenAI
        try:
            import httpx2 as httpx
        except ImportError:
            import httpx

        requests = []

        def respond(request):
            requests.append(json.loads(request.content))
            return httpx.Response(200, json={
                "id": "resp_offline_test", "object": "response",
                "created_at": 0, "status": "completed", "model": "test-model",
                "output": [{
                    "type": "message", "id": "msg_test", "role": "assistant",
                    "status": "completed", "content": [{
                        "type": "output_text", "text": "Offline SDK response.", "annotations": []
                    }]
                }],
            })

        prediction_id = self.stored_id()
        with OpenAI(api_key="offline-test-key", http_client=httpx.Client(transport=httpx.MockTransport(respond))) as sdk:
            app = create_app({
                "DATABASE": self.database, "TRACING_ENABLED": False,
                "OPENAI_MODEL": "test-model",
            }, openai_client=sdk)
            result = app.test_client().post(f"/api/predictions/{prediction_id}/explain")
        self.assertEqual(result.status_code, 200)
        self.assertEqual(result.get_json()["explanation"], "Offline SDK response.")
        self.assertEqual(len(requests), 1)
        self.assertEqual(requests[0]["model"], "test-model")
        self.assertEqual(json.loads(requests[0]["input"])["features"], self.event["features"])

    def test_missing_transaction_and_read_only_explanation_route(self):
        self.assertEqual(self.client.post("/api/predictions/999/explain").status_code, 404)
        prediction_id = self.stored_id()
        self.assertEqual(self.client.get(f"/api/predictions/{prediction_id}/explain").status_code, 405)
        self.provider.responses.create.assert_not_called()

    def test_missing_configuration_does_not_call_provider(self):
        prediction_id = self.stored_id()
        self.app.config["OPENAI_MODEL"] = ""
        self.assertEqual(self.client.post(f"/api/predictions/{prediction_id}/explain").status_code, 503)
        self.provider.responses.create.assert_not_called()
        with patch.dict("os.environ", {}, clear=True):
            app = create_app({"DATABASE": self.database, "TRACING_ENABLED": False, "OPENAI_MODEL": "test"})
            self.assertEqual(app.test_client().post(f"/api/predictions/{prediction_id}/explain").status_code, 503)

    def test_provider_error_does_not_leak_details(self):
        prediction_id = self.stored_id()
        self.provider.responses.create.side_effect = RuntimeError("private provider details")
        with self.assertLogs(self.app.logger, level="ERROR"):
            response = self.client.post(f"/api/predictions/{prediction_id}/explain")
        self.assertEqual(response.status_code, 502)
        self.assertNotIn("private provider details", response.get_data(as_text=True))

    def test_invalid_events_are_not_persisted(self):
        for field, value in (("amount", float("nan")), ("hour", 24), ("new_device", 2), ("transactions_last_hour", 1.5)):
            event = copy.deepcopy(self.event)
            event["features"][field] = value
            with self.subTest(field=field), self.assertRaises(ValueError):
                save_prediction(self.database, event)
        event = dict(self.event, predicted_fraud="1")
        with self.assertRaises(ValueError):
            save_prediction(self.database, event)
        self.assertEqual(dashboard_data(self.database)["stats"]["processed"], 0)

    # Inspect durable storage from inside the fake commit callback. That proves
    # the write has already completed when the collector advances Kafka progress.
    def test_collector_commits_exact_offset_only_after_persistence(self):
        message = SimpleNamespace(topic="fraud-predictions", partition=0, offset=7, value=self.event)
        consumer = Mock()
        consumer.__iter__ = Mock(return_value=iter([message]))

        def verify_commit(offsets):
            self.assertEqual(dashboard_data(self.database)["stats"]["processed"], 1)
            partition, position = next(iter(offsets.items()))
            self.assertEqual((partition.topic, partition.partition, position.offset), ("fraud-predictions", 0, 8))

        consumer.commit.side_effect = verify_commit
        collect(consumer, self.database)
        consumer.commit.assert_called_once()

    # An invalid event must leave its Kafka progress uncommitted so the failure
    # cannot silently advance past data the dashboard never stored.
    def test_collector_does_not_commit_failed_write(self):
        message = SimpleNamespace(topic="fraud-predictions", partition=0, offset=7, value={})
        consumer = Mock()
        consumer.__iter__ = Mock(return_value=iter([message]))
        with self.assertRaises(ValueError):
            collect(consumer, self.database)
        consumer.commit.assert_not_called()


if __name__ == "__main__":
    unittest.main()
