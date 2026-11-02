"""Freeze training inputs and preserve the same validation/test examples.

The collector and this reader cooperate using POSIX file locks (macOS/Linux).
This is a local teaching contract, not a distributed dataset transaction.
"""

import fcntl
import hashlib
import json
import os
import tempfile
from pathlib import Path

import pandas as pd
from sklearn.model_selection import train_test_split

FEATURES = ["amount", "hour", "distance_from_home", "new_device", "transactions_last_hour"]


def snapshot_csv(source, directory):
    """Hold a reader lock while copying bytes so a writer cannot split a row."""
    with open(source, "rb") as stream:
        fcntl.flock(stream, fcntl.LOCK_SH)
        try:
            content = stream.read()
        finally:
            fcntl.flock(stream, fcntl.LOCK_UN)
    digest = hashlib.sha256(content).hexdigest()
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"snapshot-{digest}.csv"
    if not path.exists():
        path.write_bytes(content)
    return path, digest


def clean_data(path):
    frame = pd.read_csv(path, dtype={"transaction_id": "string"})
    required = ["transaction_id", *FEATURES, "is_fraud"]
    if not set(required).issubset(frame):
        raise ValueError("Training CSV is missing required transaction columns.")
    frame = frame.dropna(subset=required)
    # Replays are acceptable only if the same business ID carries the same data.
    if frame.groupby("transaction_id")[[*FEATURES, "is_fraud"]].nunique().gt(1).any().any():
        raise ValueError("A replayed transaction ID has conflicting features or labels.")
    frame = frame.drop_duplicates("transaction_id").sort_values("transaction_id").reset_index(drop=True)
    if len(frame) < 100 or set(frame["is_fraud"].unique()) != {0, 1}:
        raise ValueError("Collect at least 100 complete transactions with both labels.")
    if frame["is_fraud"].value_counts().min() < 5:
        raise ValueError("Collect at least five examples of each class before creating evaluation sets.")
    return frame


def evaluation_sets(frame, directory):
    """Create two fixed exam papers once, then exclude their IDs from all training."""
    directory = Path(directory)
    if not directory.exists():
        # Reserve the final 20% test paper first; split another 20% for validation.
        rest, test = train_test_split(frame, test_size=.2, stratify=frame["is_fraud"], random_state=42)
        _, validation = train_test_split(rest, test_size=.25, stratify=rest["is_fraud"], random_state=42)
        directory.parent.mkdir(parents=True, exist_ok=True)
        temporary = Path(tempfile.mkdtemp(prefix=".evaluation-", dir=directory.parent))
        validation.to_csv(temporary / "validation.csv", index=False)
        test.to_csv(temporary / "test.csv", index=False)
        manifest = {"initial_rows": len(frame), "seed": 42, "features": FEATURES,
                    "sha256": {name: hashlib.sha256((temporary / name).read_bytes()).hexdigest()
                               for name in ["validation.csv", "test.csv"]}}
        (temporary / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
        # Publish the completed directory together. One trainer at a time is the
        # documented local workflow; parallel model-training jobs are out of scope.
        os.rename(temporary, directory)
    manifest = json.loads((directory / "manifest.json").read_text())
    papers = {}
    for name in ("validation.csv", "test.csv"):
        path = directory / name
        if hashlib.sha256(path.read_bytes()).hexdigest() != manifest["sha256"][name]:
            raise ValueError(f"Fixed evaluation data changed: {path}")
        # Reading test IDs is necessary to exclude them; no test metric is used
        # for candidate fitting or selection. Final evaluation is a separate step.
        papers[name] = pd.read_csv(path, dtype={"transaction_id": "string"})
    excluded = set(papers["validation.csv"]["transaction_id"]) | set(papers["test.csv"]["transaction_id"])
    training = frame.loc[~frame["transaction_id"].isin(excluded)].copy()
    if training["is_fraud"].nunique() < 2:
        raise ValueError("Training partition needs both classes.")
    return training, papers["validation.csv"], manifest
