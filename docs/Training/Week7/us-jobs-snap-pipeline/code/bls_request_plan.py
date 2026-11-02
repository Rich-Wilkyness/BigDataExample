from bls_inventory import INVENTORY_PATH, load_series_inventory
import json
import hashlib

BATCH_SIZE = 25
MAX_YEARS = 10
START_YEAR = 2015
END_YEAR = 2025
PLAN_PATH = (
    INVENTORY_PATH.parent
    / f"bls-historical-plan-{START_YEAR}-{END_YEAR}.json"
)

def batch_series(series, batch_size=BATCH_SIZE):
    # reject invalid sizes
    if batch_size <= 0:
        raise ValueError("batch_size must be positive")
    
    # Extract the series_id strings.
    series_ids = [record["series_id"] for record in series]

    # Split them into lists of at most batch_size items.
    batches = []
    # Each iteration keeps the first batch and replaces series_ids with the remaining IDs.
    while series_ids:
        split_ids = series_ids[:batch_size]
        batches.append(split_ids)
        series_ids = series_ids[batch_size:]

    # Return those lists.
    return batches

def build_year_windows(start_year, end_year, max_years=MAX_YEARS):
    if max_years <= 0 or start_year > end_year:
        raise ValueError("Invalid year range or window size")

    windows = []
    current_year = start_year
    while current_year <= end_year:
        window_end = min(current_year + max_years - 1, end_year)
        windows.append((current_year, window_end))
        current_year = window_end + 1
    return windows

def build_request_payloads(batches, windows):
    payloads = []
    for b in batches:
        for start_year, end_year in windows:
            p = {
                "seriesid": b,
                "startyear": str(start_year),
                "endyear": str(end_year),
            }
            payloads.append(p)
    return payloads

# sort_keys=True gives dictionary keys a consistent order. SHA-256 turns those bytes into a repeatable identifier.
def build_request_id(payload):
    text = json.dumps(payload, sort_keys=True)
    raw_bytes = text.encode("utf-8")
    return hashlib.sha256(raw_bytes).hexdigest()

def build_work_items(payloads):
    work_items = []
    for payload in payloads:
        p = {
            "request_id": build_request_id(payload),
            "payload": payload,
        }
        work_items.append(p)
    return work_items
        
if __name__ == "__main__":
    series = load_series_inventory(INVENTORY_PATH)
    batches = batch_series(series)
    windows = build_year_windows(START_YEAR, END_YEAR)
    payloads = build_request_payloads(batches, windows)
    work_items = build_work_items(payloads)
    plan = {
        "source": "bls",
        "mode": "historical",
        "start_year": START_YEAR,
        "end_year": END_YEAR,
        "series_inventory": INVENTORY_PATH.name,
        "series_inventory_sha256": hashlib.sha256(
            INVENTORY_PATH.read_bytes()
        ).hexdigest(),
        "work_items": work_items,
    }
    with PLAN_PATH.open("x", encoding="utf-8") as file:
        json.dump(plan, file, indent=2)
        

    # print(len(batches))
    # print([len(batch) for batch in batches])
    # print(windows)
    # print(len(payloads))
    # print(payloads[0])
    # print(build_request_id(payloads[0]))
    # print(build_request_id(payloads[0]))
    # print(len(work_items))
    # print(work_items[0])
    print(PLAN_PATH)
