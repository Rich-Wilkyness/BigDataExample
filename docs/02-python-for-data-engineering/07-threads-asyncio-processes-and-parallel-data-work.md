# Threads, Asyncio, Processes, and Parallel Data Work

> Status: Documentation complete  
> Level: Intermediate to Senior  
> Applies to: Python / Concurrent local data work  
> Data scale: Single machine with bounded task/queue estimates  
> Example status: Decision model complete; executable evidence planned  
> Evidence status: Documentation review; concurrency/performance/resilience pending  
> Last reviewed: 2026-09

## Overview

Concurrency manages overlapping work; parallelism executes work simultaneously.
Choose a model from workload, library behavior, resource ownership, cancellation,
ordering, and measurement—not from task count alone. Threads often suit blocking
I/O, asyncio suits large cooperative I/O sets with async-compatible libraries, and
processes can provide CPU parallelism and isolation at serialization/coordination cost.

For the repository's Python 3.12 CPython baseline, one global interpreter lock
(GIL) normally prevents multiple threads from executing Python bytecode in
parallel within one interpreter. Native operations may release it. Optional
free-threaded CPython builds began in 3.13 and continue to evolve; code must not
use the GIL as a data-race correctness guarantee.

## Learning objectives

- Distinguish concurrency, parallelism, asynchrony, and distribution.
- Select threads, asyncio, processes, or sequential work from evidence.
- Bound tasks, queues, connections, memory, and retries under overload.
- Design ordering, identity, cancellation, shutdown, and commit behavior.
- Recognize GIL, native-library, serializer, and process-start boundaries.

## Prerequisites

Complete guides 01–06. Understand iterator/resource ownership, idempotent replay,
and clean package entry points.

## Mental model

```text
admission bound
     |
bounded work queue ----> N workers ----> bounded result queue
     |                       |                    |
backpressure          owned resources      ordered/atomic commit
                             |
                   cancel -> drain/abort -> close
```

Kotlin coroutines help with structured lifetimes, but Python `asyncio` tasks run
cooperatively on an event loop and blocking calls can stall it. Neither model
automatically bounds fan-out or makes side effects idempotent. Python processes
are stronger isolation boundaries than coroutines and resemble separate app
processes more than coroutine dispatchers.

## Terminology

| Term | Meaning |
| --- | --- |
| Concurrency | Multiple tasks are in progress during overlapping time |
| Parallelism | Work executes simultaneously on multiple compute resources |
| GIL | CPython interpreter lock whose exact scope/build behavior is implementation-specific |
| Event loop | Scheduler advancing cooperative async tasks around awaitable operations |
| Backpressure | Feedback/admission that bounds outstanding work |
| Start method | How a child process is created and initialized |
| Serialization boundary | Conversion/copy needed to transfer process/task data |

## Requirements, scale assumptions, and invariants

Assume a single-machine batch has 1,000-record input batches, at most 16 in-flight
I/O operations, at most four CPU worker processes, and a measured memory budget.
These are starting hypotheses. Connection pools, remote quotas, queue length,
payload size, and retry concurrency must be bounded together.

Every input identity receives one terminal classification. Task completion order
does not redefine event order. Publication/checkpoint order is explicit. Failure
of one task cannot silently orphan siblings. Shutdown stops admission, cancels or
drains under a deadline, closes worker resources, and leaves no partial published unit.

## Model selection

| Workload/constraint | Starting choice | Why | Reconsider when |
| --- | --- | --- | --- |
| Simple bounded work meets window | Sequential | Lowest failure/ordering complexity | Measurement misses objective |
| Blocking file/API/database calls | Bounded threads | Works with synchronous clients; overlaps waits | Client is not thread-safe or async fan-out is materially better |
| Many async-compatible I/O waits | `asyncio` with semaphore/TaskGroup | Cooperative structured fan-out | Blocking/native calls stall loop or ecosystem is sync-only |
| Pure Python CPU transform | Bounded processes | Multiple interpreters/cores | Serialization/startup dominates or native vectorized engine fits |
| Native CPU library releasing GIL | Measure threads | May parallelize without process copies | Oversubscription or library thread safety hurts |
| Multi-host durability/scale | Later distributed engine | Local primitives lack scheduler/state guarantees | Never infer from local speedup alone |

