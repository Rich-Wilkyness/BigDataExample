"""Capture a bounded live GBFS sample; do not publish or calculate homework results."""
# Section: Standard-library tools and shared event contract
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import urllib.request
import uuid

from contract import make_event

# Section: Discover the feed rather than fixing its current redirected host
DISCOVERY_URL = 'https://gbfs.citibikenyc.com/gbfs/gbfs.json'


# Section: Fetch one JSON document
def get_json(url):
    """Download JSON, decode it to Python objects, and close the HTTP response."""
    # User-Agent identifies this learning client to the public API.
    request = urllib.request.Request(
        url, headers={'User-Agent': 'BigDataExample-CitiBike-Learning/1.0'}
    )
    # The timeout prevents one stalled request from waiting indefinitely.
    # 'with' closes the response even if JSON parsing raises an exception.
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.load(response)


# Section: Capture a small, traceable snapshot
def capture(output_dir, limit=2, fetch=get_json):
    """Save selected station events and a capture manifest; return that manifest."""
    # fetch is a function argument: live runs download JSON, tests supply local data.
    # This keeps the capture behavior testable without requesting the real API.

    # Step: Protect the sample size and previously saved capture.
    if not 2 <= limit <= 100:
        raise ValueError('Choose 2 through 100 stations for this bounded lab')
    output_dir.mkdir(parents=True, exist_ok=True)
    if (output_dir / 'events.jsonl').exists():
        raise FileExistsError('Use a fresh output directory for each capture')
    # Step: Resolve station_status and check the source version before interpreting fields.
    discovery = fetch(DISCOVERY_URL)
    if discovery.get('version') != '1.1':
        raise ValueError('Review the GBFS adapter: expected discovery version 1.1')
    feeds = {feed['name']: feed['url'] for feed in discovery['data']['en']['feeds']}
    status_url = feeds['station_status']
    status = fetch(status_url)
    if status.get('version') != '1.1':
        raise ValueError('Review the GBFS adapter: expected station_status version 1.1')
    # Capture time is after retrieval, not the station report or broker arrival time.
    ingested_at = datetime.now(timezone.utc).isoformat()
    snapshot_id = str(uuid.uuid4())
    # Step: Select a repeatable ordering within this response, then build events.
    # Sorting does not guarantee a station set stays unchanged between API polls.
    stations = sorted(status['data']['stations'], key=lambda row: str(row['station_id']))
    selected = stations[:limit]
    if len(selected) != limit or len({row['station_id'] for row in selected}) != limit:
        raise ValueError('Insufficient stations or duplicate station IDs in the sample')
    # make_event adds metadata and validates each selected record.
    # All events from this API response share one snapshot_id and ingestion time.
    events = [make_event(row, snapshot_id=snapshot_id, ingested_at=ingested_at,
                         feed_url=status_url, last_updated=status['last_updated'])
              for row in selected]
    # Step: Save raw responses and prepared event files.
    # The list above validates every selected event before these writes begin.
    # File writes themselves are not an atomic multi-file transaction.
    for name, payload in [('gbfs-discovery.json', discovery), ('station-status-raw.json', status)]:
        (output_dir / name).write_text(json.dumps(payload), encoding='utf-8')
    (output_dir / 'events.jsonl').write_text(
        ''.join(json.dumps(event) + '\n' for event in events), encoding='utf-8'
    )
    # A/B files support the first manual CLI exercise; events.jsonl supports batching.
    for label, event in zip(('a', 'b'), events):
        (output_dir / f'station-{label}.json').write_text(json.dumps(event) + '\n', encoding='utf-8')
    # Step: Record what this capture selected so later delivery can be reconciled.
    # A capture manifest is not evidence that AWS accepted or archived the events.
    manifest = {'snapshot_id': snapshot_id, 'ingested_at': ingested_at,
                'source_feed_url': status_url, 'source_version': status['version'],
                'source_last_updated': status['last_updated'], 'ttl': status['ttl'],
                'stations_in_source': len(stations), 'selected_for_lab': len(events),
                'event_ids': [event['event_id'] for event in events]}
    (output_dir / 'capture-manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    return manifest


# Section: Terminal arguments and visible output
def main():
    """Parse --output-dir / --limit, run one capture, and print its manifest."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir', type=Path, required=True)
    parser.add_argument('--limit', type=int, default=2)
    args = parser.parse_args()
    print(json.dumps(capture(args.output_dir, args.limit), indent=2))


# Section: Run only when executed directly, not when imported by a test
if __name__ == '__main__':
    main()
