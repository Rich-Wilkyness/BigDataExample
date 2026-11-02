"""Validate the same five numeric inputs at the inference API boundary."""

import math

FEATURES = ["amount", "hour", "distance_from_home", "new_device", "transactions_last_hour"]


def normalize_features(record):
    if not isinstance(record, dict) or set(record) != set(FEATURES):
        raise ValueError("Supply exactly the five trained feature names, without a label.")
    result = {}
    for name in FEATURES:
        value = record[name]
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value < 0:
            raise ValueError(f"{name} must be a finite nonnegative number.")
        if name in ("hour", "new_device", "transactions_last_hour"):
            if int(value) != value:
                raise ValueError(f"{name} must be an integer.")
            value = int(value)
        else:
            value = float(value)
        result[name] = value
    if result["hour"] > 23 or result["new_device"] not in (0, 1):
        raise ValueError("hour must be 0–23 and new_device must be 0 or 1.")
    return result