### Threads

Shared objects require synchronization around multi-step invariants even on a
GIL-enabled CPython build. The GIL is neither a transaction nor a portable memory
model. Give each worker its own non-thread-safe client or use a documented safe
pool. Bound executor submissions; an executor with a large producer backlog can
retain every argument and defeat streaming.

### Asyncio

An async function runs synchronously until it awaits. A blocking parser, client,
sleep, or filesystem call on the event-loop thread stalls all tasks. Use structured
groups, explicit timeouts, semaphores, and cancellation-safe cleanup. Cancellation
arrives at suspension points and can race with an external commit; reconcile
ambiguous state. Never create one task per retained record without a bound.

### Processes

Processes isolate Python heaps and can execute CPU work in parallel, but inputs,
results, exceptions, and configuration cross serialization/IPC boundaries. Avoid
shipping huge parsed object graphs; partition by coarse bounded units or use an
appropriate external format. On Windows and common portable configurations,
children start fresh interpreters: protect entry points, keep tasks importable,
and initialize clients in the child. Document and test the selected start method.

Nested native parallelism can oversubscribe cores when several worker processes
each create their own thread pools. Measure total CPU, memory, disk, and network.

## Ownership, ordering, and commit

| State/resource | Owner | Rule |
| --- | --- | --- |
| Input partition/batch | Coordinator | Assign stable identity; retry from immutable version |
| Client/connection | Worker or documented pool | Create/close within worker lifetime; least privilege |
| Queue/task set | Coordinator | Bound outstanding count/bytes and observe age |
| Per-key state | Single owner or synchronized store | Partition consistently; declare ordering scope |
| Staging output | Attempt | Unique namespace; consumers cannot see it |
| Publication/checkpoint | Coordinator/publisher | Commit complete validated unit, then advance coherently |

Preserving input order may require buffering slow earlier results. If consumers do
not require order, publish at a grain where deterministic keys make order irrelevant.
Ordering within a local task pool says nothing about ordering across a distributed
partition or rerun.

## Failure, overload, and recovery

| Failure | Detection | Containment/recovery |
| --- | --- | --- |
| Worker/task raises | Await/future result with task ID | Cancel/continue per batch policy; retry idempotent unit |
| Event loop blocked | Loop lag/task latency | Move/blocking work appropriately; reduce work per callback |
| Process dies | Broken pool/exit status | Discard uncertain attempt output; recreate and replay |
| Queue/arguments exhaust memory | Queue bytes/RSS | Stop admission; reduce bound/payload or externalize state |
| Remote throttles | Status/latency/retry-after | Shared rate/admission control; avoid retry storm |
| Timeout after side effect | Deadline plus unknown remote result | Reconcile idempotency key before retry |
| Shutdown deadline | Signal and drain timer | Stop admission; finish or abort atomic units; force only after state record |
| One hot key serializes work | Per-key latency/queue | Repartition/change algorithm without breaking key semantics |

Do not let each layer retry independently. A three-attempt client inside a
three-attempt task inside a three-attempt job can produce 27 calls before
concurrency amplification. One owner budgets attempts and total deadline.

## Security, quality, and observability

Workers receive only required credentials and fields. Process serialization must
not accept untrusted pickle data; pickle can execute code during deserialization.
Do not leak payloads through task exceptions, debug queues, or process command
lines. Treat temporary files/shared memory as sensitive governed storage.

Metrics include admitted/active/completed/failed/cancelled tasks, queue count and
bytes, oldest age, worker utilization, loop lag, pool restarts, retries, remote
throttles, batch commit latency, and reconciliation totals. Labels use bounded
worker/task classes, not event IDs.

