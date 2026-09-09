# Task Isolation, Idempotency, Retries, Timeouts, and Sensors

> Status: Documentation complete; executable attempt-failure evidence planned  
> Level: Intermediate to Senior  
> Applies to: Generic orchestration / Airflow / Batch / External systems  
> Data scale: Local fault model; distributed production estimate  
> Example status: Planned  
> Evidence status: Documentation and contract review only  
> Last reviewed: 2026-09

## Overview

A task is safe only if an attempt can be isolated, bounded, cancelled, and
repeated without corrupting durable state. Retries provide another chance; they
do not supply idempotency. Timeouts bound waiting from the orchestrator's view;
they do not guarantee a remote query or API call stopped. Sensors coordinate
readiness but can consume control-plane or worker capacity if designed poorly.

## Learning objectives

- Define attempt identity, idempotency key, commit, and cancellation boundaries.
- Classify failures as retryable, terminal, ambiguous, or repair-required.
- Choose retry, timeout, deadline, and backoff policies from downstream behavior.
- Compare polling, rescheduling, deferred waiting, and data-aware triggers.
- Verify isolation, fencing, cleanup, and graceful shutdown under faults.

## Prerequisites

- DAG/run/task/attempt distinctions from guides 01 and 03.
- Area 08 retry, speculation, backpressure, and fencing concepts.
- Area 11 atomic publication and transaction concepts.

## Mental model and terminology

```text
admit -> acquire lease -> execute private work -> validate -> commit -> report
            |                   |                    |
            +---- timeout/cancel/failure may occur at every boundary --------+
```

| Term | Meaning in this guide |
| --- | --- |
| Isolation | Resource and state separation preventing one attempt from corrupting another |
| Idempotency key | Stable identity used to recognize repetition of one logical effect |
| Fence | Monotonic token or conditional rule preventing stale attempts from committing |
| Retry budget | Maximum attempts/time/cost allocated to transient recovery |
| Deadline | Latest useful completion time across queueing, attempts, and backoff |
| Sensor | Task-like coordination that waits for an externally verifiable condition |

Coroutine cancellation is a useful analogy: it is cooperative and cleanup still
matters. The analogy stops because a remote warehouse query or object-store write
may outlive the Python process and create a durable effect.

## Requirements, scale assumptions, and invariants

- Idempotency key includes operation, dataset, interval, semantic/code version, and scope.
- Attempts write private candidates and only a current fenced owner may publish.
- Retryable errors are enumerated; validation defects and permission failures fail fast.
- Exponential backoff includes jitter and respects a global deadline and attempt cap.
- Execution timeout plus cancellation grace stays within the publication SLO.
- Remote operation IDs are persisted so ambiguous outcomes can be queried.
- Waiting has a timeout, readiness predicate, polling budget, and failure owner.
- Temporary storage, subprocesses, connections, and credentials are bounded and cleaned.

## Data flow, ownership, and trust boundaries

| Boundary | Input contract | Owner | Failure behavior | Trust level |
| --- | --- | --- | --- | --- |
| Orchestrator to worker | Attempt, interval, deadline, artifact, scoped secret refs | Platform | Duplicate launch possible; application contains it | Trusted control input |
| Worker to engine | Idempotency/comment/query ID and bounded request | Task owner | Query may continue after client loss | Privileged remote call |
| Worker to staging | Attempt-private candidate | Dataset owner | Abandoned candidate is invisible | Untrusted until validated |
| Commit service/catalog | Candidate, fence, expected current version | Dataset owner | Atomic accept/reject/unknown | Authoritative publication |
| Sensor to producer | Read-only readiness request | Producer owns truth | Not-ready, unavailable, or invalid response differ | External trust boundary |

## Idempotent publication pattern

```python
def publish_interval(request: BuildRequest) -> DatasetRef:
    existing = ledger.find_by_idempotency_key(request.key)
    if existing and existing.matches(request.inputs):
        return existing.dataset_ref

    fence = ledger.acquire(request.key, request.attempt_id)
    candidate = engine.build_private(request, fence)
    validate(candidate)
    return ledger.compare_and_publish(candidate, fence)
```

