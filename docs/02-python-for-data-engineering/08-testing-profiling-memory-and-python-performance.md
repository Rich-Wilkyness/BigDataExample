# Testing, Profiling, Memory, and Python Performance

> Status: Documentation complete  
> Level: Intermediate to Senior  
> Applies to: Python / Local data pipelines / Engineering evidence  
> Data scale: Deterministic fixtures through single-machine estimates  
> Example status: Reference evidence portfolio designed; implementation planned  
> Evidence status: Package smoke test only; all topic-specific evidence pending  
> Last reviewed: 2026-09

## Overview

Correctness evidence asks whether a transform preserves its data contract across
edge cases, reruns, and failures. Performance evidence asks whether a named
workload meets a resource and time budget. Tests, profiles, benchmarks, and
operational signals answer different questions; none substitutes for the others.

This capstone designs the evidence portfolio for the bounded event parser and
transformation library. It does not claim that local fixtures prove distributed
engines or production workloads.

## Learning objectives

- Build layered unit, property, contract, integration, and failure evidence.
- Design fixtures around grain, identity, time, invalid data, and reconciliation.
- Measure CPU, allocation, retained memory, RSS, throughput, and latency correctly.
- Diagnose before optimizing and preserve semantics through changes.
- Define regression gates, operational signals, and remaining evidence risk.

## Prerequisites

Complete guides 01–07 and Area 01's first pipeline walkthrough. The current
repository provides Python 3.12+, `unittest`, and a package smoke test. No property
test, static checker, benchmark, or profiler automation has yet been selected.

## Mental model

```text
contract + workload + budget
          |
 deterministic fixture and failure model
          |
 correctness tests ----> profile representative run
          |                         |
 mutation/edge confidence     locate bottleneck
          |                         |
          +---- safe optimization -+
                        |
          rerun correctness + benchmark + recovery
```

This resembles Android unit/instrumentation/macrobenchmark layering. The analogy
stops because data correctness also needs record accounting, schema compatibility,
replay/backfill, distribution/skew, and consumer-level reconciliation across long
dataset lifetimes.

## Terminology

| Term | Meaning |
| --- | --- |
| Fixture | Controlled data with declared provenance and expected outcomes |
| Property test | Generated cases checked against a general invariant |
| Mutation test | Deliberately changes code to see whether tests detect the defect |
| Profile | Attribution of time or memory within one observed run |
| Benchmark | Repeatable comparison against a defined workload and budget |
| Allocation | Memory requested during execution; not necessarily retained/RSS |
| Reconciliation | Cross-boundary accounting proving no unexplained loss/duplication |

## Reference requirements and invariants

The planned library accepts a caller-owned iterable of untrusted event mappings in
batches of at most 1,000. It returns one immutable valid event or safe rejection
per consumed identity. Fixed input, configuration, cutoff, and code version produce
the same logical results. Input is not mutated. Peak application working memory
should be bounded by batch plus declared state, not total row count.

Initial performance hypotheses—not acceptance evidence—are at least 1,250
accounted events/s for the Area 01 baseline batch window, process RSS below a
future explicitly approved budget, and no unbounded growth as generated input
increases at fixed batch/key-state bounds. Before implementation, refine these
using representative record sizes, parsing, sink behavior, concurrency, hardware,
and headroom.

## Evidence layers

### Unit and table tests

Test pure rules for valid records, every missing/null/type/range/version state,
empty input, duplicate identity, timestamps on interval boundaries, alias
normalization, and non-mutation. Assert values and accounting, not internal call
sequences. Use a fake clock only through an explicit clock/cutoff dependency.

### Property and mutation tests

Useful properties include: flattening batches reproduces input order; accepted +
rejected equals consumed; normalization is idempotent under one rule version;
rerunning yields the same keyed results; and output keys remain unique. Generators
must be bounded so a failing case can shrink and reproduce. Mutation testing can
reveal tests that would miss removing deduplication, changing `<` to `<=`, or
turning rejection into silent null.

### Contract and integration tests

Contract tests run producer/consumer schema version matrices. Integration tests
use the real parser, filesystem/serializer, and later selected sink. They verify
encoding, ranges, timezone behavior, atomic publication, permissions, cleanup, and
ambiguous timeout recovery. Test doubles cannot supply this evidence.

### Failure and recovery tests

Inject read, parse, worker, write, commit, cleanup, cancellation, disk/capacity, and
dependency failures at controlled boundaries. Verify prior published data remains
readable, attempt staging is isolated, checkpoint does not lie, replay converges,
and reconciliation balances.

