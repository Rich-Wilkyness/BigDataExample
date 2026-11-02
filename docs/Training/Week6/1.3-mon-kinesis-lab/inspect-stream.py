"""Decode saved GetRecords output and expose the broker arrival timestamp."""
# Section: Tools for saved CLI response files
import argparse
import base64
import json
from pathlib import Path


# Section: Decode stream bytes while keeping transport metadata visible
def decode(response):
    """Yield one dictionary per record: stream position, arrival time, and event."""
    # CLI JSON represents Data as base64. Decode base64 to bytes, bytes to UTF-8
    # text, then JSON text to a Python dictionary. This is decoding, not decryption.
    # Keep broker arrival separate from timestamps supplied inside the event.
    for record in response['Records']:
        yield {'sequence_number': record['SequenceNumber'],
               'broker_arrival_time': record.get('ApproximateArrivalTimestamp'),
               'event': json.loads(base64.b64decode(record['Data']).decode('utf-8'))}


# Section: Read one response file and print its decoded records
def main():
    """Inspect a saved response without making another AWS read."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('response', type=Path)
    args = parser.parse_args()
    response = json.loads(args.response.read_text())
    for record in decode(response):
        print(json.dumps(record))


# Section: Terminal entry point
if __name__ == '__main__':
    main()
