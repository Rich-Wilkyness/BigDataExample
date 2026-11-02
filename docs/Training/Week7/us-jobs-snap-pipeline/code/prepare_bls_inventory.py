import json
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parent.parent
EVIDENCE_PATH = PROJECT_DIR / "evidence" / "state-series-verification.json"
CONFIG_PATH = PROJECT_DIR / "config" / "bls-series-inventory.json"

# unsupported data -> not collected
EXCLUDED_SERIES_IDS = {
    "SMS10000002000000001",  # Delaware construction
    "SMS15000002000000001",  # Hawaii construction
}

SERIES_FIELDS = (
    "series_id",
    "state_fips",
    "state_name",
    "program",
    "measure",
    "industry_code",
    "industry_name",
    "units",
    "seasonal_adjustment",
)

def prepare_inventory(evidence_path):
    # TODO: Read the file as UTF-8.
    text = Path(evidence_path).read_text("utf-8")

    # TODO: Parse the JSON.
    evidence = json.loads(text)

    # TODO: Return the dictionary's "series" list.
    return evidence["series"]


def select_series(candidates, excluded_ids):
    # The first i means “keep this entire series dictionary.” 
    # The if decides whether to keep it.
    selected = [
        i
        for i in candidates
        if i["series_id"] not in excluded_ids 
    ]
    return selected

def build_series_records(selected):
    # Return a new list of dictionaries.
    # For each selected series, copy only the keys in SERIES_FIELDS.
    records = []

    for series in selected:
        record = {
            "series_id": series["series_id"],
            "state_fips": series["state_fips"],
            "state_name": series["state_name"],
            "program": series["program"],
            "measure": series["measure"],
            "industry_code": series["industry_code"],
            "industry_name": series["industry_name"],
            "units": series["units"],
            "seasonal_adjustment": series["seasonal_adjustment"],
        }
        records.append(record)
    return records

# Purpose:
# Generate config/bls-series-inventory.json with the selected series,
# their metadata, and documented exclusions.
# Run when deliberately changing ingestion scope, config fields,
# or series definitions/availability after verification.
# Review the input evidence and existing config before regenerating.
# bls_inventory.py reads this config during normal ingestion.

# TODO:
# - Read the existing evidence inventory.
# - Select the 248 supported series, excluding the two unsupported construction IDs.
# - Keep series-definition metadata rather than historical observations/statistics.
# - Write the selected "series" list and explicit exclusions into your config.
if __name__ == "__main__":

    candidates = prepare_inventory(EVIDENCE_PATH)
    print(len(candidates))
    selected = select_series(candidates, EXCLUDED_SERIES_IDS)
    print(len(selected))
    records = build_series_records(selected)
    print(len(records))
    print(records[0])

    config = {
        "source_inventory": "evidence/state-series-verification.json",
        "series": records,
        "excluded_series": [
            # Add one dictionary per excluded series:
            # series_id and reason
            {
                "series_id": "SMS10000002000000001",
                "reason": "Standalone construction series unavailable for Delaware",
            },
            {
                "series_id": "SMS15000002000000001",
                "reason": "Standalone construction series unavailable for Hawaii",  
            }
        ],
    }
    if CONFIG_PATH.exists() and CONFIG_PATH.stat().st_size > 0:
        raise FileExistsError(f"Config already contains data: {CONFIG_PATH}")
    with CONFIG_PATH.open("w", encoding="utf-8") as file:
        json.dump(config, file, indent=2)