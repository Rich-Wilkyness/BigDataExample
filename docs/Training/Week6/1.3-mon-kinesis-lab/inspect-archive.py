"""Inspect archived JSON Lines by business identity, not object count."""
# Section: File reading and counting tools
from collections import Counter
from pathlib import Path
import argparse
import json


# Section: Count archived events and distinguish repeated identities
def inspect(directory):
    """Return raw count, distinct identity count, and occurrences per identity."""
    if not directory.is_dir():
        raise FileNotFoundError(directory)
    # Counter maps each event_id to the number of times it was observed.
    counts = Counter()

    # Firehose may create subdirectories and batch many events into each file.
    # Walk all archive files and read one JSON object per nonempty line.
    # This small lab loads each file as text; large archives need bounded readers.
    for path in directory.rglob('*'):
        if path.is_file():
            for line in path.read_text().splitlines():
                if line.strip():
                    event = json.loads(line)
                    counts[event['event_id']] += 1
    # sum counts every appearance; len counts different business identities.
    # Report duplicates for investigation instead of silently deleting them.
    return {'raw_records': sum(counts.values()), 'unique_event_ids': len(counts),
            'counts_by_event': dict(counts)}


# Section: Terminal arguments and a readable JSON summary
def main():
    """Inspect only the supplied local archive directory; make no cloud calls."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('directory', type=Path)
    args = parser.parse_args()
    print(json.dumps(inspect(args.directory), indent=2))


# Section: Terminal entry point
if __name__ == '__main__':
    main()
