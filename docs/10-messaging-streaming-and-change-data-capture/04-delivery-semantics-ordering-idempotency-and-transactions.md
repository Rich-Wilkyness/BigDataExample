# Delivery Semantics, Ordering, Idempotency, and Transactions

> Status: Documentation complete; executable evidence planned  
> Level: Intermediate to Senior  
> Applies to: Messaging / Streaming / Transactions / Distributed systems  
> Data scale: Local deterministic model; distributed and production estimates  
> Example status: Planned  
> Evidence status: None  
> Last reviewed: 2026-09

## Overview

Delivery semantics describe what may happen to record deliveries around failure;
they do not automatically describe business outcomes. At-most-once permits loss
but avoids redelivery at a boundary. At-least-once avoids unexplained loss by
retrying but permits duplicates. “Exactly once” is meaningful only for named
inputs, state, outputs, transaction boundaries, versions, and failure assumptions.

Most robust pipelines accept at-least-once delivery and make the business effect
idempotent. Transactions can atomically couple selected operations supported by
one system or protocol, but arbitrary external side effects remain outside that
boundary and require an identity ledger, reconciliation, or compensation.

## Learning objectives

- Translate delivery labels into concrete crash timelines and observable outcomes.
- Separate transport occurrence, logical event identity, business key, and effect identity.
- Preserve required ordering while handling retry, concurrency, and repartitioning.
- Design idempotent state transitions and transactional consume-process-produce flows.
- Prove convergence through replay and reconciliation rather than labels.

## Prerequisites

- [Producers, consumers, acknowledgements, and backpressure](03-producers-consumers-acknowledgements-and-backpressure.md)
- [Retries, idempotency, speculation, and fault recovery](../08-distributed-systems-foundations/07-retries-idempotency-speculation-and-fault-recovery.md)
- [DDL, constraints, transactions, and concurrent change](../03-sql-and-analytical-querying/07-ddl-constraints-transactions-and-concurrent-change.md)

## Mental model and terminology

```text
read input I -> compute -> write effect E -> record progress P

crash before E: retry needed
crash after E, before P: E may repeat
record P before E: crash may skip E
atomic(E, P): possible only when both share a supported transaction boundary
```

Room transactions are a useful analogy: several database writes can commit or
roll back together. The analogy stops when Kafka, an HTTP API, object storage,
and a warehouse are independent coordinators; there is no implicit transaction
spanning them.

| Term | Meaning in this guide |
| --- | --- |
| Delivery identity | Topic/partition/offset or equivalent occurrence |
| Logical event identity | Producer-stable ID reused across retries |
| Business key | Entity/window identity whose state changes |
| Effect identity | Stable ID for one externally visible operation |
| Idempotent | Repeating the same intended operation converges to one effect |
| Transaction | Atomic isolation/durability boundary supplied by named systems |
| Fence | Epoch/token that rejects work from a stale producer or owner |

## Requirements and invariants

The reference pipeline requires no acknowledged unexplained loss, tolerates
redelivery, preserves per-subject session order, and publishes one metric value
per `(definition_version, tenant_id, product_id, window_start)`. External
notifications are explicitly outside the streaming transaction.

- Producer retries reuse logical event identity; a changed payload under the same ID is a conflict.
- Per-key state changes apply in a total declared version/order, not arrival-time guesswork.
- Deduplication retention covers the maximum retry/replay horizon or documents the gap.
- Progress cannot become durable ahead of an effect that replay cannot reconstruct.
- Idempotency scope includes operation, target, semantic version, and intended payload.
- Stale transaction/assignment epochs cannot commit after ownership transfer.
- Every claim names excluded systems and behavior under timeout, fencing, and retention loss.

## Delivery semantics by crash order

| Pattern | Sequence | Failure outcome | Suitable when |
| --- | --- | --- | --- |
| At-most-once | Mark progress, then effect | Crash between can lose effect | Loss explicitly acceptable |
| At-least-once | Effect, then progress | Crash between can repeat effect | Effect is idempotent/deduplicated |
| Atomic input/output | Effect and progress in one supported transaction | Commit is all-or-none; response may still be unknown | Inputs/outputs share transaction domain |
| Reconcile/repair | Record intent/result ledger around external effect | Ambiguity remains until queried/repaired | External API cannot join transaction |

Kafka's idempotent producer and transactions have precise broker/client scope and
configuration requirements. They do not make an email, REST call, database, or
arbitrary consumer logic exactly once. Test the selected versions and read
isolation behavior before making a stronger claim.

