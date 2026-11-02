"""Run with the lab Boto3 requirement: actual SDK shapes, no AWS calls."""
# Section: SDK stubbing and temporary test-file tools
import contextlib
import io
import json
from pathlib import Path
import sys
import tempfile
from unittest.mock import Mock, patch

import boto3
from botocore.stub import Stubber

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from contract import make_event
import producer


# Section: Exercise the command-line producer with real SDK request validation
def main():
    """Check partial retry and journal output while Stubber intercepts AWS calls."""
    # Step: Prepare the same event bytes the real producer would submit.
    status = json.loads((ROOT / 'fixtures/station-status.json').read_text())
    events = [make_event(row, snapshot_id='sdk-fixture',
                        ingested_at='2026-10-12T19:35:05+00:00',
                        feed_url='https://example.invalid/status', last_updated=status['last_updated'])
              for row in status['data']['stations']]
    requests = [item['request'] for item in next(producer.batches(events))]
    arn = 'arn:aws:kinesis:us-east-2:123456789012:stream/week6-sdk-shape-check'
    # Explicit fake credentials prevent metadata-service/credential-provider calls.
    client = boto3.client('kinesis', region_name='us-east-2',
                          aws_access_key_id='testing', aws_secret_access_key='testing')
    # Step: Save test inputs temporarily and queue expected SDK responses.
    # Stubber compares each request with its expected parameters instead of sending it.
    with tempfile.TemporaryDirectory() as temp, Stubber(client) as stub:
        directory = Path(temp)
        source = directory / 'events.jsonl'
        source.write_text(''.join(json.dumps(event) + '\n' for event in events))
        journal = directory / 'journal.jsonl'
        partial = json.loads((ROOT / 'fixtures/put-records-partial.json').read_text())
        stub.add_response('put_records', partial, {'StreamARN': arn, 'Records': requests})
        # The SDK model marks the optional aggregate counter as min=1; omit it
        # for the all-success stub. Per-entry results determine success.
        stub.add_response('put_records', {'Records': [
            {'ShardId': 'shardId-000000000000', 'SequenceNumber': 'fixture-confirmed-b'}]},
            {'StreamARN': arn, 'Records': [requests[1]]})
        # Step: Replace session creation so main() receives our stubbed client.
        session = Mock()
        session.client.return_value = client
        argv = ['producer.py', '--events', str(source), '--stream-arn', arn,
                '--region', 'us-east-2', '--journal', str(journal)]
        # patch temporarily replaces selected objects, restoring them after the block.
        # The command-line arguments are fake; the publication/journal code is real.
        with patch('boto3.Session', return_value=session), patch.object(sys, 'argv', argv), \
                contextlib.redirect_stdout(io.StringIO()):
            # Default sleep parameter was bound at definition, so replace it explicitly.
            original = producer.publish_batch
            def no_wait(send, batch, emit):
                return original(send, batch, emit, sleep=lambda delay: None)
            with patch('producer.publish_batch', side_effect=no_wait):
                assert producer.main() == 0
        # Step: Check that both expected calls happened and the journal agrees.
        stub.assert_no_pending_responses()
        records = [json.loads(line) for line in journal.read_text().splitlines()]
        assert records[0]['action'] == 'planned'
        assert records[-1]['action'] == 'complete'
        assert records[-1]['confirmed_entries'] == 2
        assert len([entry for entry in records if entry['action'] == 'accepted']) == 2
        assert [entry['event_ids'] for entry in records if entry['action'] == 'attempt'] == [
            [e['event_id'] for e in events], [events[1]['event_id']]]
    print(f'PASS: Boto3 {boto3.__version__} Stubber checked CLI journal flow and failed-entry-only retry; no network.')


# Section: Run this optional check in the environment with Boto3 installed
if __name__ == '__main__':
    main()
