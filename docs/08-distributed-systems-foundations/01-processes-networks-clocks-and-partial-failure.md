# Processes, Networks, Clocks, and Partial Failure

> Status: Documentation complete; executable evidence planned  
> Level: Beginner to Intermediate  
> Applies to: Generic data engineering / Distributed systems / Batch / Streaming  
> Data scale: Local model; distributed and production estimates  
> Example status: Planned  
> Evidence status: None  
> Last reviewed: 2026-09

## Overview

A distributed data job is a set of independent processes communicating through
networks and durable stores. A caller that receives a response knows more than a
caller that times out: silence cannot distinguish a slow worker, a lost request,
a committed operation with a lost response, or a failed process. This partial
failure is the first durable constraint of distributed design.

This guide covers remote boundaries, deadlines, cancellation, clocks, failure
detection, and unknown outcomes. It does not prescribe a networking library,
cluster manager, or exactly-once product feature.

## Learning objectives

- Distinguish local exceptions from uncertain remote outcomes.
- Define deadlines, attempt identities, leases, heartbeats, and fencing.
- Separate elapsed-time measurement from wall-clock and event-time ordering.
- Trace cancellation and resource cleanup across process boundaries.
- Design evidence that recovery converges after delay, loss, and process death.

## Prerequisites

- [07 Dependencies, retries, partial failure, and recovery](../07-batch-processing-and-etl-elt/07-dependencies-retries-partial-failure-and-recovery.md)
- Basic process, thread, coroutine, HTTP, and transaction concepts

## Mental model and terminology

A coroutine timeout is a useful reminder that waiting should be bounded. It does
not prove that the remote operation stopped: cancellation is a protocol message,
not a rollback of already durable effects.

```text
caller        network             worker             durable metadata
  | request A ----?---------------->|                       |
  |                 worker commits |---- commit A --------->|
  |<---- response lost -------------|                       |
  | deadline expires                |                       |
  | inspect A --------------------------------------------->|
  |<------------------------------- committed --------------|
```

| Term | Meaning in this guide |
| --- | --- |
| Partial failure | Some components fail or become unreachable while others continue |
| Unknown outcome | The observer lacks evidence whether an operation committed |
| Deadline | Latest useful completion time propagated through dependent work |
| Heartbeat | Evidence of recent liveness, not proof of progress or commit outcome |
| Lease | Time-bounded permission to act, normally paired with a generation |
| Fencing token | Monotonically ordered generation that lets storage reject stale actors |
| Monotonic clock | Clock suitable for durations within one process, not cross-host event ordering |

## Requirements, assumptions, and invariants

The reference aggregation gives each stage-partition attempt a stable operation ID,
a deadline, and a lease generation. Network delivery may be delayed, duplicated,
reordered, or lost. Hosts may pause or restart, and their wall clocks may differ.

- A timeout never becomes evidence that no effect occurred.
- Retry first inspects authoritative state or uses the same idempotency identity.
- Deadline budget decreases across calls; nested components do not reset it.
- Old lease holders cannot publish after a newer generation is admitted.
- Wall-clock timestamps provide observability, not a total order of causality.
- Consumer-visible success requires durable output and publication evidence.

## Boundaries, time, and failure detection

| Boundary | Failure signal | What it proves | Safe next step |
| --- | --- | --- | --- |
| Process call | Return/exception | Local control flow ended | Inspect declared effects |
| Network call | Response | That response arrived | Validate operation identity/result |
| Network timeout | No timely response | Only that deadline elapsed | Query authoritative state before retry |
| Heartbeat expiry | No recent heartbeat | Suspicion, not certain death | Reassign with fencing |
| Storage commit | Conditional success | Named state transition won | Record version and publish evidence |

Use monotonic time for local elapsed duration and deadlines. Use UTC instants for
human correlation and retention. Use source offsets, versions, or logical sequence
numbers when order matters. Event time belongs to business records and may arrive
late; processing time belongs to an execution environment.

## Cancellation, shutdown, and recovery

Cancellation propagates intent from run to stage to attempt. Each boundary stops
admitting new work, closes streams and temporary files, records a terminal or
recoverable state, and acknowledges. A forceful process kill remains possible, so
cleanup cannot be the correctness mechanism. Candidates stay invisible until a
conditional manifest commit, and an orphan sweeper removes only objects proven
unreferenced after a retention delay.

## Failure model and recovery