## Idempotent sink patterns

For a SQL sink, use a unique effect identity and one database transaction:

```sql
-- PostgreSQL-style sketch. Claim an immutable semantic effect and apply it once.
BEGIN;

WITH claimed AS (
  INSERT INTO applied_effect (effect_id, payload_hash)
  VALUES (:effect_id, :payload_hash)
  ON CONFLICT (effect_id) DO NOTHING
  RETURNING effect_id
)
INSERT INTO product_window_metric (
  definition_version, tenant_id, product_id, window_start, views, input_frontier
)
SELECT :definition_version, :tenant_id, :product_id,
       :window_start, :views, :input_frontier
FROM claimed
ON CONFLICT (definition_version, tenant_id, product_id, window_start) DO UPDATE
SET views = EXCLUDED.views,
    input_frontier = EXCLUDED.input_frontier;

COMMIT;
```

On a duplicate claim, compare the stored and supplied payload hashes; a mismatch
is a hard conflict, while a match returns the prior outcome. The `effect_id` should
be derived from stable semantic identity, not a random ID generated on each attempt.
A legitimate later correction uses an explicit correction/version identity; do
not let deduplication suppress evolution.

For additive counters, `SET total = total + :delta` is not idempotent. Store each
delta once under a unique effect ID and derive/sum, or atomically claim the effect
and update the aggregate in one database transaction.

## Ordering and concurrency

Broker partition order does not guarantee completion order when consumer work is
concurrent. Preserve per-key order by serial processing, keyed lanes, versioned
conditional updates, or buffering with a bounded gap policy. Global order is
usually expensive and unnecessary; define the narrowest business requirement.

Event-time order may differ from transport order. Sequence numbers detect gaps
only when the producer defines a sequence scope and lifecycle. Timestamps alone
are not unique, monotonic, or immune to skew.

## Data flow and commit boundaries

| Boundary | Atomic together | Not atomic with it | Recovery mechanism |
| --- | --- | --- | --- |
| Kafka producer transaction | Declared Kafka records and offsets supported by transaction | External DB/API/object store | Abort/fence/retry within protocol |
| Database transaction | Rows/ledger in one database | Kafka offsets unless connector pattern bridges it | Rollback/unique constraint/reconcile |
| Stream checkpoint | Engine state and declared source progress under engine contract | Arbitrary side effects | Restore/replay |
| External API | API's idempotency contract only | Local offset/checkpoint | Effect ID, status lookup, ledger, compensation |

## Failure model and recovery

| Failure | Symptom | Containment and convergence proof |
| --- | --- | --- |
| Duplicate delivery | Same logical ID at multiple offsets | Same final state/effect count after replay |
| Conflicting duplicate ID | Same ID, different canonical payload hash | Quarantine/stop; never choose silently |
| Crash after effect/before progress | Effect exists, input repeats | Idempotent claim returns prior outcome |
| Commit timeout | Caller cannot distinguish success/failure | Query transaction/effect ID, retry safely, reconcile |
| Stale owner commits | Old assignment epoch writes late | Sink/broker fence rejects it |
| Dedup state expired | Old event can apply again | Bound replay or rebuild from authoritative state |
| Repartition changes order | Same key spans old/new partitions | Versioned migration, merge by source sequence, reconcile |

## Security, privacy, and governance

Effect and idempotency ledgers are sensitive operational data and need retention,
access, encryption, and deletion policy. Do not place PII directly into globally
visible keys or transaction IDs. Transactions do not authorize data: producers,
consumers, sinks, and administration each need least privilege. Protect replay and
reset operations because they can repeat regulated side effects at large scale.

## Data quality, testing, and evidence

Create a deterministic crash matrix at every point before/during/after input read,
effect claim, effect commit, progress commit, and acknowledgement response.

| Evidence | Procedure | Expected result | Result |
| --- | --- | --- | --- |
| Duplicate/property | Repeat every event 0–5 times and vary grouping | Same logical result | Pending |
| Conflict | Reuse ID with mutated payload | Explicit conflict disposition | Pending |
| Crash matrix | Kill at every commit boundary | No unexplained loss; duplicates within contract | Pending |
| Ordering | Delay concurrent operations for same/different keys | Required per-key state converges | Pending |
| Transaction isolation | Abort, timeout, fence, and read with supported isolation | No aborted/partial output exposed | Pending |
| External effect | Lose response and restart | One effect or explicit repair case | Pending |

