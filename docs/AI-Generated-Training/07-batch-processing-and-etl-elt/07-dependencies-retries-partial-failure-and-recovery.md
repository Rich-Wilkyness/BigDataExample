# Dependencies, Retries, Partial Failure, and Recovery

> Status: Documentation complete; executable evidence planned  
> Level: Intermediate to Senior  
> Applies to: Generic data engineering / Batch / Schedulers / Storage  
> Data scale: Local fixture; distributed and production estimates  
> Example status: Planned  
> Evidence status: None  
> Last reviewed: 2026-09

## Overview

A batch pipeline is a dependency graph whose nodes consume and publish versioned
data contracts. A retry is safe only when the node can determine or reproduce its
prior effect. Partial failure is normal: workers, dependencies, storage, metadata,
or notification can fail independently, and a timeout can leave the outcome
unknown.

This guide defines job boundaries, retry ownership, poison-data containment,
cancellation, compensation, and restart. It remains scheduler-neutral; workflow
product syntax does not substitute for these guarantees.

## Learning objectives

- Model data availability and certification dependencies separately from task order.
- Choose job boundaries that are independently retryable and observable.
- Classify failures as transient, deterministic input, capacity, contract, or unknown outcome.
- Design bounded retry, cancellation, compensation, and restart behavior.
- Prove recovery and end-to-end convergence after partial failure.

## Prerequisites

- [Checkpoints, idempotency, and atomic publication](05-checkpoints-idempotency-and-atomic-publication.md)
- [Backfills, reprocessing, and historical correction](06-backfills-reprocessing-and-historical-correction.md)

## Mental model and terminology

The dependency graph resembles a Gradle task graph only at a high level: declared
inputs produce outputs and independent nodes may run concurrently. The analogy
stops because data jobs interact with remote mutable systems, may have unknown
commit outcomes, and publish durable datasets used outside the graph.

| Term | Meaning in this guide |
| --- | --- |
| Data dependency | Exact certified dataset/version or closed input condition a node requires |
| Control dependency | Ordering constraint that may not prove data readiness |
| Retry owner | Boundary capable of determining prior outcome and safely repeating/repairing it |
| Transient failure | Condition likely to change without input/code change, such as brief unavailability |
| Deterministic failure | Same pinned input and code predictably fail, such as an invalid required record |
| Compensation | Explicit semantic action addressing a committed effect that cannot be rolled back atomically |
| Recovery point | Durable state from which execution can resume without losing or double-applying work |

## Requirements, assumptions, and invariants

The reference DAG selects accepted raw data, canonicalizes events, enriches facts,
aggregates daily metrics, runs quality gates, publishes, and notifies consumers.
The 02:00 UTC deadline has a 30-minute recovery reserve. A node may retry three
times only as an initial policy; measured failure modes and dependency quotas must
replace that estimate.

Invariants:

- A node reads named immutable/versioned inputs rather than “whatever is latest” mid-run.
- Success means durable output contract evidence, not process exit zero alone.
- Only the owner of an idempotent effect retries it; nested retry multiplication is bounded.
- Deterministic poison input is quarantined or fails explicitly, never retried forever.
- Cancellation stops new work and leaves candidates invisible or recoverable.
- Downstream admission requires upstream certification, not merely task completion.
- Recovery completes only when dataset versions, checkpoints, reconciliation, and consumers agree.

## Dependency graph and boundaries

```text
accepted-events V17 ----> canonicalize ----> canonical V22 ----+
product-history V8 --------------------------------------------+--> enrich facts
                                                                  |
                                                     fact candidate V31
                                                                  |
                                       aggregate metrics + quality/reconcile
                                                                  |
                                                  atomic publish generation G9
                                                                  |
                                                     consumer notification
```

The graph records exact versions on edges. Canonicalization and enrichment may be
separate when the canonical output is reusable, expensive, or a recovery boundary;
otherwise an extra persisted stage adds storage and cleanup without value.
Notification occurs after publication and uses the publication identity so it can
be retried or deduplicated independently.

## Failure classification and retry policy