The sketch omits real transaction boundaries. `find` followed by `acquire` must
not be an unfenced check-then-act race. A returned success is accepted only after
reading the committed ledger entry.

### SQL upsert/ledger sketch

```sql
INSERT INTO publication_ledger
    (idempotency_key, publication_id, input_version, status)
VALUES (:key, :publication_id, :input_version, 'committed')
ON CONFLICT (idempotency_key) DO NOTHING;
```

Dialect and isolation matter. After an unknown commit result, read by key and
compare all semantic fields; do not blindly issue a different publication ID.

## Retry and timeout decision table

| Condition | Default action | Reason |
| --- | --- | --- |
| Connection refused before request accepted | Retry with jitter within deadline | Likely no effect, transient dependency |
| HTTP/DB timeout after submission | Query operation/idempotency state first | Outcome is ambiguous |
| Invalid schema or violated invariant | Fail terminal and quarantine/alert | Retry repeats deterministic defect |
| Permission denied | Fail terminal; correct access | Repetition adds load and noise |
| Rate limited with retry hint | Respect hint and global budget | Protect dependency |
| Worker killed after commit | Adopt result by stable key | Prevent duplicate side effect |
| Cleanup failure after successful commit | Report separately; do not republish | Primary effect already authoritative |

Timeout layers include sensor wait, task execution, remote client request, remote
statement, and workflow deadline. The shortest layer should not cause untracked
work at a longer layer. Propagate cancellation where supported and reconcile when
support is uncertain.

## Sensors and waiting

Prefer a durable producer event/asset update when available. Otherwise poll a
cheap, explicit readiness endpoint with jitter and a maximum interval. A worker-
occupying polling loop is acceptable only for very short waits with reserved
capacity. Rescheduling or deferral can release worker slots, but the trigger or
polling control plane still needs bounds and high availability.

Never treat “object exists” as complete if multipart upload, manifest creation,
or producer transaction has a stronger readiness contract.

## Failure model and recovery

| Failure | Containment | Recovery evidence |
| --- | --- | --- |
| Duplicate attempts overlap | Private staging plus fence | Exactly one commit; loser cannot publish later |
| Timeout leaves query running | Remote query ID and cancel request | Query terminal; no untracked publish |
| Response lost after commit | Lookup stable key | Existing result matches requested inputs |
| Retry storm overloads dependency | Jitter, cap, circuit/admission limit | Queue and dependency latency recover |
| Sensor condition never arrives | Deadline and producer alert | Explicit failed/missed interval, no infinite wait |
| Worker disk/memory exhaustion | Per-attempt limits and bounded staging | Failed attempt cleaned; other tasks isolated |
| Cancellation during shutdown | Drain, grace, fence expiry | Late attempt rejected; rerun converges |
| Poison input repeats | Deterministic classification/quarantine | Valid records progress under declared policy |

## Security, privacy, and governance

Resolve secret references at runtime and avoid serializing values into task
arguments or metadata. Use per-task service identities and destination allowlists.
Sanitize command arguments and SQL identifiers; parameterization does not make
dynamic table names safe. Quarantine paths and failure logs must apply the same
classification and retention as source data.

## Data quality, testing, and evidence

| Evidence | Dataset and environment | Procedure | Expected result | Result |
| --- | --- | --- | --- | --- |
| Idempotency property | Six-event fixture / local model | Repeat and permute attempts | One equivalent publication | Pending |
| Crash matrix | Fake engine/ledger | Crash before/during/after commit | No partial visible state; convergence | Pending |
| Timeout | Controllable remote double | Delay response past each timeout | Work cancelled or reconciled | Pending |
| Sensor | Mutable readiness fixture | Missing, late, malformed, unavailable | Bounded state and correct owner alert | Pending |
| Isolation/load | Test deployment | Exhaust one task's CPU/memory/disk and retry | Other classes retain capacity | Pending |

## Debugging guide

1. Capture logical key, attempt ID, fence, remote query/request ID, candidate, and publication ID.
2. Determine whether failure is before acceptance, after acceptance, or unknown.
3. Query the authoritative remote system and ledger before retry or clear.
4. Inspect queue, retry count, backoff, deadline, cancellation, and resource-limit signals.
5. Fence stale attempts, retain the prior certified version, and stop retry amplification.
6. Repair/retry with the same semantic key; reconcile candidates and cleanup afterward.

