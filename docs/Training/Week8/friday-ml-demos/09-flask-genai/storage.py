"""SQLite storage for the reconstructed classroom dashboard."""

import json
import math
import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path

# The same five model inputs are used in training, inference, and explanation.
# Keeping this list explicit prevents unrelated event fields becoming inputs.
FEATURES = (
    "amount", "hour", "distance_from_home", "new_device", "transactions_last_hour"
)


# Default to a database beside this file. Flask, collector, and sample loader
# share this function so their working directories cannot silently split data.
def database_path():
    return Path(os.getenv("FRAUD_DB_PATH", Path(__file__).resolve().with_name("fraud.sqlite3")))


# A with block commits on success or rolls back on failure, then closes the
# connection. Each operation gets its own connection; timeout bounds waits
# while the collector and dashboard briefly contend for SQLite access.
@contextmanager
def connect(path):
    connection = sqlite3.connect(path, timeout=10)
    connection.row_factory = sqlite3.Row
    try:
        with connection:
            yield connection
    finally:
        connection.close()


# WAL allows readers alongside a writer. The unique business key makes
# replayed transaction/model pairs harmless to counts. Initialization is
# idempotent: an existing table and its rows are preserved.
def initialize(path):
    with connect(path) as db:
        db.execute("PRAGMA journal_mode=WAL")
        db.execute("""
            CREATE TABLE IF NOT EXISTS predictions (
                id INTEGER PRIMARY KEY,
                transaction_id TEXT NOT NULL,
                model_version TEXT NOT NULL,
                event_time TEXT,
                prediction_time TEXT,
                predicted_fraud INTEGER NOT NULL CHECK (predicted_fraud IN (0, 1)),
                actual_fraud INTEGER NOT NULL CHECK (actual_fraud IN (0, 1)),
                features TEXT NOT NULL,
                UNIQUE(transaction_id, model_version)
            )
        """)


# Validate the wire contract before storage. A missing legacy feature set is
# allowed, but present values must be usable numeric inputs; missing labels
# are not silently interpreted as legitimate transactions.
def validate_event(event):
    if not isinstance(event, dict):
        raise ValueError("Prediction must be a JSON object.")
    if not isinstance(event.get("transaction_id"), str) or not event["transaction_id"].strip():
        raise ValueError("transaction_id must be a nonempty string.")
    version = event.get("model_version")
    if isinstance(version, bool) or not isinstance(version, (str, int)) or not str(version).strip():
        raise ValueError("model_version must be a nonempty string or integer.")
    for field in ("predicted_fraud", "actual_fraud"):
        if not isinstance(event.get(field), (bool, int)) or event[field] not in (0, 1):
            raise ValueError(f"{field} must be 0 or 1.")
    features = event.get("features", {})
    if not isinstance(features, dict):
        raise ValueError("features must be an object when supplied.")
    # Older events may have no features; display them without inventing values.
    # Keep only model features, not arbitrary extra event keys. This also gives
    # the explanation prompt a small, known evidence structure.
    features = {name: features[name] for name in FEATURES if name in features}
    for name, value in features.items():
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
            raise ValueError(f"{name} must be a finite number.")
        if value < 0:
            raise ValueError(f"{name} cannot be negative.")
        if name in ("hour", "new_device", "transactions_last_hour") and value != int(value):
            raise ValueError(f"{name} must be an integer.")
        if name == "hour" and value > 23:
            raise ValueError("hour must be between 0 and 23.")
        if name == "new_device" and value not in (0, 1):
            raise ValueError("new_device must be 0 or 1.")
    for field in ("event_time", "prediction_time"):
        if event.get(field) is not None and not isinstance(event[field], str):
            raise ValueError(f"{field} must be a string when supplied.")
    return features


# SQL placeholders separate data from SQL syntax. ON CONFLICT preserves
# the first stored record for an identity/version pair, so replays do not
# change cumulative counts or overwrite evidence with a later duplicate.
def save_prediction(path, event):
    features = validate_event(event)
    with connect(path) as db:
        cursor = db.execute("""
            INSERT INTO predictions (
                transaction_id, model_version, event_time, prediction_time,
                predicted_fraud, actual_fraud, features
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(transaction_id, model_version) DO NOTHING
        """, (
            event["transaction_id"], str(event["model_version"]),
            event.get("event_time"), event.get("prediction_time"),
            int(event["predicted_fraud"]), int(event["actual_fraud"]),
            json.dumps(features, allow_nan=False),
        ))
        return cursor.rowcount == 1


# Convert a database row to a browser-ready object. Compute correctness
# from labels instead of trusting an incoming correct flag. can_explain
# requires all five features; zero is a valid value, not a missing marker.
def decode(row):
    event = dict(row)
    event["features"] = json.loads(event["features"])
    event["correct"] = event["predicted_fraud"] == event["actual_fraud"]
    event["can_explain"] = all(name in event["features"] for name in FEATURES)
    return event


# Fetch one selected row by its local integer ID. Return None for a missing
# ID so Flask can report 404 without making any provider request.
def get_prediction(path, prediction_id):
    with connect(path) as db:
        row = db.execute("SELECT * FROM predictions WHERE id = ?", (prediction_id,)).fetchone()
    return decode(row) if row else None


# The table is capped at 100 recent arrivals, but totals cover the entire
# stored dataset across versions. Empty-set accuracy is unknown (None),
# not 0% or 100%. Flask serializes None to JSON null.
def dashboard_data(path):
    with connect(path) as db:
        rows = db.execute("SELECT * FROM predictions ORDER BY id DESC LIMIT 100").fetchall()
        summary = db.execute("""
            SELECT COUNT(*) AS processed,
                   COALESCE(SUM(predicted_fraud), 0) AS flagged,
                   COALESCE(SUM(predicted_fraud = actual_fraud), 0) AS correct
            FROM predictions
        """).fetchone()
    stats = dict(summary)
    stats["accuracy"] = stats["correct"] / stats["processed"] if stats["processed"] else None
    return {"stats": stats, "predictions": [decode(row) for row in rows]}
