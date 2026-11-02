import json
from pathlib import Path

INVENTORY_PATH = (
    Path(__file__).resolve().parent.parent
    / "config"
    / "bls-series-inventory.json"
)


def load_series_inventory(inventory_path):
    # TODO: Read the JSON file.
    text = Path(inventory_path).read_text(encoding="utf-8")
    inventory = json.loads(text)

    # TODO: Return its "series" list.
    return inventory["series"]


# Purpose: provide config info on what series to injest
if __name__ == "__main__":
    series = load_series_inventory(INVENTORY_PATH)
    print(len(series))