| Failure | Detection | Containment and recovery | Consumer behavior |
| --- | --- | --- | --- |
| Request lost | No worker record for operation ID | Retry same identity within deadline | No visible change |
| Response lost after commit | Caller timeout; durable record exists | Return committed result; do not repeat effect | One result |
| Worker pause exceeds lease | Heartbeat/lease expiry | New generation starts; storage fences old attempt | Prior generation remains |
| Coordinator restarts | Durable run ledger versus active attempts | Reconcile, cancel/fence or resume | Published manifest is truth |
| Clock jumps | Wall/monotonic discrepancy | Ignore wall time for duration; alert host owner | No ordering claim from timestamps |

## Security, privacy, and governance

Authenticate workers and coordinators, authorize by run and dataset, encrypt
remote traffic, and never place record payloads or secrets in heartbeat labels.
Treat operation IDs as untrusted input and bound request sizes. Audit lease and
manual recovery transitions.

## Data quality, testing, and evidence

| Evidence | Procedure | Expected result | Result |
| --- | --- | --- | --- |
| Deterministic state-model test | Enumerate request/commit/response transitions | Timeout never implies absence | Pending |
| Delay/loss/duplicate test | Fault-inject messages around commit | One committed operation identity | Pending |
| Process-death test | Kill caller, worker, then coordinator | Durable state permits convergence | Pending |
| Stale-worker test | Pause past lease, start replacement, resume old worker | Old generation cannot publish | Pending |
| Clock test | Skew/jump wall clocks while measuring deadlines | Durations remain bounded | Pending |

Test doubles can validate transitions but not operating-system pauses, socket
behavior, storage durability, or real cross-process cancellation.

## Common pitfalls

### Pitfall: treating timeout as failure of the operation

The symptom is duplicate output after retry. Preserve a stable operation ID and
inspect durable state before repeating an ambiguous mutation.

### Pitfall: using timestamps as a global sequence

Clock skew can invert apparent order. Use source-specific sequence, version, or
consensus-assigned position where ordering is a contract.

### Pitfall: lease without fencing

A paused worker can resume after expiry. Require the durable commit boundary to
compare its generation, not merely ask workers to behave.

## Performance, operations, and compatibility

Budget connection, queue, service, retry, and commit time under one end-to-end
deadline. Observe latency percentiles, timeout class, attempt age, last progress,
heartbeat lag, lease generation, unknown-outcome count, and reconciliation time
with bounded-cardinality labels. During protocol evolution, accept old and new
request envelopes, preserve operation identity, drain incompatible attempts, and
prove mixed-version recovery before retiring old readers.

## Working example

- Python/tests: planned deterministic operation ledger and multi-process fault harness
- Expected result: request loss, response loss, process death, and stale attempts converge to one published outcome
- Scale represented: none yet; local model followed by multi-process evidence
- Remaining risk: real network partitions, scheduler pauses, storage failures, and clock behavior

## Knowledge check

1. Explain four states consistent with a timed-out commit request.
2. Predict what happens when an old worker resumes after lease replacement without fencing.
3. Choose the right clock or identifier for duration, business time, and ordering.
4. Design cancellation around an open candidate file and an in-flight commit.
5. Define evidence that a recovered run has converged.

## Key takeaways

- Silence is uncertainty; inspect durable truth before retrying.
- Deadlines and cancellation bound waste but do not undo remote effects.
- Leases detect stale ownership only when the commit path enforces fencing.
- Clocks serve different purposes and do not create a free global order.
- Recovery is a reconciled state, not merely a restarted process.

## Resources

- [RFC 9110: HTTP semantics and idempotent methods](https://www.rfc-editor.org/rfc/rfc9110.html#section-9.2.2) (reviewed 2026-09)
- [Python documentation: time](https://docs.python.org/3/library/time.html) (reviewed 2026-09)
- [The Chubby lock service for loosely-coupled distributed systems](https://research.google/pubs/the-chubby-lock-service-for-loosely-coupled-distributed-systems/) (reviewed 2026-09)

## Related topics

- [Retries, idempotency, speculation, and fault recovery](07-retries-idempotency-speculation-and-fault-recovery.md)
- [CAP, coordination, consensus, and metadata](04-cap-coordination-consensus-and-metadata.md)

## Completion checklist

- [x] Remote boundaries, uncertainty, clocks, deadlines, cancellation, leases, and fencing explained
- [x] Ownership, security, failure, recovery, observability, compatibility, and capacity addressed
- [ ] State-model, fault, process-death, stale-worker, and clock evidence run
