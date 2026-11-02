# Live station status: theory

[Step-by-step guide](README.md)

## Data enrichment

`load_citibike.py` supplies relatively static station metadata from the export. `live_status.py` reads the matching local status snapshot by default and inner-joins it on `station_id`. Optional `--live` mode downloads a current public API response instead. The resulting DataFrame combines station names and locations with current availability.

The inner join retains only matching station IDs, so the matched count can be smaller than either input count. This is data ingestion and enrichment; no model is trained. One current snapshot does not provide the repeated observations needed to evaluate a future-availability forecast.

## Data boundary

Default mode uses matching saved information and status snapshots. Optional live mode combines saved metadata with a current API response. The exported status file preserves `num_bikes_available` and `num_docks_available`; optional live mode expects the GBFS `data.stations` envelope. Neither mode collects a time series; the default snapshot is already stored locally.
