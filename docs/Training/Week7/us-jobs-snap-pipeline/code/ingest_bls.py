import json
from pathlib import Path
from urllib.request import Request, urlopen
from datetime import datetime, timezone
from uuid import uuid4
import hashlib
from urllib.error import HTTPError
import time
import os



# Where is our data located? /data
REQUEST_PATH = (
        Path(__file__).resolve().parent.parent
        / "config"
        / "bls-idaho-2024-request.json"
    )
BLS_ENDPOINT = "https://api.bls.gov/publicAPI/v2/timeseries/data/"

MAX_ATTEMPTS = 3
RETRY_DELAYS = (5, 15)
MAX_RETRY_DELAY = 60

# - Converts request_path to a Path.
# - Reads the file as UTF-8 text.
# - Parses it with json.loads().
# - Returns the resulting dictionary.
def load_request(request_path):

    text = Path(request_path).read_text(encoding="utf-8")
    return json.loads(text)

# - Convert the dictionary to JSON text, then UTF-8 bytes.
# - Build a Request to https://api.bls.gov/publicAPI/v2/timeseries/data/ with method "POST" and header Content-Type: application/json.
# - Open it using urlopen(request, timeout=30) inside a with block.
# - Return response.read() as the original response bytes.
# - Add the runtime key to an outgoing copy, then serialize to JSON bytes.
def fetch_bls(payload):

    # json.loads() does the reverse: JSON text → Python object.
    api_key = os.environ.get("BLS_API_KEY", "").strip()
    if not api_key:
        raise ValueError("BLS_API_KEY is not configured")

    # **payload copies the request fields into a new dictionary. 
    # The original payload stays key-free for your saved plan, manifest, and error metadata.
    request_payload = {
        **payload,
        "registrationkey": api_key,
    }
    body = json.dumps(request_payload).encode("utf-8")

    # create a request
    request = Request(
        BLS_ENDPOINT,
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urlopen(request, timeout=30) as response:
        return response.read()


# defines and prints the path; it doesn’t create directories or call BLS yet.
def get_run_dir():
    ingestion_date = datetime.now(timezone.utc).date().isoformat()
    run_id = uuid4().hex

    capture_dir = (
        Path(__file__).resolve().parent.parent
        / "data"
        / "bronze"
        / "bls"
        / f"ingestion_date={ingestion_date}"
        / f"run_id={run_id}"
    )

    print(capture_dir)
    return capture_dir

# This makes one BLS request and preserves its original response bytes. 
# "xb" creates a new binary file and refuses to overwrite an existing one.
def make_request(capture_dir, payload):
    capture_dir.mkdir(parents=True, exist_ok=False)


    # with is a python statement that: 
    try:
        raw_response = fetch_bls(payload)
    except HTTPError as error:
        failed_at = datetime.now(timezone.utc).isoformat()
        error_record = {
            "failed_at": failed_at,
            "endpoint": BLS_ENDPOINT,
            "request_params": payload,
            "http_status": error.code,
            "reason": str(error.reason),
            "retry_after": error.headers.get("Retry-After"),
            "content_type": error.headers.get("Content-Type"),
            "body_preview": error.read(2048).decode("utf-8", errors="replace"),
        }
        error_path = capture_dir / "error.json"

        with error_path.open("x", encoding="utf-8") as file:
            json.dump(error_record, file, indent=2)

        raise

    retrieved_at = datetime.now(timezone.utc).isoformat()

    response_path = capture_dir / "response.json"
    with response_path.open("xb") as file:
        file.write(raw_response)

    byte_size = len(raw_response)
    print(f"Saved {byte_size} bytes to {response_path}")

    # return dictionary
    return {
        "response_path": response_path,
        "retrieved_at": retrieved_at,
    }

# It should write manifest.json beside response.json, recording:
#    | Information | Source |
#    |---|---|
#    | BLS endpoint | Request URL |
#    | Request parameters | payload |
#    | Retrieval timestamp | capture["retrieved_at"] |
#    | Response filename | capture["response_path"].name |
#    | Byte size and SHA-256 | Saved response bytes |
#    | Ingestion date, run ID, attempt ID | Capture-directory components |

def write_manifest(capture_dir, payload, capture):

    raw_bytes = capture["response_path"].read_bytes()
    checksum = hashlib.sha256(raw_bytes).hexdigest()

    # Here, .parent moves up one directory, .name returns its final component, and .removeprefix() removes the label. Keep attempt_id as a string so "001" retains its leading zeros.
    manifest = {
        "bls_endpoint": BLS_ENDPOINT,
        "request_params": payload,
        "retrieval_ts": capture["retrieved_at"],
        "response_filename": capture["response_path"].name,
        "byte_size": len(raw_bytes),
        "sha256": checksum,
        "ingestion_date": capture_dir.parent.parent.name.removeprefix("ingestion_date="),
        "run_id": capture_dir.parent.name.removeprefix("run_id="),
        "attempt_id": capture_dir.name.removeprefix("attempt_id="),
    }

    response_path = capture_dir / "manifest.json"
    with response_path.open("x", encoding="utf-8") as file:
        json.dump(manifest, file, indent=2)

def run_with_retries(run_dir, payload, max_attempts=MAX_ATTEMPTS):
    # This prevents unsupported attempt counts.
    if not 1 <= max_attempts <= len(RETRY_DELAYS) + 1:
        raise ValueError("max_attempts must fit the configured retry delays")

    for attempt_number in range(1, max_attempts + 1):
        # :03d formats 1 as 001, 2 as 002, and so on.
        attempt_dir = run_dir / f"attempt_id={attempt_number:03d}"

        # The else runs after a successful request. 
        # return stops the loop immediately.
        try: 
            capture = make_request(attempt_dir, payload)
        except HTTPError as error:
            # Retry 503 while attempts remain and Retry-After is absent.
            if error.code != 503 or attempt_number == max_attempts:
                raise
            if error.headers.get("Retry-After") is not None:
                raise
            delay = RETRY_DELAYS[attempt_number - 1]
            time.sleep(delay)
        
        else:
            write_manifest(attempt_dir, payload, capture)
            return capture


# capture_dir = local directory where capture data is stored
# payload = request parameters: which BLS series and years to retrieve
# REQUEST_PATH = local JSON file containing those request parameters
# capture = dictionary containing the saved response path and retrieval timestamp
if __name__ == "__main__":
    payload = load_request(REQUEST_PATH)
    run_dir = get_run_dir()
    run_with_retries(run_dir, payload)
    # capture_dir = get_capture_dir()
    # capture = make_request(capture_dir, payload)
    # write_manifest(capture_dir, payload, capture)
