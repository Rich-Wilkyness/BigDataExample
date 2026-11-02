"""Join one current availability snapshot to stored station metadata."""

import requests
import pandas as pd

from load_citibike import df

# This is the endpoint captured in class. The source must still provide
# data.stations and the availability field names used below.
import argparse
from shared.station_data import load_status

parser = argparse.ArgumentParser()
parser.add_argument("--live", action="store_true", help="Fetch the current public GBFS feed instead of the local snapshot")
args = parser.parse_args()
if args.live:
    # Optional live mode needs internet but no API key. This endpoint is the
    # class-captured GBFS 1.1 contract; default mode uses the verified AWS export.
    response = requests.get("https://gbfs.lyft.com/gbfs/1.1/bkn/en/station_status.json", timeout=30)
    response.raise_for_status()
    status = pd.DataFrame(response.json()["data"]["stations"])
    status["station_id"] = status["station_id"].astype("string")
else:
    status = load_status()

print("Status records:", len(status))
print(status.columns.tolist())

# Join the static metadata and current measurements using station_id.
# An inner join keeps only matching IDs; unmatched stations disappear.
# This assumes compatible ID types and one row per station in each input.
combined = df.merge(
    status,
    on="station_id",
    how="inner",
    validate="one_to_one"
)

# Compare source and matched counts before trusting the enrichment.
# This script prints one snapshot; it neither persists history nor fits ML.
print("Matched stations:", len(combined))

print(
    combined[
        [
            "station_name",
            "num_bikes_available",
            "num_docks_available"
        ]
    ].head(10)
)
