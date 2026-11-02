"""Bounded failure tests, not evidence of AWS durability or database behavior."""
# Section: Standard-library test tools and access to lab modules
import base64
import copy
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from capture import capture
from contract import make_event, validate_event
from producer import AmbiguousWrite, PublishIncomplete, batches, publish_batch


# Section: Load scripts with kebab-case filenames for local inspection tests
def module(name):
    """Import a script by path without running its terminal entry point."""
    spec = importlib.util.spec_from_file_location(name.replace('-', '_'), ROOT / f'{name}.py')
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


# Section: Failure and data-contract checks
class RecoveryTests(unittest.TestCase):
    """Each test checks an observable behavior across a failure or data boundary."""
    # Step: Start each test with a fresh pair of synthetic station events.
    def setUp(self):
        self.status = json.loads((ROOT / 'fixtures/station-status.json').read_text())
        self.events = [make_event(row, snapshot_id='snapshot-one',
                                 ingested_at='2026-10-12T19:35:05+00:00',
                                 feed_url='https://example.invalid/status.json', last_updated=1791833705)
                       for row in self.status['data']['stations']]

    # Retry behavior: partial success must not resend A; lost replies can duplicate B.
    def test_partial_success_and_lost_reply(self):
        result = module('demonstrate-retries').run_demo(emit=lambda entry: None)
        self.assertEqual(result['request_sizes'], [2, 1, 1])
        self.assertEqual(result['simulated_stored_records'], 3)
        self.assertEqual(result['distinct_event_ids'], 2)

    def test_exhaustion_is_bounded_and_reports_unconfirmed_ids(self):
        calls, delays, logs = [], [], []
        def send(records):
            calls.append(records)
            raise AmbiguousWrite()
        with self.assertRaises(PublishIncomplete) as raised:
            publish_batch(send, next(batches(self.events)), logs.append, max_attempts=3,
                          sleep=delays.append, uniform=lambda low, high: high)
        self.assertEqual(len(calls), 3)
        self.assertEqual(delays, [0.25, 0.5])
        self.assertEqual(raised.exception.event_ids, [e['event_id'] for e in self.events])
        self.assertEqual(logs[-1]['action'], 'exhausted')

    def test_unknown_record_error_stops_instead_of_looping(self):
        calls = []
        def send(records):
            calls.append(records)
            return {'Records': [{'ErrorCode': 'UnexpectedError'} for _ in records]}
        with self.assertRaises(PublishIncomplete):
            publish_batch(send, next(batches(self.events)), lambda entry: None)
        self.assertEqual(len(calls), 1)

    def test_response_mismatch_does_not_silently_drop_an_entry(self):
        with self.assertRaises(ValueError):
            publish_batch(lambda records: {'Records': []}, next(batches(self.events)), lambda entry: None)

    # Identity behavior: new capture metadata alone must not create a new observation.
    def test_identity_excludes_capture_time_but_includes_changed_source_content(self):
        station = copy.deepcopy(self.status['data']['stations'][0])
        recaptured = make_event(station, snapshot_id='snapshot-two',
                                ingested_at='2026-10-12T19:36:05+00:00',
                                feed_url='https://example.invalid/status.json', last_updated=1791833765)
        self.assertEqual(recaptured['event_id'], self.events[0]['event_id'])
        station['num_bikes_available'] += 1
        changed = make_event(station, snapshot_id='snapshot-three',
                             ingested_at='2026-10-12T19:37:05+00:00',
                             feed_url='https://example.invalid/status.json', last_updated=1791833825)
        self.assertNotEqual(changed['event_id'], recaptured['event_id'])
        self.assertEqual(changed['last_reported'], recaptured['last_reported'])

    def test_invalid_counts_and_naive_ingestion_time_are_rejected(self):
        for field, value in [('num_bikes_available', -1), ('num_docks_available', True),
                             ('ingested_at', '2026-10-12T19:35:05')]:
            with self.subTest(field=field):
                event = dict(self.events[0], **{field: value})
                with self.assertRaises(ValueError):
                    validate_event(event)

    # Capture behavior: preserve source content and protect earlier evidence.
    def test_capture_preserves_source_and_refuses_overwrite(self):
        discovery = {'version': '1.1', 'data': {'en': {'feeds': [
            {'name': 'station_status', 'url': 'https://example.invalid/status.json'}]}}}
        def fetch(url):
            return copy.deepcopy(discovery if 'gbfs.json' in url else self.status)
        with tempfile.TemporaryDirectory() as temp:
            directory = Path(temp)
            manifest = capture(directory, fetch=fetch)
            event = json.loads((directory / 'station-a.json').read_text())
            self.assertEqual(event['source_record'], self.status['data']['stations'][0])
            self.assertEqual(manifest['selected_for_lab'], 2)
            with self.assertRaises(FileExistsError):
                capture(directory, fetch=fetch)

    def test_oversized_event_rejected_before_send(self):
        event = dict(self.events[0], padding='x' * 300_000)
        with self.assertRaises(ValueError):
            list(batches([event]))

    # Inspection behavior: keep transport time separate and count duplicate identities.
    def test_stream_time_and_archive_identity_have_distinct_roles(self):
        event = self.events[0]
        data = base64.b64encode(json.dumps(event).encode()).decode()
        decoded = list(module('inspect-stream').decode({'Records': [{
            'Data': data, 'SequenceNumber': 'position-one', 'ApproximateArrivalTimestamp': 1791833710}]}))
        self.assertEqual(decoded[0]['broker_arrival_time'], 1791833710)
        self.assertEqual(decoded[0]['event']['last_reported'], event['last_reported'])
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp)
            (path / 'events.jsonl').write_text(''.join(json.dumps(e) + '\n' for e in self.events + [event]))
            result = module('inspect-archive').inspect(path)
            self.assertEqual((result['raw_records'], result['unique_event_ids']), (3, 2))


# Section: Run the checks directly or through unittest discovery
if __name__ == '__main__':
    unittest.main()
