# Collections, Iteration, Generators, and Bounded Memory

> Status: Documentation complete  
> Level: Beginner to Intermediate  
> Applies to: Python / Local batch processing  
> Data scale: Bounded fixture and single-machine estimate  
> Example status: Design complete; executable benchmark planned  
> Evidence status: Documentation review; unit and memory evidence pending  
> Last reviewed: 2026-09

## Overview

An iterable describes how values can be requested; an iterator is the stateful,
single-pass cursor producing them. A generator is one convenient iterator. These
abstractions allow memory use to depend on batch size rather than total input,
but laziness alone does not guarantee bounded memory: sorting, grouping, caching,
duplicate state, and careless fan-out can still materialize the dataset.

This guide covers local record flow. Distributed partitions, shuffles, DataFrame
optimizers, and file-layout mechanics belong to later areas.

## Learning objectives

- Distinguish container, iterable, iterator, generator, and materialized result.
- Predict when work, I/O, and exceptions occur in a lazy pipeline.
- Design batches with an explicit peak-memory bound.
- Identify operations that require global or per-key state.
- Define iterator ownership, replay, cancellation, and cleanup behavior.

## Prerequisites

Complete guide 01 and understand the reference event grain. Familiarity with
Kotlin collections and `Sequence` is assumed.

## Mental model

```text
re-iterable source --iter()--> one-shot cursor --next()--> record
                                           |
                                    lazy transform chain
                                           |
                           bounded batch or materialized sink
```

Python iterables resemble Kotlin `Iterable`, and generators resemble sequences
in lazy pipelines. The analogy stops because a Python iterator is itself mutable
state, often owns I/O indirectly, and may be one-shot. Calling `iter(x)` does not
promise a fresh independent traversal.

## Terminology

| Term | Meaning |
| --- | --- |
| Iterable | Object from which an iterator can be requested |
| Iterator | Stateful object returning the next item or raising `StopIteration` |
| Generator | Iterator produced by a function containing `yield` or expression syntax |
| Materialization | Retaining values in a concrete collection or external dataset |
| Working set | Memory needed by active records and algorithmic state |
| Backpressure | Mechanism that stops producers outrunning bounded downstream capacity |

## Requirements, scale assumptions, and invariants

Assume 3 million daily events averaging 1 KiB serialized. Deserialized Python
objects may occupy several times their serialized size; that multiplier must be
measured. The local parser uses batches of at most 1,000 records. It must preserve
input order where promised, classify every consumed item, and not retain prior
batches except explicitly bounded identity or metric state.

```python
from collections.abc import Iterable, Iterator
from itertools import islice
from typing import TypeVar

T = TypeVar("T")

def batched(source: Iterable[T], size: int) -> Iterator[tuple[T, ...]]:
    if size <= 0:
        raise ValueError("size must be positive")
    cursor = iter(source)
    while batch := tuple(islice(cursor, size)):
        yield batch
```

The returned generator does no consumption until iteration. Each tuple
materializes at most `size` references, while downstream transformation objects
add to the actual peak. The caller still owns and closes the source.

## Execution behavior

### Lazy versus eager

List, set, and dictionary comprehensions materialize. Generator expressions do
not. `map`, `filter`, `enumerate`, and many `itertools` functions are lazy;
`list`, `sorted`, `sum`, `min`, `max`, grouping into a dictionary, and most
serializers consume input. Some consumers short-circuit, so cleanup and metrics
cannot assume the source was exhausted.

Generator code executes on the first and subsequent `next` calls, not at generator
construction. Parsing exceptions therefore appear at consumption sites. Place
record-level containment where one bad record can be quarantined, and job-level
containment around the resource/publication boundary.

### Hidden unbounded state

- Exact global sort requires retaining data or spilling through an external algorithm.
- Exact deduplication requires identity state proportional to distinct keys unless
  input is partitioned/sorted or state is stored externally.
- `itertools.tee` may buffer the gap between consumers.
- Grouping into lists retains all group members; aggregate incrementally instead.
- A queue without `maxsize` transfers the out-of-memory risk between stages.

### One pass, replay, and time

A consumed iterator cannot generally rewind. Retry needs a replayable source,
immutable input file/version, or checkpoint at a defined boundary. Never retry by
reusing an unknown partially consumed iterator. Event order from a file is not
automatically event-time order, and stable local order is not a distributed
ordering guarantee.

## Ownership and lifecycle

| Object | Owner | Lifetime and failure behavior |
| --- | --- | --- |
| File/client iterable | Caller | Open through consumption; close on success, failure, or cancellation |
| Iterator/generator | Transform caller | Single traversal; explicitly close if abandoning resource-owning generator |
| Batch tuple | Current stage | Release after publication/checkpoint of that batch |
| Deduplication state | Job/state component | Bounded by declared retention or externalized |
| Output transaction | Publisher | Commit only a complete validated unit; abort partial work |