## Fixture design and data quality

One deterministic safe fixture should include valid records, duplicate delivery,
missing and null fields, empty/unknown screen, unsupported schema, Unicode, large
but allowed values, just-over-limit values, out-of-order event times, late receipt,
and exact cutoff boundaries. It contains no production personal data. Record its
schema, generator seed/version, expected identities, counts, and provenance.

Quality assertions cover validity, completeness, uniqueness, referential rules,
freshness/cutoff, volume, distributions, and cross-stage reconciliation. A golden
file is appropriate only when reviewed meaning is stable; it should not turn an
accidental byte ordering or formatting choice into the business contract.

## Measuring CPU and time

First define hardware, interpreter/build, dependency/artifact versions, data shape,
cache conditions, warm-up, repetitions, concurrency, and sink. Wall time measures
the consumer objective; process/thread CPU distinguishes computation from waits.
Use `cProfile` for deterministic call-level CPU attribution and `timeit` only for
small isolated operations. Statistical profilers may reduce observer effect in
longer runs but require a selected tool.

Report throughput with latency percentiles, failures, retries, and output counts.
A faster run producing fewer valid outputs is a correctness regression. Compare a
simple baseline, change one material factor, repeat enough to expose variance, and
retain raw results with environment metadata.

## Measuring memory

`sys.getsizeof` is shallow and excludes referenced graphs. `tracemalloc` observes
many Python allocations and can compare snapshots, but it does not represent all
native allocations or complete process resident memory. Measure both allocation
attribution and OS-level peak/RSS using an explicitly selected cross-platform
procedure. Account separately for parsed objects, batches, queues, dedup state,
native buffers, worker processes, memory mapping, and OS cache where relevant.

Run a growth experiment at fixed batch/state bounds across increasing row counts.
After warm-up, retained memory should plateau within a justified range. Also test
one huge record, high cardinality, skew, slow sink/backpressure, and failure paths;
happy-path uniform generators commonly conceal the real peak.

## Optimization decision order

1. Verify the contract and locate the measured bottleneck.
2. Remove unnecessary work, copies, parsing, materialization, and repeated lookups.
3. Choose an algorithm with bounded/suitable state before micro-optimizing syntax.
4. Batch I/O and serialization within latency/memory/failure constraints.
5. Use appropriate native/vectorized or SQL/engine operations when semantics match.
6. Add bounded concurrency only after wait/CPU/resource evidence supports it.
7. Re-run correctness, compatibility, failure, memory, and benchmark evidence.

Vectorization can move loops to optimized native code and compact memory, but it
may require materialization, change null/type/time behavior, or hide copies. A
distributed engine can exceed local capacity but adds shuffle, serialization,
scheduling, skew, and commit concerns. Neither is automatically faster for small data.

## Failure model for evidence itself

| Failure | Symptom | Repair |
| --- | --- | --- |
| Fixture omits boundary state | Production-only defect | Add provenance-driven case/property and mutation |
| Flaky time/order test | Nondeterministic failure | Inject cutoff/seed; assert keyed results where order is irrelevant |
| Benchmark measures warm cache only | Unrealistic speed | Document cold/warm scenarios and target workload |
| Profiler changes result materially | Distorted attribution | Compare profiled/unprofiled; use appropriate sampler/tool |
| RSS grows due to queued work | OOM despite small batches | Bound count and bytes; profile retained references |
| Optimization changes semantics | Faster wrong output | Gate on reconciliation/contract before performance |
| Local test overclaimed | False readiness | Label environment and retain distributed/production gaps |

## Security, privacy, and governance

Fixtures are synthetic or approved/minimized. Profiles, traces, failure artifacts,
heap dumps, temp files, and benchmark outputs may contain values and therefore
need access, retention, encryption, deletion, and review. Use safe summaries and
bounded labels. Never upload a production heap/profile to an external service
without explicit authorization and classification review.

Dependency and test tools execute code in the build environment; pin/review them
under the delivery policy. Performance tests must not become accidental denial of
service against shared dependencies.

## Observability and debugging guide

For a regression, identify first affected artifact/config/schema/data version and
consumer. Confirm output reconciliation before examining speed. Compare wall/CPU,
RSS/allocation snapshots, queue bytes/age, record-size/cardinality distributions,
GC, I/O rates, retries, and external latency. Reproduce from immutable input or a
privacy-safe equivalent and vary one dimension at a time.

Operational signals mirror test assertions: consumed/valid/rejected/duplicate/
published totals, freshness cutoff age, batch and commit latency, throughput,
backlog, largest record/batch, RSS, worker saturation, retries, and version IDs.
Alerts require an owner and repair/runbook action, not merely a threshold.