## Common pitfalls

### Pitfall: retry every exception

Deterministic validation and authorization errors become storms. Classify errors
and budget retry amplification.

### Pitfall: timeout means stopped

It may mean only the client stopped waiting. Persist remote operation identity and
cancel or reconcile explicitly.

### Pitfall: sensor success means complete

Test the producer's commit marker or frontier, not a weak proxy such as filename
existence or row count greater than zero.

## Performance, capacity, and cost

Budget attempts per logical task, total retry time, open connections, worker
slots, deferred triggers, polling requests, staging bytes, and remote queries.
With three attempts, one logical 3 GiB scan can become 9 GiB before speculative
or overlapping work. Reserve capacity for cancellation and repair.

## Observability and operations

Metrics include queue delay, attempt count, retry reason, backoff, deadline
remaining, timeout layer, cancellation latency, sensor age, fence rejection,
candidate bytes, and ambiguous outcomes. Keep labels bounded: dataset/task/error
class are useful; raw event, query, or publication IDs belong in logs/traces.

## Compatibility, migration, backfill, and delivery

Changing an idempotency-key formula or task ID can make old effects invisible.
Deploy readers that understand both key versions, migrate ledger mappings, canary
crash cases, then contract after replay/rollback retention. Changes to provider
timeouts or cancellation semantics require real integration tests.

## Working example

- Python source: Planned attempt/ledger state model under `src/big_data_example/orchestration/`
- Tests: Planned property and crash-matrix tests under `tests/orchestration/`
- Infrastructure: Planned Airflow plus controllable remote service integration
- Try it: Planned fault scenario command accepting a crash point
- Expected result: One visible publication or explicit terminal failure
- Evidence: Planned state trace, reconciliation, resource, and retry metrics
- Scale represented: Local model and production estimates only
- Remaining risk: Real transactions, cancellation, isolation, and executor faults unverified

## Knowledge check

1. Distinguish retryability from idempotency.
2. Predict state when a warehouse commits after the client's timeout.
3. Diagnose repeated permission failures configured with five retries.
4. Design a fence test with two concurrent attempts.
5. Estimate scan amplification for three retries over 3 GiB.
6. Migrate an idempotency-key formula without duplicating old effects.
7. Implement one crash point in the planned state model and assert convergence.

## Key takeaways

- Retries repeat work; idempotency makes repetition safe.
- Timeouts bound waiting, not necessarily remote effects.
- Private candidates and fencing prevent stale attempts from publishing.
- Waiting needs the same capacity, timeout, ownership, and evidence discipline as processing.
- Ambiguous outcomes are reconciled before another side effect.

## Resources

- [Apache Airflow: tasks](https://airflow.apache.org/docs/apache-airflow/stable/core-concepts/tasks.html) (reviewed 2026-09)
- [Apache Airflow: sensors](https://airflow.apache.org/docs/apache-airflow/stable/core-concepts/sensors.html) (reviewed 2026-09)
- [Apache Airflow: deferrable operators and triggers](https://airflow.apache.org/docs/apache-airflow/stable/authoring-and-scheduling/deferring.html) (reviewed 2026-09)

## Related topics

- [Airflow architecture and lifecycle](03-airflow-architecture-dags-and-task-lifecycle.md)
- [Backfills and concurrency controls](05-backfills-dynamic-workflows-and-concurrency-controls.md)
- [Area 08 retries and fault recovery](../08-distributed-systems-foundations/07-retries-idempotency-speculation-and-fault-recovery.md)

## Completion checklist

- [x] Attempt, isolation, idempotency, retry, timeout, deadline, and sensor contracts defined
- [x] SQL/Python models expose commit ambiguity and fencing needs
- [x] Failure, cancellation, security, resource, and recovery behavior addressed
- [x] Capacity, observability, migration, and diagnosis covered
- [x] Working example and all executable evidence accurately marked Planned
- [ ] Fault model, real integration, isolation, cancellation, and load evidence executed

