"""Read the local AWS export without requiring a SQL database or AWS session."""

import os
from pathlib import Path

import numpy as np
import pandas as pd

# Resolve the repo path from this source file, independent of the shell cwd.
DATA_DIRECTORY = Path(__file__).resolve().parents[5] / "data/raw/week8-friday-citibike"


def read_table(path):
    path = Path(path).expanduser().resolve()
    if not path.is_file():
        raise FileNotFoundError(f"Local station data not found: {path}. Follow data-preparation.md first.")
    if path.suffix.lower() == ".csv":
        # IDs are identifiers, not numbers: preserve leading zeros in CSV input.
        frame = pd.read_csv(path, dtype={"station_id": "string"})
    elif path.suffix.lower() == ".parquet":
        frame = pd.read_parquet(path)
    else:
        raise ValueError("Station input must be a .csv or .parquet file.")
    if "station_id" not in frame or frame["station_id"].isna().any():
        raise ValueError("Every row needs a station_id.")
    frame["station_id"] = frame["station_id"].astype("string")
    if frame["station_id"].str.strip().eq("").any() or frame["station_id"].duplicated().any():
        raise ValueError("Expected exactly one nonempty station_id per row.")
    return frame


def load_stations(*, require_capacity=False):
    path = Path(os.getenv("CITIBIKE_STATIONS_PATH", DATA_DIRECTORY / "stations.csv"))
    frame = read_table(path)
    required = {"station_name", "latitude", "longitude", "capacity"}
    if not required.issubset(frame):
        raise ValueError(f"Missing station columns: {sorted(required - set(frame))}")
    for name in ("latitude", "longitude", "capacity"):
        frame[name] = pd.to_numeric(frame[name], errors="raise")
        if np.isinf(frame[name].dropna()).any():
            raise ValueError(f"Infinite value in {name}.")
    if frame["latitude"].dropna().abs().gt(90).any() or frame["longitude"].dropna().abs().gt(180).any():
        raise ValueError("Coordinates fall outside latitude/longitude bounds.")
    if frame["capacity"].dropna().lt(0).any():
        raise ValueError("Station capacity cannot be negative.")
    if require_capacity:
        # Zero/missing capacity is excluded from this prediction task, not filled.
        frame = frame.loc[frame["capacity"].gt(0) & frame[["latitude", "longitude"]].notna().all(axis=1)].copy()
    print(f"Loaded {len(frame)} stations from {path}")
    return frame


def load_status():
    path = Path(os.getenv("CITIBIKE_STATUS_PATH", DATA_DIRECTORY / "station-status.csv"))
    frame = read_table(path)
    for name in ("num_bikes_available", "num_docks_available"):
        if name not in frame:
            raise ValueError(f"Missing status column: {name}")
        frame[name] = pd.to_numeric(frame[name], errors="raise")
        if frame[name].isna().any() or not np.isfinite(frame[name]).all() or frame[name].lt(0).any():
            raise ValueError(f"Invalid availability measure: {name}")
    return frame
