# Errors, Context Managers, and Resource Lifetime

> Status: Documentation complete  
> Level: Intermediate  
> Applies to: Python / Files / Clients / Batch jobs  
> Data scale: Bounded local batches  
> Example status: Failure design complete; executable injection planned  
> Evidence status: Documentation review; resilience evidence pending  
> Last reviewed: 2026-09

## Overview

Exceptions transfer control; they do not undo consumed input, remote writes, or
mutated state. A context manager gives a lexical owner the chance to acquire and
release a resource on normal exit, exception, and cancellation. Correct data jobs
combine this local lifetime mechanism with explicit staging, commit, checkpoint,
and idempotency boundaries.

The Kotlin `use` analogy is helpful for closeable resources. It stops at external
atomicity: neither `use` nor Python `with` makes several files, API calls, or
database systems one transaction.

## Learning objectives

- Classify record, batch, dependency, cancellation, and programming failures.
- Use context managers and `ExitStack` to make dynamic ownership visible.
- Preserve causal exceptions and safe diagnostic context.
- Design retry and cleanup around explicit commit boundaries.
- Prove partial work is contained and recovery converges.

## Prerequisites

Complete guides 01–03. Understand one-shot iterators, replayable input, and the
pure-policy/impure-shell split.

## Mental model

```text
acquire -> process -> validate -> stage -> commit
   |          |          |         |
   +---------- exception/cancel ---+
                    |
             close/abort resources
                    |
       retry from last durable boundary
```

Cleanup answers “what local resources are released?” Recovery answers “what
externally visible state exists and how does the next attempt converge?” They are
related but distinct contracts.

## Terminology

| Term | Meaning |
| --- | --- |
| Context manager | Object defining enter/exit behavior around a lexical scope |
| Commit boundary | Point after which output is intentionally consumer-visible/durable |
| Record failure | One input violates a known data rule |
| System failure | Dependency or resource prevents reliable continuation |
| Programming defect | Broken invariant or unexpected code behavior, not bad data |
| Exception chaining | Preserving an original cause while adding boundary context |

## Requirements and invariants

Every consumed record becomes accepted, safely rejected, or part of an explicitly
failed/uncommitted batch. No exception may cause a batch to be marked complete
before output commit. Resources close in reverse acquisition order. Retry policy
is bounded and owned by the orchestration shell, not nested independently in each
adapter.

```python
from contextlib import ExitStack
from pathlib import Path

def copy_stage(inputs: list[Path], stage: Path) -> None:
    with ExitStack() as stack:
        sources = [stack.enter_context(path.open("rb")) for path in inputs]
        target = stack.enter_context(stage.open("xb"))
        for source in sources:
            while chunk := source.read(1024 * 1024):
                target.write(chunk)
        target.flush()
        # Publication is intentionally outside this function.
```

This bounds each read, but dynamic simultaneous sources still consume one handle
per input. A production fan-in should also bound open handles and verify bytes,
checksums, and expected input completeness before publication.

## Error boundaries and exception design

Catch only where code can add ownership context, translate to a stable domain
failure, safely classify a record, retry an idempotent operation, or clean up.
Use specific exceptions. Preserve causes with `raise NewError(...) from error`.
A bare `except` also catches process-control exceptions; routine record handling
should generally catch `Exception` or narrower types and let cancellation/exit
signals propagate after required cleanup.

Do not retry validation errors. Retry transient dependency failures only with a
budget, backoff/jitter, deadline, and idempotency key. An ambiguous timeout may
mean the remote side committed; query/reconcile state rather than assuming failure.

### Context-manager guarantees and limits

`with` calls exit logic even when the body raises. Exit logic may suppress an
exception, so suppress only an expected narrow condition. Cleanup can itself fail;
preserve the primary failure and report cleanup failure without losing causality.
Garbage collection is not a timely resource-lifetime contract.

Generators that own resources require special care when consumers stop early.
Prefer the caller opening the resource within a visible `with`, or return a context
manager whose yielded iterator remains valid only inside its scope.

## Data ownership and publication

| Boundary | Owner | Commit/recovery behavior |
| --- | --- | --- |
| Immutable input/version | Ingestion/source | Reopen by version and checkpoint |
| Parser and transform | Pipeline | Record classification; no external commit |
| Staging file/table | Run attempt | Unique attempt path; delete/expire after failure |
| Published dataset/version | Publisher | Visible only after quality gate and atomic supported operation |
| Checkpoint | Orchestrator/state owner | Advance only with corresponding durable output |

Local rename atomicity depends on filesystem and operation; object stores and
databases expose different semantics. Application context managers cannot invent
a multi-system transaction. Prefer immutable versioned outputs and a supported
catalog/table/database commit, then reconcile.