## Evidence plan

| Evidence | Dataset/environment | Command/procedure | Expected result | Result |
| --- | --- | --- | --- | --- |
| Existing package smoke | Local Python 3.12.3 | `python -m unittest discover -s tests` | Package imports | Passed previously |
| Parser unit/table | Planned safe fixture | Same test entry point | Exact classification and non-mutation | Pending |
| Property/mutation | Generated bounded records | Tool to be selected | Invariants survive; seeded reproduction | Pending |
| Static type check | Package source | Tool to be selected | Public/internal contracts pass | Pending |
| Memory growth | Generated 1x/10x/100x rows | `tracemalloc` plus selected RSS measurement | Peak follows bounds, not total rows | Pending |
| CPU/throughput | Representative record shapes | Profile then controlled benchmark | Meet approved budget with correct totals | Pending |
| Concurrency/process | Slow I/O and CPU fixtures | Sweep bounded workers; inject cancellation | Same results; safe shutdown/recovery | Pending |
| Real boundary integration | Parser/filesystem/selected sink | Interrupt and reconcile publication | Old or new complete version | Pending |

## Compatibility, delivery, and cost

Regression results are comparable only when environment metadata is retained.
Canary new parser/rule versions, dual-evaluate a safe sample where justified,
compare distributions and identities, backfill a bounded interval, then publish
atomically. Keep old readers and artifacts until rollback and retained data are
compatible. Isolate benchmark/backfill capacity from the daily objective.

Model developer/test runtime, CI compute, stored fixtures/artifacts, worker CPU and
memory, I/O, and downstream repair cost. A small optimization rarely justifies
opaque code unless measured frequency and lifetime savings outweigh maintenance
and incident risk.

## Working example

- Python source: Planned under `src/big_data_example` as a bounded event library
- Tests: Planned under `tests` using the existing standard-library baseline first
- Data: Planned safe deterministic fixture under `data`
- Try it: Pending implementation; no command beyond the package smoke test is claimed
- Expected result: Exact classification, idempotent logical output, bounded memory,
  safe failure/replay, and measured throughput against an approved budget
- Evidence represented: Design portfolio only, plus existing package import smoke
- Remaining risk: All parser-specific, static, property, integration, performance,
  concurrency, resilience, distributed, operational, and production evidence

## Knowledge check

1. Design the smallest fixture that kills mutants removing deduplication and
   changing the event-time upper bound from exclusive to inclusive.
2. Explain what `tracemalloc`, RSS, and serialized input bytes each omit.
3. Build a benchmark matrix varying record size, cardinality, skew, and sink speed.
4. Diagnose a transform that is twice as fast but publishes 1% fewer rows.
5. Propose a safe vectorized rewrite rollout with semantic and rollback checks.
6. Decide which evidence can remain local and which requires a real sink or cluster.

## Key takeaways

- Evidence begins with a named contract, workload, environment, and budget.
- Reconciliation and failure recovery are as important as happy-path unit output.
- Allocation profiles, RSS, CPU profiles, and benchmarks answer different questions.
- Optimize measured algorithms and boundaries before syntax or concurrency.
- Local evidence must remain explicitly local.

## Resources

- [Python 3.12 unittest](https://docs.python.org/3.12/library/unittest.html)
- [Python 3.12 profiling](https://docs.python.org/3.12/library/profile.html)
- [Python 3.12 tracemalloc](https://docs.python.org/3.12/library/tracemalloc.html)
- [Python 3.12 timeit](https://docs.python.org/3.12/library/timeit.html)
- [Python 3.12 resource module](https://docs.python.org/3.12/library/resource.html)

## Related topics

- [Area README](README.md)
- [Collections, iteration, generators, and bounded memory](02-collections-iteration-generators-and-bounded-memory.md)
- [Threads, asyncio, processes, and parallel data work](07-threads-asyncio-processes-and-parallel-data-work.md)
- [First end-to-end data pipeline](../01-big-data-and-data-engineering-foundations/08-first-end-to-end-data-pipeline.md)

## Completion checklist

- [x] Evidence hierarchy, fixtures, quality, profiling, memory, performance, and recovery covered
- [x] Security, operations, compatibility, delivery, scale limits, and cost explicit
- [x] Reference evidence portfolio and pending risks recorded accurately
- [ ] Parser/transformation implementation and tests completed
- [ ] Static, property, mutation, memory, benchmark, concurrency, and integration evidence run
