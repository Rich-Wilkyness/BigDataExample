"""PutRecords partial retry: successful HTTP status is not per-event success.

Only main() imports boto3. The retry algorithm can run against a local fake.
"""
# Section: Local helpers; the AWS SDK is imported only by main()
import argparse
from contextlib import closing
from datetime import datetime, timezone
import json
from pathlib import Path
import random
import sys
import time

from contract import load_events

# Section: Batch limits and errors that can be retried
# Conservative teaching bounds, deliberately below AWS request limits.
MAX_BATCH_RECORDS = 100
MAX_BATCH_BYTES = 1024 * 1024
MAX_EVENT_BYTES = 256 * 1024
RETRYABLE_RECORD_ERRORS = {'ProvisionedThroughputExceededException', 'InternalFailure'}


# Section: Explicit failure outcomes for the caller
class AmbiguousWrite(Exception):
    """The request may have reached Kinesis; retrying can publish duplicates."""


class PublishIncomplete(Exception):
    """Stop visibly and carry IDs whose writes could not be confirmed."""
    def __init__(self, event_ids):
        self.event_ids = event_ids
        super().__init__(f'Unconfirmed event IDs: {event_ids}; inspect the journal before retrying')


# Section: Prepare bounded Kinesis requests
def batches(events):
    """Yield batches containing stable event IDs, payload bytes, and partition keys."""
    # yield returns one batch at a time and resumes this function on the next request.
    batch, size = [], 0
    for event in events:
        # Serialize once. Retries reuse these exact bytes and the same partition key.
        data = (json.dumps(event, separators=(',', ':')) + '\n').encode('utf-8')
        # A station key groups that station's writes under partition-key routing.
        # It does not deduplicate events or guarantee source event-time ordering.
        key = event['station_id']
        record_size = len(data) + len(key.encode('utf-8'))
        if record_size > MAX_EVENT_BYTES or not 1 <= len(key) <= 256:
            raise ValueError('Event or partition key exceeds the teaching bounds')
        if batch and (len(batch) >= MAX_BATCH_RECORDS or size + record_size > MAX_BATCH_BYTES):
            # Hand off the completed batch, then start a new empty one.
            yield batch
            batch, size = [], 0
        batch.append({'event_id': event['event_id'], 'request': {'Data': data, 'PartitionKey': key}})
        size += record_size
    # The final batch may be smaller than the size limit; it still must be sent.
    if batch:
        yield batch


# Section: Publish and retry only work that remains unconfirmed
def publish_batch(send, batch, emit, *, max_attempts=5, sleep=time.sleep, uniform=random.uniform):
    """Return confirmed entry count, or raise when recovery cannot finish safely."""
    # send makes a request; emit records what happened. Both are supplied functions.
    # sleep and uniform can also be replaced in tests so no waiting is needed.
    if max_attempts < 1:
        raise ValueError('max_attempts must be positive')
    # pending starts as the whole batch and shrinks when records are acknowledged.
    # accepted counts confirmed input entries, not unique business observations.
    pending = list(batch)
    accepted = 0
    for attempt in range(1, max_attempts + 1):
        emit({'action': 'attempt', 'attempt': attempt,
              'event_ids': [item['event_id'] for item in pending]})
        # Step: Attempt all currently pending entries, keeping their original bytes.
        try:
            response = send([item['request'] for item in pending])
        except AmbiguousWrite:
            # With no trustworthy response, none of these entries is confirmed.
            emit({'action': 'ambiguous_timeout', 'attempt': attempt,
                  'event_ids': [item['event_id'] for item in pending]})
        else:
            # Step: Inspect each result even if the HTTP request itself succeeded.
            results = response['Records']
            if len(results) != len(pending):
                raise ValueError('Response/request cardinality mismatch; stop rather than guess')
            retry = []
            terminal = []
            # Pair each submitted item with its result at the same index.
            # strict=True prevents unequal list lengths from being silently truncated.
            # HTTP 200 can contain both accepted entries and entries with ErrorCode.
            for item, result in zip(pending, results, strict=True):
                code = result.get('ErrorCode')
                if code:
                    emit({'action': 'record_failed', 'event_id': item['event_id'],
                          'attempt': attempt, 'error_code': code})
                    # Retry known temporary failures; keep other errors for a visible stop.
                    (retry if code in RETRYABLE_RECORD_ERRORS else terminal).append(item)
                else:
                    emit({'action': 'accepted', 'event_id': item['event_id'],
                          'sequence_number': result['SequenceNumber'],
                          'shard_id': result['ShardId'], 'attempt': attempt})
                    accepted += 1
            # An unexpected error needs investigation rather than endless retrying.
            if terminal:
                raise PublishIncomplete([item['event_id'] for item in terminal + retry])
            # Do not resend entries with confirmed success after a partial response.
            pending = retry
            if not pending:
                return accepted
        # Step: Wait before retrying, but only while another attempt is available.
        if attempt < max_attempts:
            # Full jitter: independently sample a delay from a capped exponential range.
            # The delay range grows exponentially and stops growing at four seconds.
            # Sampling within that range spreads retries from different producers.
            ceiling = min(4.0, 0.25 * 2 ** (attempt - 1))
            delay = uniform(0.0, ceiling)
            emit({'action': 'backoff', 'attempt': attempt, 'seconds': delay})
            sleep(delay)
    # Step: Preserve unconfirmed IDs when the attempt budget is exhausted.
    emit({'action': 'exhausted', 'event_ids': [item['event_id'] for item in pending]})
    raise PublishIncomplete([item['event_id'] for item in pending])


