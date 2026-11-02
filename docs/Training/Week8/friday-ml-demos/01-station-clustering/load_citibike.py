"""Read the local CSV/Parquet station snapshot; no SQL or AWS session needed."""

from pathlib import Path
import sys

# Share the file-input contract while keeping each demo's own runnable script.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from shared.station_data import load_stations

# Importing this loader reads the local snapshot and exposes df to this demo.
df = load_stations()
print(df.head())
print(df.dtypes)