| Failure class | Example | Default response | Retry evidence |
| --- | --- | --- | --- |
| Transient dependency | Throttle, brief network/storage outage | Bounded exponential backoff with jitter and deadline | Dependency health plus idempotent request |
| Unknown outcome | Timeout during metadata commit | Read authoritative state before mutation | Stable operation/run ID found or absent |
| Deterministic input | Required schema/value violation | Quarantine if contract permits; otherwise fail scope | Stable rejection fingerprint/disposition |
| Code/contract defect | Join fan-out, invariant failure | Stop retries; fix/version/reprocess | New artifact/config and regression test |
| Capacity/overload | OOM, disk full, queue saturation | Reduce admission/partition size or add approved capacity | Headroom and bounded workload |
| Authorization/configuration | Revoked grant, missing secret/config | Fail fast and repair control plane | Preflight succeeds; audit trail |

Exponential backoff reduces synchronized pressure but must obey a total deadline,
maximum attempts, dependency quota, and cancellation. If client, task, and workflow
each retry three times, one logical operation can execute 27 times. Assign one
retry owner or coordinate budgets.

## Run and node state

```text
PENDING -> ADMITTED -> RUNNING -> OUTPUT_READY -> CERTIFIED -> SUCCEEDED
               |          |            |             |
            CANCELLED   RETRYABLE     FAILED        REJECTED
                           |
                       UNKNOWN -> inspect durable state -> resume/succeed/fail
```

Persist transitions with run/node/attempt identity, expected prior state, input
versions, output candidate, heartbeat/lease generation, timestamps, and reason.
A lease expiry permits another attempt only after fencing prevents the old worker
from committing. Heartbeats detect absence, not whether a remote write committed.

## Partial failure and recovery patterns

| Boundary | Safe recovery pattern | Limitation |
| --- | --- | --- |
| Pure deterministic transform | Recompute from pinned inputs | Dependency/environment versions must truly be pinned |
| Expensive persisted stage | Validate and reuse immutable candidate | Storage and compatibility lifecycle |
| Database transaction | Roll back or inspect transaction/run ledger | Does not cover other systems |
| Manifest publication | Inspect authoritative head; conditional retry | Orphans need safe cleanup |
| External notification/export | Idempotency key/outbox, or compensation | Recipient must expose state or accept repair |
| Multi-dataset graph | Publish one generation/manifest after all gates | Larger coordination and rollback scope |

Compensation is domain logic, not a technical undo. If a consumer received an
incorrect daily metric, publishing a correction and audit notice may be safer
than deleting history. Record who approves compensation and how reconciliation
proves the final business state.

## Poison data and degraded dependencies

Classify defects at the smallest contractually safe grain. An optional malformed
record can enter protected quarantine while the scope reconciles; a corrupt file
header, unknown schema, missing required dimension version, or systemic validator
defect may invalidate the whole run. Quarantine is not success unless consumer
completeness and reject thresholds permit it.

Do not substitute stale or empty dependency data silently. If degraded operation
is allowed, name maximum staleness, visible quality flag, affected consumers,
approval, and correction workflow.

## Failure model and recovery

| Failure | Detection | Containment and recovery | Consumer behavior |
| --- | --- | --- | --- |
| Worker disappears | Lease/heartbeat expires | Fence old attempt; inspect candidate; resume/retry | Prior certified version remains |
| Storage write times out | Unknown write state | Verify object/checksum/manifest before retry | No candidate visibility |
| Upstream version withdrawn | Certification dependency invalid | Stop descendants; select valid version and rebuild | Continue prior version or declared unavailable |
| Quality service unavailable | Gate has no result | Retry within deadline; do not treat missing evidence as pass | Prior version remains |
| One partition repeatedly OOMs | Task metrics/skew show repeat | Isolate key/range, repartition or repair data, rerun | No mixed publish |
| Notification fails after publish | Head is new; delivery absent | Retry notification with version idempotency key | Data is available; notice delayed |
| Scheduler database restarts | Run state recovered from durable ledger | Reconcile leases/tasks to outputs, then resume | Dataset head determines truth |

## Security, privacy, and governance

Use separate least-privilege identities for read, stage, publish, and repair.
Treat scheduler parameters, logs, exception strings, retry queues, dead-letter
records, and lineage as data surfaces. Authenticate callbacks, prevent command/SQL
and path injection, rotate secrets without embedding them in retries, fence stale
workers, audit manual state changes, and require approval for bypassing quality or
retention controls.

## Data quality, testing, and evidence