Avoid a function that both opens a file and returns a lazy iterator after its
context has exited. Prefer caller-owned resources or a context manager that keeps
the resource lifetime visible.

## Failure model and recovery

| Failure | Signal | Recovery contract |
| --- | --- | --- |
| Invalid record mid-batch | Indexed validation error | Quarantine safe reference; continue only if policy allows |
| Source read fails | I/O exception and offset | Abort batch; reopen replayable version at checkpoint |
| Consumer stops early | Generator not exhausted | Close stack/resource; do not mark input complete |
| Memory grows with rows | Profile/RSS slope | Find retained references/global state; bound, spill, or change algorithm |
| Duplicate after retry | Reconciliation by event ID | Idempotent sink or deduplication in declared scope |
| Output fails after input advances | Missing commit/checkpoint | Replay from last committed boundary, never guessed cursor state |

## Data quality, security, and evidence

Limit record bytes, nesting, batch size, field lengths, and decompressed volume.
A tiny compressed input can expand dramatically. Do not include complete rejected
records in logs. Count consumed, accepted, rejected, deferred, and published
identities so early termination and silent loss are visible.

| Evidence | Dataset/environment | Expected result | Result |
| --- | --- | --- | --- |
| Unit cases | Empty, exact batch, remainder, invalid size | Correct batches and no lost rows | Pending |
| Property tests | Generated finite sequences and sizes | Flattened batches equal input exactly | Pending |
| Memory profile | Increasing generated record counts | Peak follows batch/state bound, not total rows | Pending |
| Failure injection | Source/output fails at each batch | Replay converges without double count | Pending |

An in-memory generator validates iteration logic but not file buffers, parser
allocation, OS caching, serializer behavior, or sink atomicity.

## Debugging guide and common pitfalls

1. Record input version, checkpoint, batch index, consumed/published counts, RSS,
   queue depth, and largest record; use bounded-cardinality labels.
2. Inspect reference holders and materialization sites before changing batch size.
3. Reproduce with empty input, one item, boundary sizes, a huge item, duplicate,
   early consumer exit, and injected read/write failure.
4. Repair from the last committed immutable boundary and reconcile identities.

Common mistakes are returning a generator tied to a closed file, iterating a
one-shot cursor twice, assuming a generator makes `sorted` bounded, using an
unbounded queue, and measuring only serialized input bytes. A smaller batch can
reduce peak memory but increase call, I/O, and commit overhead; choose from an
explicit memory and throughput budget.

## Performance, operations, and compatibility

Measure records/s, bytes/s, batch latency percentiles, peak resident memory,
allocation hotspots, queue depth, GC time, output commits, and rejected/duplicate
rates. Warm caches and synthetic uniform records can mislead; include large and
skewed shapes. On overload, bound admission and expose backlog age rather than
allowing memory to become the queue.

Changing batch size should not change logical rows. A code rollout must preserve
checkpoint and serialized-state compatibility or start from a safe immutable
boundary. Backfills receive separate capacity and versions so they cannot starve
the daily run.

## Working example

- Python source/tests: Planned for `batched` and the event transform
- Data: Planned deterministic JSON Lines fixture plus generated records
- Expected behavior: Exact accounting with peak working set bounded by batch and
  declared state
- Evidence: Pending unit/property tests and memory profile
- Remaining risk: Real parser, filesystem, sink, concurrency, and production scale

## Knowledge check

1. Predict when an exception in a generator body becomes visible.
2. Find the hidden materialization in a lazy chain ending in `sorted`.
3. Design exact deduplication for a cardinality larger than memory.
4. Specify a checkpoint that safely handles output failure after source consumption.
5. Estimate a starting batch size from measured bytes per parsed record and a
   256 MiB working-set budget, then name the missing measurements.

## Key takeaways

- Iterable, iterator, and materialized collection have different replay semantics.
- Laziness defers work; it does not prove bounded state or resource safety.
- Batch, queue, record, and retained-key bounds must all be explicit.
- Replay begins from a durable commit/checkpoint, not a half-consumed cursor.
- Memory and throughput claims require representative measurement.

## Resources

- [Python 3.12 iterator types](https://docs.python.org/3.12/library/stdtypes.html#iterator-types)
- [Python 3.12 itertools](https://docs.python.org/3.12/library/itertools.html)
- [Python 3.12 generator expressions](https://docs.python.org/3.12/reference/expressions.html#generator-expressions)

## Related topics

- [Area README](README.md)
- [Errors, context managers, and resource lifetime](04-errors-context-managers-and-resource-lifetime.md)
- [Testing, profiling, memory, and Python performance](08-testing-profiling-memory-and-python-performance.md)

## Completion checklist

- [x] Iteration model, ownership, scale, materialization, replay, and failure covered
- [x] Quality, security, observability, performance, and compatibility addressed
- [x] Evidence boundary and practical exercises explicit
- [ ] Iterator/property tests implemented
- [ ] Memory and fault behavior measured