## Failure model and recovery

| Failure | Detection | Containment | Recovery proof |
| --- | --- | --- | --- |
| Invalid record | Rule ID and safe reference | Quarantine or reject per policy | Accounting equation balances |
| Read fails mid-batch | Exception plus input offset | No checkpoint advance | Replay yields same logical results |
| Write fails during staging | Short write/exception/checksum | Staging remains invisible | Orphan cleaned; prior version intact |
| Timeout after remote commit | Timeout with idempotency key | Do not blindly repeat side effect | Query/reconcile key and final state |
| Cancellation/shutdown | Task/process signal | Stop admission, finish/abort owned unit, close | No half-published output |
| Cleanup fails | Chained/aggregated error | Mark attempt uncertain/failed | Resource and external state inspected |
| Disk full | Capacity/error signal | Stop before publish | Space restored; staging removed; rerun passes |

## Security, observability, and data quality

Never embed secrets, full payloads, SQL text containing values, or sensitive paths
in exceptions. Stable error codes should reveal rule and owning boundary without
becoming high-cardinality metrics. Structured events include run ID, attempt,
dataset/input version, batch, checkpoint, code/config/schema versions, and safe
counts.

Quality gates verify schema, uniqueness, completeness, volume, and reconciliation
before commit. “No exception” is not evidence of correct data. Alert separately on
failure rate, retry exhaustion, oldest uncommitted input, orphan staging, and
cleanup errors.

| Evidence | Procedure | Expected result | Result |
| --- | --- | --- | --- |
| Unit failure table | Raise at acquire/read/transform/write/close | Correct exception and cleanup order | Pending |
| Publication integration | Interrupt before/during/after commit | Old or new complete version only | Pending |
| Replay test | Fail each batch once and rerun | Same logical output/no double effect | Pending |
| Shutdown test | Cancel with full queues/open resources | Bounded drain and released resources | Pending |

## Debugging and pitfalls

Start at the consumer-visible version and last successful checkpoint. Inspect
attempt-specific staging, commit marker/transaction, exception chain, retry count,
and resource saturation. Reproduce at the same failure boundary; do not replay
until ambiguous external state is reconciled.

Avoid `except Exception: pass`, catch-and-return-empty, returning a lazy reader from
a closed context, advancing a checkpoint before output commit, and layered retries
whose product exceeds the job deadline. A `finally` block is appropriate for local
cleanup but does not compensate external side effects.

## Performance, compatibility, and operations

Opening per record is safe but often too costly; opening once forever risks stale
connections and poor recovery. Scope resources to a bounded batch/run and measure
connection/handle limits, timeout percentiles, retries, staged bytes, and cleanup
latency. Deploy changes that can read old checkpoints and distinguish old staging
formats. If that is impossible, drain old workers and restart from an immutable
boundary under a new version namespace.

## Working example

- Planned evidence: Context-manager unit tests and staged-publication fault injection
- Current artifact: Lifecycle, exception, and recovery contracts above
- Expected result: No consumer-visible partial output; rerun converges
- Remaining risk: Filesystem/database/object-store-specific atomicity and real shutdown behavior

## Knowledge check

1. Predict which resources close when the third `ExitStack` acquisition fails.
2. Classify parse error, disk full, timeout-after-commit, and assertion failure.
3. Design a safe retry for a remote write whose response was lost.
4. Place checkpoint advancement relative to staging, quality checks, and commit.
5. Specify fault injection needed to prove old-or-new publication visibility.

## Key takeaways

- Exceptions do not roll back data or un-consume iterators.
- Context managers make local lifetime explicit; commit protocols make output safe.
- Retry depends on failure class, deadline, and idempotency.
- Preserve causal errors and protect sensitive values.
- Recovery is complete only after reconciliation proves convergence.

## Resources

- [Python 3.12 exceptions](https://docs.python.org/3.12/tutorial/errors.html)
- [Python 3.12 contextlib](https://docs.python.org/3.12/library/contextlib.html)
- [Python 3.12 with statement](https://docs.python.org/3.12/reference/compound_stmts.html#the-with-statement)

## Related topics

- [Area README](README.md)
- [Collections, iteration, generators, and bounded memory](02-collections-iteration-generators-and-bounded-memory.md)
- [Threads, asyncio, processes, and parallel data work](07-threads-asyncio-processes-and-parallel-data-work.md)

## Completion checklist

- [x] Error classification, lifecycle, ownership, commit, retry, and recovery explained
- [x] Security, quality, observability, performance, and compatibility covered
- [ ] Failure-injection and replay tests implemented
- [ ] Real publication and shutdown behavior verified

