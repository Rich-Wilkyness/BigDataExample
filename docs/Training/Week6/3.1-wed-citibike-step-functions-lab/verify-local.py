"""Offline lab checks; never calls AWS or runs Spark/Redshift transformations."""
import ast
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
from pathlib import Path
import re
from unittest.mock import patch

ROOT = Path(__file__).resolve().parent


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def check_structure():
    python_files = list(ROOT.rglob("*.py"))
    json_files = [p for p in ROOT.rglob("*.json")
                  if ".terraform" not in p.parts and not p.name.endswith(".local.json")]
    for path in python_files:
        ast.parse(path.read_text(), filename=str(path))
    for path in json_files:
        json.loads(path.read_text())
    provenance = json.loads((ROOT / "reference/provenance.json").read_text())
    for entry in provenance["files"]:
        actual = hashlib.sha256((ROOT / entry["local_file"]).read_bytes()).hexdigest()
        assert actual == entry["sha256"], entry["local_file"]
    for path in (ROOT / "workflows").glob("*.json"):
        workflow = json.loads(path.read_text())
        states = workflow["States"]
        edges = {}
        for name, state in states.items():
            targets = {state[key] for key in ("Next", "Default") if key in state}
            targets.update(item["Next"] for item in state.get("Choices", []) + state.get("Catch", []))
            assert targets <= states.keys(), (name, targets)
            edges[name] = targets
        visited = set()
        pending = [workflow["StartAt"]]
        while pending:
            state = pending.pop()
            if state not in visited:
                visited.add(state)
                pending.extend(edges[state])
        assert visited == states.keys(), path
    link_count = 0
    for path in list(ROOT.rglob("*.md")) + [ROOT.parent / "3_Wed_Step_Functions.md"]:
        text = path.read_text()
        assert len(re.findall(r"^```", text, re.M)) % 2 == 0, path
        for link in re.findall(r"\]\(([^)]+)\)", text):
            if link.startswith(("https://", "http://", "#")):
                continue
            assert (path.parent / link.split("#")[0]).exists(), (path, link)
            link_count += 1
    print(f"PASS: {len(python_files)} Python files, {len(json_files)} JSON files, "
          f"three reachable workflow graphs, six source hashes, {link_count} local links")


def check_input_contract():
    prepare = load_module("prepare_input", ROOT / "prepare-input.py")
    fixed_now = datetime(2026, 10, 14, 18, tzinfo=timezone.utc)
    value = prepare.build_input("batch_a", "2026-10-14T16:00:00Z", "2026-10-14T17:00:00Z",
                                now=fixed_now)
    assert value["batch_id"] == "batch_a" and not value["reuse_silver"]
    assert "'batch_a', '2026-10-14T16:00:00Z', '2026-10-14T17:00:00Z'" in value["accept_sql"]
    replay = prepare.build_input("batch_a", value["start_at_utc"], value["end_before_utc"],
                                 reuse_silver=True, now=fixed_now)
    assert replay["reuse_silver"] and replay["accept_sql"] == value["accept_sql"]
    for batch, start, end in [
        ("bad' SQL", "2026-10-14T16:00:00Z", "2026-10-14T17:00:00Z"),
        ("a", "2026-10-14T16:00:00Z", "2026-10-14T16:00:00Z"),
        ("a", "2026-10-14T16:00:00Z", "2026-10-14T19:00:00Z"),
        ("a", "2026-10-14 16:00:00", "2026-10-14T17:00:00Z"),
    ]:
        try:
            prepare.build_input(batch, start, end, now=fixed_now)
        except ValueError:
            pass
        else:
            raise AssertionError("Invalid execution input accepted")
    print("PASS: aligned batch/SQL input, replay flag, malformed/injected IDs, empty/future intervals")


def check_sdk_reader():
    import boto3
    from botocore.stub import ANY, Stubber
    reader = load_module("redshift_reader_test", ROOT / "dashboard/redshift-reader.py")
    client = boto3.client("redshift-data", region_name="us-east-2",
                          aws_access_key_id="offline", aws_secret_access_key="offline")
    identifier = "11111111-1111-4111-8111-111111111111"
    with Stubber(client) as stub:
        stub.add_response("execute_statement", {"Id": identifier},
                          {"WorkgroupName": "offline", "Database": "dev", "Sql": ANY})
        stub.add_response("describe_statement", {"Id": identifier, "Status": "FINISHED"},
                          {"Id": identifier})
        stub.add_response("get_statement_result", {
            "ColumnMetadata": [{"name": "bikes_available"}],
            "Records": [[{"longValue": 18}]], "NextToken": "page2",
        }, {"Id": identifier})
        stub.add_response("get_statement_result", {
            "ColumnMetadata": [{"name": "bikes_available"}],
            "Records": [[{"isNull": True}]],
        }, {"Id": identifier, "NextToken": "page2"})
        with patch.object(reader.boto3, "Session") as session:
            session.return_value.client.return_value = client
            rows, actual_id = reader.read_summary("us-east-2", "offline", "dev")
        assert rows == [{"bikes_available": 18}, {"bikes_available": None}]
        assert actual_id == identifier
        stub.assert_no_pending_responses()
    with Stubber(client) as stub:
        stub.add_response("execute_statement", {"Id": identifier})
        stub.add_response("describe_statement", {"Id": identifier, "Status": "FAILED", "Error": "denied"})
        with patch.object(reader.boto3, "Session") as session:
            session.return_value.client.return_value = client
            try:
                reader.read_summary("us-east-2", "offline", "dev")
            except RuntimeError as error:
                assert "denied" in str(error)
            else:
                raise AssertionError("SQL failure hidden")
    print("PASS: offline SDK submission/completion, two result pages, null decoding, SQL failure surfacing")


def check_dashboard():
    from streamlit.testing.v1 import AppTest
    # Any accidental AWS client creation in sample mode fails this check.
    with patch("boto3.Session", side_effect=AssertionError("AWS accessed in sample mode")):
        app = AppTest.from_file(str(ROOT / "dashboard/app.py")).run(timeout=20)
    assert not app.exception, list(app.exception)
    assert [metric.value for metric in app.metric] == ["3", "20", "10"]
    assert "Synthetic sample data" in app.info[0].value
    assert len(app.dataframe[0].value) == 3
    print("PASS: Streamlit sample mode, three metrics, three table rows, zero AWS client creation")


def main():
    check_structure()
    check_input_contract()
    check_sdk_reader()
    check_dashboard()
    print("No AWS API calls, Terraform apply, Spark jobs or SQL execution performed")


if __name__ == "__main__":
    main()
