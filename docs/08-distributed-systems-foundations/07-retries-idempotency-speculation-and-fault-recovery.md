# Retries, Idempotency, Speculation, and Fault Recovery

> Status: Documentation complete; executable evidence planned  
> Level: Intermediate to Senior  
> Applies to: Generic data engineering / Distributed computation / Storage  
> Data scale: Local model; distributed and production estimates  
> Example status: Planned  
> Evidence status: None  
> Last reviewed: 2026-09

## Overview

Distributed engines routinely execute the same logical work more than once:
responses disappear, workers die, shuffle blocks vanish, leases expire, and slow
tasks may be speculated. Correctness therefore depends on stable logical identity,
deterministic derivation, isolated attempt output, fenced commit, and reconciliation.

“Exactly once” is not a property of task execution. It can describe a bounded
consumer-visible effect only when every boundary participates in a specific
protocol and its failure assumptions are stated.

## Learning objectives

- Separate logical operation, task, attempt, effect, and publication identity.
- Classify retryable, deterministic, capacity, and unknown-outcome failures.
- Design idempotent operations and attempt-safe output commit.
- Explain when speculation helps and when it amplifies load.
- Select replay, recomputation, checkpoint, or repair recovery.

## Prerequisites

- [Processes, networks, clocks, and partial failure](01-processes-networks-clocks-and-partial-failure.md)
- [MapReduce, DAGs, and data locality](05-mapreduce-dags-and-data-locality.md)
- [Shuffles, skew, stragglers, and hot partitions](06-shuffles-skew-stragglers-and-hot-partitions.md)

## Mental model and terminology

WorkManager's unique work and idempotent sync design are useful analogies. They
stop where one distributed stage has thousands of speculative attempts and
durable intermediate blocks whose winning versions must compose into one dataset.

```text
logical task (run=R, stage=S, partition=P)
       | attempt A1 -> private output O1 --\
       | attempt A2 -> private output O2 ---- conditional winner/commit
       | late A1 resumes -------------------X fenced
                                      winner referenced by generation manifest
```

| Term | Meaning in this guide |
| --- | --- |
| Logical task | Required work for one run, stage, and partition |
| Attempt | One execution of a logical task |
| Idempotency key | Stable logical identity used to recognize repeated effects |
| Attempt output | Private candidate identified by attempt and content/version |
| Speculation | Concurrent duplicate attempt intended to reduce tail latency |
| Checkpoint | Durable progress/state from which compatible work can resume |
| Convergence | All authoritative state and derived outputs reach one valid outcome |

## Requirements, assumptions, and invariants

Attempts may overlap and finish out of order. The pipeline reads immutable versioned
inputs and produces content-addressed or attempt-named candidates. The coordinator
may retry transient faults three times as an initial policy, but one global deadline
and attempt budget controls nested clients and tasks.

- One logical task contributes at most one winning output to a generation.
- Repeated execution over pinned inputs is deterministic or records nondeterminism.
- Attempt output never overwrites a shared final path before winner selection.
- Stale lease generations cannot commit even if they finish successfully.
- Unknown outcomes are inspected before a new mutation.
- Checkpoints bind to input, code, schema, routing, and state-format versions.
- Recovery ends only after manifest, checkpoints, counts, and consumers reconcile.

## Retry and speculation policy

| Condition | Retry/speculate? | Required guard | Stop condition |
| --- | --- | --- | --- |
| Brief dependency failure | Bounded retry | Idempotency plus jitter/deadline | Attempt/deadline budget |
| Commit timeout | Inspect, then maybe retry | Authoritative operation record | Outcome established |
| Invalid input/code defect | No blind retry | Quarantine or corrected version | Changed input/code/policy |
| Partition OOM/hot key | No identical retry loop | Repartition/algorithm/admission change | Headroom demonstrated |
| Random slow task | Maybe speculate | Fenced commit and spare capacity | Winner or overload threshold |
| Host lost with immutable input | Retry elsewhere | Reproducible input/version | Recovery budget |

Speculation should trigger from robust task-duration distributions plus progress,
not a fixed wall-clock alone. Do not speculate when most tasks are slow from shared
overload, when work has non-idempotent external effects, or when duplicate reads
would violate a dependency quota.

## Commit and checkpoint lifecycle

1. Register logical task and lease generation.
2. Attempt reads pinned inputs and writes a private candidate.
3. Attempt validates size, schema, checksum, grain, and counts.
4. Coordinator conditionally records one winner for the current generation.
5. Dataset publication references exactly the complete winning partition set.
6. Loser/orphan cleanup runs later against authoritative references.

Checkpointing trades recovery work for write cost and compatibility obligations.
Checkpoint state should be atomic at its declared scope and never advance beyond
durable output. Replaying raw immutable data is often simpler; checkpoints matter
when recomputation exceeds the recovery or source-retention budget.