# Section: Wire the retry algorithm to real AWS calls and a local journal
def main():
    """Read CLI arguments, configure one SDK client, and publish a saved capture."""
    import boto3
    from botocore.config import Config
    from botocore.exceptions import (ClientError, ConnectTimeoutError,
                                     ConnectionClosedError, EndpointConnectionError, ReadTimeoutError)

    # Step: Take paths and resource identity from the caller, not hardcoded credentials.
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--events', type=Path, required=True)
    parser.add_argument('--stream-arn', required=True)
    parser.add_argument('--region', required=True)
    parser.add_argument('--profile')
    parser.add_argument('--journal', type=Path, required=True)
    args = parser.parse_args()
    # Validate all event sizes before any remote writes.
    prepared = list(batches(load_events(args.events)))
    # Step: Build one reusable client using the selected profile/default credential chain.
    # SDK retries handle request-level errors; publish_batch handles partial records.
    session = boto3.Session(profile_name=args.profile, region_name=args.region)
    client = session.client('kinesis', config=Config(
        connect_timeout=5, read_timeout=10,
        retries={'mode': 'standard', 'total_max_attempts': 3}
    ))
    # Step: Own client and journal lifetimes for the whole publication run.
    # 'x' creates a new journal and refuses to overwrite earlier evidence.
    # closing() calls client.close() when this block exits.
    with closing(client), args.journal.open('x', encoding='utf-8') as journal:
        def emit(entry):
            """Write one timestamped JSON Lines journal entry and show it in the terminal."""
            # **entry copies its fields into the new dictionary alongside logged_at.
            entry = {'logged_at': datetime.now(timezone.utc).isoformat(), **entry}
            line = json.dumps(entry)
            journal.write(line + '\n')
            # Flush Python's buffer so progress is visible during a run.
            # This is not an atomic commit with Kinesis or a crash-proof checkpoint.
            journal.flush()
            print(line)

        def send(records):
            """Send one request, preserving uncertainty if the transport loses its reply."""
            try:
                return client.put_records(StreamARN=args.stream_arn, Records=records)
            except (ReadTimeoutError, ConnectTimeoutError, EndpointConnectionError, ConnectionClosedError) as error:
                raise AmbiguousWrite() from error

        # Step: Record intended work before sending, then count confirmed entries.
        emit({'action': 'planned', 'event_ids': [item['event_id'] for batch in prepared for item in batch]})
        try:
            total = sum(publish_batch(send, batch, emit) for batch in prepared)
        except (ClientError, PublishIncomplete) as error:
            emit({'action': 'aborted', 'reason': str(error)})
            print(str(error), file=sys.stderr)
            # A nonzero exit code tells a shell or scheduler this run did not complete.
            return 1
        emit({'action': 'complete', 'confirmed_entries': total})
    return 0


# Section: Terminal entry point; imported tests do not publish to AWS
if __name__ == '__main__':
    sys.exit(main())
