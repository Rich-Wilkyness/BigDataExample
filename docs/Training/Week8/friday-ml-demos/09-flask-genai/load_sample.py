"""Load labeled fixtures without running Kafka, a classifier, or OpenAI."""

import json
from pathlib import Path

from storage import database_path, initialize, save_prediction


def main():
    path = database_path()
    initialize(path)
    # These four fixed records intentionally cover TP, TN, FP, and FN. They
    # preview the UI without pretending a real classifier produced them.
    events = json.loads(Path(__file__).with_name("sample-predictions.json").read_text())
    # Use the same persistence/validation path as the live collector. Re-running
    # the loader is safe because the transaction/model keys are unchanged.
    inserted = sum(save_prediction(path, event) for event in events)
    print(f"Loaded {inserted} sample records into {path} (model version: sample).")


# Importing this file has no side effects; run it explicitly to load fixtures.
if __name__ == "__main__":
    main()
