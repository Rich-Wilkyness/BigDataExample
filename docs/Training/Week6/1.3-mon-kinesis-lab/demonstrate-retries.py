"""Deterministic local failure demonstration; no credentials, network, or boto3."""
# Section: Local fixture and shared producer tools
from collections import Counter
import json
from pathlib import Path

from contract import make_event
from producer import AmbiguousWrite, batches, publish_batch

ROOT = Path(__file__).parent


# Section: Build two events and simulate a three-request failure timeline
def run_demo(emit=print):
    """Run the real retry algorithm against a fake service and return its summary."""
    # Step: Use saved synthetic inputs so every run has the same starting data.
    status = json.loads((ROOT / 'fixtures/station-status.json').read_text())
    events = [make_event(row, snapshot_id='fixture-snapshot',
                        ingested_at='2026-10-12T19:35:05+00:00',
                        feed_url='https://example.invalid/station-status.json',
                        last_updated=status['last_updated']) for row in status['data']['stations']]
    partial = json.loads((ROOT / 'fixtures/put-records-partial.json').read_text())
    # calls = requests sent; stored = what the fake service accepted.
    # delays collects requested waits so this demonstration never actually sleeps.
    calls, stored, delays = [], [], []

    # Step: Stand in for Kinesis; behavior depends on which attempt this is.
    def send(records):
        """Simulate partial success, a lost reply, and a successful retry."""
        calls.append(records)
        ids = [json.loads(record['Data'])['event_id'] for record in records]
        if len(calls) == 1:
            stored.append(ids[0])  # A accepted, B failed, despite HTTP 200.
            return partial
        if len(calls) == 2:
            stored.extend(ids)  # Pretend Kinesis accepted B but its reply was lost.
            raise AmbiguousWrite()
        # Request three accepts B again: the first acceptance was not acknowledged.
        stored.extend(ids)
        return {'FailedRecordCount': 0, 'Records': [
            {'ShardId': 'shardId-000000000000', 'SequenceNumber': 'fixture-sequence-3'}]}

    # Step: Reuse the actual producer algorithm with fake send, sleep, and randomness.
    # next() takes the one small batch; lambda chooses a repeatable half-range delay.
    confirmed = publish_batch(send, next(batches(events)), emit,
                              sleep=delays.append, uniform=lambda low, high: high / 2)
    # The retry uses only B, with exactly the same bytes on both later attempts.
    assert [len(call) for call in calls] == [2, 1, 1]
    assert calls[0][1] == calls[1][0] == calls[2][0]
    assert confirmed == 2 and len(stored) == 3 and len(set(stored)) == 2
    # Step: Compare what the producer can confirm with what the service really stored.
    return {'http_status_on_partial_success': partial['ResponseMetadata']['HTTPStatusCode'],
            'request_sizes': [len(call) for call in calls],
            'confirmed_logical_entries': confirmed, 'simulated_stored_records': len(stored),
            'distinct_event_ids': len(set(stored)), 'stored_counts': dict(Counter(stored)),
            'backoff_seconds': delays}


# Section: Print the timeline first, then its outcome
def main():
    """Show each journal-style action and the final reconciliation summary."""
    result = run_demo(emit=lambda entry: print(json.dumps(entry)))
    print(json.dumps(result, indent=2))


# Section: Terminal entry point
if __name__ == '__main__':
    main()