| Evidence | Workload/procedure | Expected result | Result |
| --- | --- | --- | --- |
| Determinism test | Random task completion delays | Same keyed output/counts | Pending |
| Bound test | Slow sink and growing finite input | In-flight count/bytes stay bounded | Pending |
| Cancellation test | Stop during read/compute/write/commit | No orphan visible output; resources close | Pending |
| Process test | Spawn workers with representative payload | Correct serialization/startup/failure propagation | Pending |
| Benchmark | I/O-bound and CPU-bound fixtures | Selected model beats baseline within budget | Pending |

## Debugging and pitfalls

Capture run/batch/task/attempt IDs, selected model/start method, worker count,
queue bytes/age, resource pool use, deadlines, cancellation state, and commit
version. Inspect the first causal failure rather than a cascade of cancelled tasks.
Reproduce with one worker, then increase concurrency while holding data constant.

Pitfalls include assuming threads make Python CPU work parallel, assuming the GIL
makes compound state safe, mixing blocking calls into the event loop, unbounded
`gather`/executor submission, passing open clients to processes, depending on fork
state, ignoring result retrieval, and benchmarking only happy-path throughput.

## Performance, capacity, compatibility, and delivery

Start sequential, profile wait versus CPU, then sweep bounded concurrency. Measure
throughput and latency percentiles alongside correctness, RSS, serialization bytes,
context switching, connection usage, remote errors, and recovery time. More workers
can reduce throughput through contention, rate limits, oversubscription, or skew.

Changing worker count must not change logical output. Mixed deployments need
compatible task and result schemas; process tasks should carry versioned plain
data, not fragile internal object graphs. Drain old workers or support both
versions, isolate backfills, canary under real bounds, and preserve rollback readers.

## Working example

- Planned source: Sequential, bounded-thread, asyncio, and process variants around
  controlled I/O- and CPU-bound fixtures
- Expected result: Same logical outputs; explicit cancellation and resource cleanup
- Evidence: Pending correctness, benchmark, memory, and fault-injection runs
- Remaining risk: Real clients, native libraries, platform start methods, and production load

## Knowledge check

1. Choose a model for blocking API calls plus CPU-heavy parsing and justify boundaries.
2. Explain why an executor consuming a generator may still retain excessive work.
3. Design ordering/commit behavior when task 5 finishes before task 4.
4. Trace cancellation after a remote side effect but before its response.
5. Build a concurrency sweep plan that can detect rate-limit and memory regressions.

## Key takeaways

- Choose concurrency from workload and evidence; sequential is the correctness baseline.
- Bound outstanding tasks, bytes, queues, clients, retries, and state together.
- GIL behavior is interpreter/build-specific and is not a synchronization contract.
- Cancellation and timeouts create uncertain external state that requires reconciliation.
- Local parallel speedup does not prove distributed correctness or capacity.

## Resources

- [Python 3.12 concurrent futures](https://docs.python.org/3.12/library/concurrent.futures.html)
- [Python 3.12 asyncio tasks](https://docs.python.org/3.12/library/asyncio-task.html)
- [Python 3.12 multiprocessing](https://docs.python.org/3.12/library/multiprocessing.html)
- [PEP 703: optional GIL in CPython](https://peps.python.org/pep-0703/)
- [PEP 779: free-threaded support criteria](https://peps.python.org/pep-0779/)

## Related topics

- [Area README](README.md)
- [Errors, context managers, and resource lifetime](04-errors-context-managers-and-resource-lifetime.md)
- [Testing, profiling, memory, and Python performance](08-testing-profiling-memory-and-python-performance.md)

## Completion checklist

- [x] Models, GIL boundaries, bounds, ownership, ordering, failures, and shutdown covered
- [x] Security, evidence, performance, compatibility, and operations explicit
- [ ] Correctness/concurrency/process tests implemented
- [ ] Benchmarks, memory, cancellation, and real-client evidence executed