## Failure model and recovery

| Failure | Detection | Containment and recovery | Consumer behavior |
| --- | --- | --- | --- |
| Worker dies before candidate | Lease/progress absent | Retry logical task | No visible change |
| Worker dies after candidate | Candidate exists; winner absent | Validate/reuse or retry | Candidate remains private |
| Response lost after winner commit | Attempt sees unknown outcome | Read winner record | No second contribution |
| Old attempt finishes late | Lower lease generation | Commit rejected; safe cleanup later | Current winner only |
| Corrupt checkpoint | Checksum/schema/version failure | Roll back to earlier point or replay | Prior generation remains |
| Speculation storm | Duplicate-attempt/resource metrics | Disable/throttle speculation and admission | Freshness may degrade explicitly |
| External sink lacks idempotency | Reconciliation detects duplicate/missing effect | Outbox/staging/compensation | Do not claim exactly once |

## Security, privacy, and governance

Attempt paths and idempotency keys are untrusted inputs: prevent traversal and
cross-tenant collisions. Restrict commit authority separately from compute, encrypt
checkpoints/candidates, redact record content from errors, audit overrides, and
retain loser outputs only as long as debugging and privacy policies allow.

## Data quality, testing, and evidence

| Evidence | Procedure | Expected result | Result |
| --- | --- | --- | --- |
| Retry state-model test | Enumerate failures around each transition | One winner or explicit failure | Pending |
| Duplicate-attempt test | Run attempts concurrently/out of order | One fenced commit | Pending |
| Determinism/property test | Repartition/retry same pinned inputs | Same certified business output | Pending |
| Checkpoint corruption/version test | Truncate or change checkpoint schema | Safe reject and replay/rollback | Pending |
| Speculation capacity test | Mix random slow and globally slow tasks | Tail improves only without overload | Pending |

## Common pitfalls

### Pitfall: write directly to the final partition path

Overlapping attempts can interleave or overwrite output. Write private candidates
and make one conditional metadata commit authoritative.

### Pitfall: random IDs on every retry

The system cannot correlate repeated logical work. Keep a stable operation/task
identity while assigning distinct attempt identities.

### Pitfall: checkpoint means exactly once

Checkpoint and sink commit can diverge. Define their atomic relationship or design
idempotent sink replay and reconciliation.

## Performance, operations, and compatibility

Track attempts per task, retries by class, unknown outcomes, speculative attempts
and wins, duplicate resource seconds, candidate/orphan bytes, checkpoint size/time,
recompute estimate, fenced commits, and convergence duration. Version checkpoint
formats and commit protocols; support old-state readers or drain/replay before
deployment, and rehearse rollback after a new writer has committed state.

## Working example

- Python/tests/data: planned task-attempt ledger, fenced committer, checkpoint format, and multi-process fault/speculation harness
- Expected result: duplicate and failed attempts converge to one complete dataset generation
- Scale represented: none yet; deterministic state model then multi-process faults
- Remaining risk: real storage atomicity, executor loss, external sinks, and shared-cluster contention

## Knowledge check

1. Distinguish logical task identity from attempt identity and output identity.
2. Predict the result of two attempts writing one shared final filename.
3. Classify timeout, corrupt input, OOM, and lost-worker failures.
4. Decide when checkpointing beats replay for the reference job.
5. Design a speculation policy that cannot worsen shared overload indefinitely.

## Key takeaways

- Duplicate execution is normal; duplicate consumer effects are a design choice.
- Stable identity, private candidates, winner selection, and fencing compose safe retry.
- Unknown outcomes require inspection and deterministic failures require change.
- Checkpoints bind to versions and cannot outrun durable effects.
- Speculation trades resources for tail latency and needs admission controls.

## Resources

- [MapReduce paper](https://research.google/pubs/mapreduce-simplified-data-processing-on-large-clusters/) (reviewed 2026-09)
- [RFC 9110: idempotent methods](https://www.rfc-editor.org/rfc/rfc9110.html#section-9.2.2) (reviewed 2026-09)

## Related topics

- [Checkpoints, idempotency, and atomic publication](../07-batch-processing-and-etl-elt/05-checkpoints-idempotency-and-atomic-publication.md)
- [Resource scheduling, backpressure, and capacity](08-resource-scheduling-backpressure-and-capacity.md)

## Completion checklist

- [x] Retries, identities, idempotency, speculation, commit safety, checkpoints, and convergence explained
- [x] Failure, security, quality, capacity, operations, compatibility, and external effects addressed
- [ ] Retry-model, duplicate-attempt, determinism, checkpoint, and speculation evidence run
