"""Event time comes from GBFS; ingestion time belongs to our producer."""
# Section: Tools for JSON, stable identity, and timestamp validation
import hashlib
import json
from datetime import datetime


# Section: Build one event from one source station record
# Arguments after * must be passed by name, making the different timestamps clear.
def make_event(station, *, snapshot_id, ingested_at, feed_url, last_updated):
    """Return a validated event dictionary with source data and capture metadata."""
    # Hash source content only: a producer retry must not create a new identity.
    identity = {'source_system': 'citibike', 'source_record': station}
    # Sorting dictionary keys gives identical bytes for the same source content.
    # UTF-8 turns JSON text into bytes, which the hash function requires.
    canonical = json.dumps(identity, sort_keys=True, separators=(',', ':')).encode('utf-8')
    # The envelope adds our metadata while source_record retains the original fields.
    # event_id describes source content; snapshot_id describes this particular poll.
    event = {
        'schema_version': 1,
        'source_system': 'citibike',
        'event_id': hashlib.sha256(canonical).hexdigest(),
        'snapshot_id': snapshot_id,
        'source_feed_url': feed_url,
        'source_last_updated': last_updated,
        'ingested_at': ingested_at,
        'station_id': station['station_id'],
        'num_bikes_available': station['num_bikes_available'],
        'num_docks_available': station['num_docks_available'],
        'last_reported': station['last_reported'],
        'source_record': station,
    }
    # Reject invalid selected data before it can be published to the stream.
    validate_event(event)
    return event


# Section: Check the fields this lab relies on
def validate_event(event):
    """Raise ValueError for invalid fields; return normally when checks pass."""
    # A version tells readers which payload contract they should expect.
    if type(event.get('schema_version')) is not int or event['schema_version'] != 1:
        raise ValueError('Unsupported schema_version')
    for field in ('event_id', 'station_id', 'snapshot_id', 'source_system'):
        if not isinstance(event.get(field), str) or not event[field]:
            raise ValueError(f'{field} must be a nonempty string')
    for field in ('num_bikes_available', 'num_docks_available', 'last_reported'):
        # bool is an int subclass in Python, but is not a valid count here.
        if type(event.get(field)) is not int or event[field] < 0:
            raise ValueError(f'{field} must be a nonnegative integer')
    # A timezone prevents the same timestamp being interpreted differently on two hosts.
    timestamp = datetime.fromisoformat(event['ingested_at'])
    if timestamp.tzinfo is None or timestamp.utcoffset() is None:
        raise ValueError('ingested_at must have a timezone')
    # This validation is a bounded lab contract, not a full GBFS/schema registry.


# Section: Read saved JSON Lines for publication
def load_events(path):
    """Read and validate the small saved sample before the producer sends it."""
    # JSON Lines means one complete JSON object per nonempty line.
    # Loading the sample is intentional here; an unbounded stream needs bounded reads.
    with open(path, encoding='utf-8') as source:
        events = [json.loads(line) for line in source if line.strip()]
    if not events:
        raise ValueError('No events to publish')
    for event in events:
        validate_event(event)
    return events