| Evidence | Procedure | Expected result | Result |
| --- | --- | --- | --- |
| DAG contract test | Validate exact inputs, outputs, owners, and version edges | No hidden latest/control-only dependency | Pending |
| Failure classification unit tests | Inject each failure class | Correct retry/fail/quarantine/inspect action | Pending |
| Retry-budget test | Stack client/node/workflow failure | Attempts stay within global budget | Pending |
| Fault matrix | Kill worker/coordinator/dependency around every commit | No partial visibility; recovery converges | Pending |
| Poison/skew test | Stable bad record/file and hot partition | Bounded attempts and explicit disposition | Pending |
| Cancellation/drain test | Cancel at each node state | No new admission; resources close; safe resume | Pending |
| End-to-end reconciliation | Recover graph and compare source to all published outputs | Versions/checkpoints/counts/keys/totals agree | Pending |

Mocks can verify classification but not process death, network ambiguity, database
restart, storage durability, scheduler fencing, or distributed resource exhaustion.

## Common pitfalls

### Pitfall: retrying every exception

Deterministic defects waste the recovery window and amplify load. Classify errors,
inspect unknown outcomes, and require changed conditions before repeating poison work.

### Pitfall: depending on task success instead of a dataset version

A task may exit zero before durable publish, or its output may later be invalidated.
Downstream nodes require certified version evidence.

### Pitfall: overlapping retries without fencing

A slow original attempt can commit after its replacement. Use lease generations
or conditional publication so stale workers cannot win.

### Pitfall: manual “mark success” to unblock the graph

It fabricates evidence and can propagate missing data. Record a governed waiver or
publish an explicit degraded dataset version with correction ownership.

## Performance, capacity, cost, and operations

Budget critical path, queue and retry delay, recovery reserve, maximum attempt
amplification, concurrent readers/writers, dependency quotas, heartbeat/control
traffic, candidate duplication, and repair cost. Retry storms are overload, not
free reliability.

Observe run/node/attempt state age, input/output versions, queue/runtime percentiles,
retries by class, deadline budget, last progress, lease generation, candidate size,
dependency latency/throttle, quality state, and publish/notification outcome.
Alerts route to the boundary owner with a runbook that inspects durable truth before
mutating or retrying.

## Compatibility, migration, and tradeoffs

Changing DAG boundaries, retry policy, or state schema can strand in-flight runs.
Deploy readers that understand old/new states, drain or migrate registered runs,
dual-run a pinned scope, compare outputs and recovery behavior, then switch
schedulers. Keep data contracts independent from product-specific task identifiers.

## Working example

- Python/SQL/data/tests: planned DAG contract, durable run/node ledger, failure classifier, retry budget, fencing publisher, poison fixture, and fault harness
- Expected result: injected partial failures converge without mixed versions, runaway retries, or unexplained loss
- Scale represented: none yet; local process faults then real scheduler/storage integration planned
- Remaining risk: network partitions, stale workers, shared-platform overload, and external compensation

## Knowledge check

1. Distinguish a data dependency from a control dependency in the reference DAG.
2. Predict request count when three retry layers each allow three attempts.
3. Diagnose a stale worker publishing after a lease expires.
4. Classify and handle a corrupt record, disk full, and commit timeout.
5. Design cancellation behavior while two candidate files are open.
6. Define evidence that an end-to-end recovery is complete.

## Key takeaways

- Durable versioned data contracts, not scheduler arrows, define readiness.
- Retry belongs to the boundary that can establish prior outcome and idempotency.
- Unknown outcomes require inspection; deterministic failures require changed conditions.
- Fencing, isolated candidates, and atomic publication contain partial failure.
- Recovery ends with convergence and reconciliation, not a green rerun alone.

## Resources

- [Python documentation: exceptions](https://docs.python.org/3/tutorial/errors.html) (reviewed 2026-09)
- [PostgreSQL documentation: transaction isolation](https://www.postgresql.org/docs/current/transaction-iso.html) (reviewed 2026-09)
- [RFC 9110: idempotent methods](https://www.rfc-editor.org/rfc/rfc9110.html#section-9.2.2) (reviewed 2026-09)

## Related topics

- [Lineage, testing, operating, and evolving batch pipelines](08-lineage-testing-operating-and-evolving-batch-pipelines.md)
- [Event ingestion, batching, and backpressure](../06-data-ingestion-and-source-integration/06-event-ingestion-batching-and-backpressure.md)
- [Checkpoints, idempotency, and atomic publication](05-checkpoints-idempotency-and-atomic-publication.md)

## Completion checklist

- [x] Dependencies, job boundaries, failure classes, retries, fencing, cancellation, and recovery explained
- [x] Security, quality, poison data, capacity, operations, migration, compensation, and evidence addressed
- [ ] DAG, classifier, budget, fault, poison, cancellation, scheduler, and reconciliation evidence run

