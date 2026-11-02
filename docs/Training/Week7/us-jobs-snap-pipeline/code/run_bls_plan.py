from pathlib import Path
import json
import hashlib

PLAN_PATH = (
    Path(__file__).resolve().parent.parent
    / "config"
    / "bls-historical-plan-2015-2025.json"
)

def load_historical_plan(plan_path):
    # Read the plan JSON.
    text = Path(plan_path).read_text(encoding="utf-8")
    plan = json.loads(text)
    inventory_path = (
        Path(plan_path).parent / plan["series_inventory"]
    )
    check_hash = hashlib.sha256(
        inventory_path.read_bytes()
    ).hexdigest()

    if check_hash != plan["series_inventory_sha256"]:
        raise ValueError("Inventory differs from the saved plan")

    return plan
    # Resolve its series_inventory filename beside the plan.
    # Calculate that inventory file's SHA-256.
    # Raise ValueError if it differs from series_inventory_sha256.
    # Return the plan.

if __name__ == "__main__":
    plan = load_historical_plan(PLAN_PATH)
    print(len(plan["work_items"]))