Mocks can test the state machine but cannot prove real broker transactions,
database isolation, fencing, failover, or API idempotency. Run real integrations.

## Debugging guide

Trace logical event ID, delivery position, business key/version, effect ID,
transaction ID/epoch, assignment generation, checkpoint, and sink result. For a
duplicate symptom, first determine whether duplicate deliveries produced one or
multiple effects. For a gap, compare source positions, progress, effect ledger,
and business reconciliation. Root cause is complete only when the exact failure
window is reproduced and replay converges.

## Common pitfalls

### Pitfall: “exactly once” without a boundary

The phrase is unverifiable unless inputs, outputs, state, isolation, time,
retention, and failures are named. Replace it with a scoped claim and crash test.

### Pitfall: random idempotency keys on retry

Each retry becomes a new effect. Derive or persist the key from the original
business intent before the first attempt.

### Pitfall: deduplicating forever

Unbounded identity state is another availability failure. Set retention from
retry/replay requirements and define rebuild or old-event behavior.

## Performance, capacity, and operations

Measure transaction rate/latency/abort/fence, outstanding transactions, duplicate
and conflict rates, idempotency-ledger lookup/write latency, state cardinality and
retention bytes, retry amplification, sink contention, and reconciliation drift.
Transactions and ordered lanes reduce concurrency; benchmark with hot keys,
timeouts, broker failover, and sink throttling.

## Compatibility, migration, backfill, and delivery

Semantic version belongs in state/effect identity when new logic may produce a
different correct result. Shadow new logic from the same frontier into isolated
state, compare, cut over atomically, and retain rollback input. Backfills must not
share transaction IDs, groups, or sink keys accidentally with live processing;
coordinate corrections deliberately.

| Choice | Prefer when | Cost/risk |
| --- | --- | --- |
| Idempotent upsert/ledger | At-least-once input and stable effect identity | State retention and sink contention |
| Broker transaction | Consume/process/produce remains in supported broker domain | Operational/configuration complexity |
| Database transaction | Effects and progress can live in one database | Coupling and write load |
| Compensation/reconciliation | External side effect cannot be atomic | Temporary inconsistency and runbook burden |

## Working example

- Python/SQL: planned delivery state machine, effect ledger, and idempotent metric upsert
- Tests: planned property, crash, conflict, ordering, transaction, and external-effect cases
- Infrastructure: planned Kafka and PostgreSQL integrations with fault injection
- Try it: no command yet
- Evidence: documentation review only
- Remaining risk: real transaction fencing/isolation, retention, failover, and external API behavior

## Knowledge check

1. Describe the crash gap in effect-then-offset and offset-then-effect sequences.
2. Design an effect ID for one versioned product-window metric.
3. Explain why an idempotent Kafka producer does not make an HTTP call exactly once.
4. Diagnose a duplicate counter despite one final committed consumer offset.
5. Decide how long to retain deduplication state and what happens after expiry.
6. Design a mixed-version shadow, cutover, replay, and rollback.

## Key takeaways

- Delivery occurrence, logical event, business entity, and side effect need distinct identities.
- At-least-once plus idempotent effects is often the composable baseline.
- Transactions are powerful only inside their named atomic boundary.
- Ordering is partition/key scoped and can be lost again through concurrency.
- Crash matrices and reconciliation prove outcomes; labels do not.

## Resources

- [Apache Kafka 4.3 design and delivery semantics](https://kafka.apache.org/43/design/) (reviewed 2026-09)
- [Apache Kafka 4.3 producer configuration](https://kafka.apache.org/43/configuration/producer-configs/) (reviewed 2026-09)
- [PostgreSQL transaction isolation](https://www.postgresql.org/docs/current/transaction-iso.html) (reviewed 2026-09)

## Related topics

- [Idempotency, deduplication, late data, and reconciliation](../06-data-ingestion-and-source-integration/08-idempotency-deduplication-late-data-and-reconciliation.md)
- [Stateful stream processing, checkpoints, and replay](06-stateful-stream-processing-checkpoints-and-replay.md)

## Completion checklist

- [x] Delivery labels, identities, ordering, idempotency, transactions, side effects, and fencing explained
- [x] Failure, security, testing, capacity, compatibility, backfill, and recovery addressed
- [ ] State-model, Kafka/database transaction, fault, ordering, and external-effect evidence run
