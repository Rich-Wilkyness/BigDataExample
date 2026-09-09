# 02 Python for Data Engineering

> Area status: Documentation complete; executable reference example planned  
> Level: Beginner to Intermediate data engineering  
> Runtime baseline: Python 3.12 or newer; behavior called out when interpreter-specific  
> Reference scenario: Bounded parser and transformation library for mobile events  
> Evidence boundary: Documentation and design review; package smoke test only  
> Last reviewed: 2026-09

## Purpose

This area teaches the Python execution behavior that data engineers must reason
about before using DataFrames, Spark, orchestration frameworks, or cloud SDKs.
The learner already knows Kotlin, so the guides concentrate on semantic gaps:
runtime typing, mutable object graphs, iterator ownership, exceptions and cleanup,
process boundaries, and measurement.

The durable goal is not Python syntax fluency. It is the ability to build a
transform whose record meaning, resource use, failure behavior, and evidence are
clear enough to run repeatedly against untrusted and growing data.

## Prerequisites

- Complete [01 Big Data and Data Engineering Foundations](../01-big-data-and-data-engineering-foundations/README.md), especially record grain, authority, and publication boundaries.
- Install a Python interpreter satisfying the root `pyproject.toml` contract.
- No third-party library, database, distributed engine, or notebook is required.

## Learning path

1. [Python runtime, types, and Kotlin comparisons](01-python-runtime-types-and-kotlin-comparisons.md)
   establishes the object and execution model.
2. [Collections, iteration, generators, and bounded memory](02-collections-iteration-generators-and-bounded-memory.md)
   separates lazy record flow from materialization.
3. [Functions, classes, dataclasses, protocols, and modules](03-functions-classes-dataclasses-protocols-and-modules.md)
   defines small reusable transformation boundaries.
4. [Errors, context managers, and resource lifetime](04-errors-context-managers-and-resource-lifetime.md)
   makes partial work and cleanup explicit.
5. [Type hints, validation, and untrusted data](05-type-hints-validation-and-untrusted-data.md)
   separates developer-facing static contracts from runtime data checks.
6. [Environments, packaging, dependencies, and reproducibility](06-environments-packaging-dependencies-and-reproducibility.md)
   connects source code to a repeatable runnable artifact.
7. [Threads, asyncio, processes, and parallel data work](07-threads-asyncio-processes-and-parallel-data-work.md)
   selects concurrency from workload and boundary behavior.
8. [Testing, profiling, memory, and Python performance](08-testing-profiling-memory-and-python-performance.md)
   combines the area into an evidence plan for the reference library.

## Shared reference contract

The planned implementation consumes an iterator of untrusted mappings. One input
record represents one delivered mobile event envelope. It emits either one typed,
normalized event or one safe rejection; it never silently drops an input.

The pipeline owns validation and transformation logic. The caller owns the input
resource and publication transaction. Event identity is the producer's stable
`event_id`; delivery order is not business order. Processing must remain bounded
by a configured batch size, produce deterministic results for fixed input and
configuration, and avoid sensitive payloads in errors or telemetry.

```text
caller-owned input iterator
          |
    bounded batches
          |
runtime validation -> safe rejection
          |
typed normalized event
          |
caller-owned publication boundary
```

This resembles a Kotlin `Sequence` feeding pure mappers behind typed interfaces.
The analogy stops at runtime enforcement: Python hints are not JVM bytecode type
checks, iteration may execute arbitrary user code, and mutable objects can be
shared without declarations in their types.

## Evidence and scope

The repository currently proves only that its package imports in the configured
local test environment. The parser, fixtures, unit/property tests, type check,
memory profile, and concurrency/process demonstrations remain planned. Each guide
therefore distinguishes language guarantees from CPython details and design
examples from executed evidence.

Pandas, NumPy, Polars, PyArrow, Spark, and orchestration products are intentionally
outside this area. Later areas can adopt them after the standard-library execution
and ownership model is understood.

## Area completion checklist

- [x] Eight inventory guides authored in the planned order
- [x] Python/Kotlin semantic differences and interpreter boundaries stated
- [x] Bounded iteration, validation, resource, failure, and concurrency contracts designed
- [x] Packaging, security, observability, compatibility, and profiling concerns covered
- [x] Evidence limitations recorded without claiming runtime verification
- [ ] Bounded parser and transformation library implemented
- [ ] Unit/property tests and static type check executed
- [ ] Memory, process, cancellation, and concurrency evidence collected

