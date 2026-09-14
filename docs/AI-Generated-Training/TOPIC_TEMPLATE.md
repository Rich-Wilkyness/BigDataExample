# Topic title

> Status: Draft  
> Level: Beginner / Intermediate / Senior  
> Applies to: Generic data engineering / Python / SQL / Batch / Streaming / Storage / Platform  
> Data scale: Local fixture / Single machine / Distributed / Production estimate  
> Example status: Planned / Partial / Complete  
> Evidence status: None / Unit / Integration / Contract / Data quality / Performance / Resilience / Operational / Delivery  
> Last reviewed: YYYY-MM

## Using this template

Copy this file when beginning a learning topic and remove these instructions.
This is the learning-material contract; standalone interview-bank entries use
`INTERVIEW_QUESTION_TEMPLATE.md` instead.

Not every guide needs every subsection, but normally retain Overview, Learning
objectives, Mental model, Requirements and invariants, Data ownership and
boundaries, Failure model and recovery, Data quality and testing, Common
pitfalls, Production considerations, Knowledge check, and Completion checklist.

Begin with the durable data behavior or guarantee. Introduce Python, SQL, Spark,
Kafka, Airflow, a warehouse, a lakehouse, or a cloud product only after the
reader understands the problem it solves. Prefer a local example before a
distributed one, but do not imply that local evidence proves distributed or
production behavior.

Use Kotlin, coroutines, Room/SQLite, Gradle, or Android telemetry comparisons
when they help this repository's learner. State where each analogy stops being
accurate.

## Overview

Explain concisely:

- What the subject is.
- Why data engineers need it.
- Where it fits in the path from producer to consumer.
- Which parts are durable concepts and which depend on a language, engine,
  storage system, orchestrator, table format, or cloud.
- What is intentionally outside this guide.

## Learning objectives

After completing this guide, you should be able to:

- Explain ...
- Query or implement ...
- Diagnose ...
- Measure or verify ...
- Evaluate the tradeoffs between ...

## Prerequisites

List only required concepts, tools, datasets, and earlier guides. Separate
conceptual prerequisites from infrastructure required to run the evidence.

## Topical guide

1. Concept or data contract.
2. SQL or Python implementation mechanism.
3. Scale, concurrency, or failure scenario.
4. Production evolution and operational scenario.

## Terminology

Define unfamiliar, overloaded, or engine-specific terms precisely.

| Term | Meaning in this guide |
| --- | --- |
| Grain | What one record represents at a stated boundary |
| Owner | The system or team responsible for authoritative state, change, recovery, and lifecycle |
| Invariant | A condition that must remain true across reruns, failures, concurrency, and evolution |
| Guarantee | Behavior a producer or consumer may rely upon, including its limits |

## Requirements, scale assumptions, and invariants

State before selecting an implementation:

- Producer and consumer requirements.
- Expected rows, bytes, files, events, partitions, and growth rate.
- Batch window, latency, freshness, throughput, and concurrency needs.
- Correctness, completeness, availability, durability, and consistency needs.
- Security, privacy, locality, retention, deletion, and audit constraints.
- Compatibility, backfill, deployment, and cost constraints.
- Explicit non-goals.
- Invariants that must survive duplicates, late data, partial failure, and reruns.

Label estimates and assumptions. Name the evidence that would invalidate them.

## Mental model

Explain the central idea in plain language. Use a data-flow diagram, record
lifecycle, state machine, partition map, query plan, lineage graph, event-time
timeline, or comparison table when it materially improves understanding.

When translating from Kotlin, Android, or a transactional application, identify
both the useful analogy and the point at which scale, declarative execution,
distribution, or data lifetime makes it inaccurate.

## Data flow, ownership, and trust boundaries

| Boundary | Input contract | Authority and owner | Failure behavior | Trust level |
| --- | --- | --- | --- | --- |
| Example | Versioned event schema | Source system | Reject or quarantine invalid records | Untrusted input |

Cover relevant producer, API, database, broker, filesystem, object store,
catalog, processing engine, warehouse, serving system, and human operational
boundaries. Identify the authoritative dataset and every derived copy.

## Subtopic one

### Concept

Explain how it works and which guarantee it provides.

### SQL model or implementation

Show the relational, declarative, or analytical form where relevant. State the
dialect, `NULL` behavior, ordering assumptions, transaction boundary, and query
plan implications.

```sql
-- Explain grain, ownership, and why this operation is correct and rerunnable.
SELECT example_key, COUNT(*) AS example_count
FROM example_records
GROUP BY example_key;
```

### Python model or implementation

Show the relevant standard-library, typed-boundary, DataFrame, client, or engine
API. Explain iteration versus materialization, resource lifetime, errors,
serialization, concurrency, and memory behavior where relevant.

```python
# The caller owns the input iterator; processing remains bounded by batch size.
def transform(records: Iterable[InputRecord]) -> Iterator[OutputRecord]:
    ...
```

### Engine, storage, and infrastructure considerations

Cover relevant execution engine, partitioning, scheduling, shuffle, storage,
metadata, network, container, cloud, and operating-system behavior. Identify
which guarantee application code cannot provide by itself.

### Example walkthrough

Link to or include a focused example. Comments explain grain, ownership,
boundaries, invariants, laziness, materialization, partitioning, failure, and
observability—not obvious syntax.

After a substantial example:

1. Identify the producer, consumer, and entry point.
2. Trace validation, normalization, transformation, and publication.
3. Identify authoritative data, derived state, and commit/checkpoint boundaries.
4. Trace empty, invalid, duplicate, late, out-of-order, retry, and overload cases.
5. Explain logs, metrics, lineage, quality checks, and safe error records.
6. State what was tested and which scale or production assumptions remain.

### Example patterns

#### Smallest correct implementation

Start with the minimum correct contract. Add one production concern at a time,
such as schema validation, bounded memory, idempotency, checkpointing, late-data
handling, atomic publication, observability, or access control.

#### Avoid / Prefer

Place a tempting misuse beside a safer implementation. Explain the violated
invariant, observable symptom, and guarantee supplied by the repair.

#### Failure demonstration

Reproduce a minimal duplicate, dropped record, corrupt file, schema mismatch,
join explosion, skewed partition, out-of-memory condition, partial publication,
late event, stalled consumer, broken backfill, or incompatible deployment before
repairing it.

#### Decision table

| Requirement or constraint | Prefer | Why | Reconsider when |
| --- | --- | --- | --- |
| Example | Approach | Relevant guarantee | Evidence or condition that changes the choice |

## Record, file, job, and dataset lifecycle

Explain where relevant:

- Record creation, event time, ingestion time, normalization, and deletion.
- File creation, validation, atomic publication, compaction, and expiration.
- Job admission, scheduling, retries, cancellation, checkpointing, and shutdown.
- Dataset versioning, backfills, correction, retention, archival, and erasure.
- Connection, iterator, DataFrame, executor, memory, and temporary-storage ownership.
- Retry ownership, deduplication identity, and idempotency scope.

## Consistency, ordering, identity, and time

Explain:

- The consistency and freshness model consumers receive.
- Record identity, business keys, surrogate keys, and duplicate definition.
- Atomic operations and publication boundaries.
- Ordering guarantees and their partition scope.
- Missing, duplicate, delayed, corrupt, or out-of-order behavior.
- Event time, processing time, time zones, clock skew, windows, and watermarks.

## Architecture and dependency direction

Explain:

- Which system and team own each behavior and dataset.
- Dependency direction among producers, pipelines, storage, and consumers.
- Sources of truth, derived datasets, caches, and indexes.
- Whether a schema, table, event, file, API, module, job, or service boundary is useful.
- When an abstraction helps and when it hides engine or storage behavior.
- The migration path from the current design.

## Failure model and recovery

Enumerate realistic failures:

- Invalid, malicious, incompatible, or unexpectedly large input.
- Missing, duplicate, late, out-of-order, or partially delivered data.
- Dependency latency, timeout, throttling, or unavailability.
- Worker, driver, broker, database, storage, scheduler, or network failure.
- Resource exhaustion, skew, hot partitions, and small-file amplification.
- Partial output, corrupt checkpoints, failed backfills, and replay hazards.
- Mixed schema, code, engine, or table-format versions.
- Catalog, lineage, telemetry, or control-plane failure.

For each, identify detection, containment, retry or repair ownership, recovery,
consumer-visible behavior, and evidence of convergence.

## Security, privacy, and governance

Cover applicable concerns:

- Trust boundaries, threat model, and least privilege.
- Authentication, authorization, tenant isolation, and row/column access.
- Injection, unsafe deserialization, path traversal, and untrusted destinations.
- Secrets, encryption, key lifecycle, masking, and tokenization.
- Data classification, minimization, purpose limitation, retention, and deletion.
- Catalog, lineage, ownership, audit, and policy enforcement.
- Safe samples, logs, metrics, traces, quarantine records, and notebooks.

## Data quality, testing, and evidence

Choose evidence proportional to risk:

- Unit, property-based, and SQL assertion tests.
- Schema, contract, and compatibility tests.
- Data-quality tests for validity, completeness, uniqueness, freshness, volume,
  referential integrity, distribution, and reconciliation.
- Integration tests with real databases, storage, brokers, and engines.
- End-to-end pipeline and consumer tests.
- Migration, backfill, replay, rollback, and restore rehearsals.
- Load, scale, soak, skew, fault-injection, and cost tests.
- Dashboards, alerts, runbooks, lineage, and operational reviews.

| Evidence | Dataset and environment | Command or procedure | Expected result | Result |
| --- | --- | --- | --- | --- |
| Example | Bounded fixture / Local | `command` | Invariant survives a rerun | Pending |

Distinguish deterministic fixtures and test doubles from real-engine,
distributed, cloud, and production evidence.

## Debugging guide

Include:

- Observable symptom and affected consumers.
- Likely owning dataset, job, boundary, or platform component.
- Dataset samples, rejected-record paths, logs, metrics, traces, lineage, query
  plans, task timelines, partition sizes, offsets, and checkpoints to inspect.
- Correlation, run, batch, event, partition, schema, and dataset-version identifiers.
- Safe reproduction, mitigation, replay, and repair procedures.
- Evidence required before declaring root cause and recovery complete.

## Common pitfalls

### Pitfall: descriptive name

Explain why it occurs, which invariant it violates, its downstream symptom, how
to reproduce it, and how to repair or prevent it. Use an Avoid/Prefer pair or a
failure demonstration when code or SQL makes the distinction clearer.

## Performance, capacity, and cost

Cover relevant rows, bytes, events, files, partitions, cardinality, selectivity,
latency percentiles, throughput, concurrency, CPU, memory, disk, network,
shuffle, queue depth, storage growth, and monetary cost. Define a budget before
optimizing and record workload assumptions with results.

## Observability and operations

Define:

- Structured operational events and their privacy classification.
- Metrics, labels, units, and cardinality limits.
- Traces and lineage across pipeline boundaries.
- Freshness, completeness, correctness, latency, and availability indicators.
- Objectives, alerts, ownership, escalation, and runbook steps.
- Readiness, liveness, checkpoint, drain, restart, and shutdown behavior.
- Backup, restore, disaster recovery, data repair, and reconciliation.

## Compatibility, migration, backfill, and delivery

Cover schema, event, file, table, code, dependency, configuration, and engine
evolution. Include mixed-version operation, expand/migrate/contract sequencing,
dual reads or writes where justified, historical backfills, validation, atomic
cutover, rollback constraints, and post-deployment reconciliation.

## Engineering tradeoffs

Compare reasonable choices using requirements and evidence. Do not present
Python, SQL, a DataFrame library, Spark, Kafka, Airflow, a warehouse, a lakehouse,
a table format, or a cloud service as universally correct.

## Working example

- Python source: `src/big_data_example/...`
- SQL: `sql/...`
- Tests: `tests/...`
- Data or fixture: `data/...`
- Infrastructure: `infra/...` when applicable
- Try it: Exact command and input procedure
- Expected result: Success and relevant failure behavior
- Evidence: Test, quality result, query plan, task timeline, metric, or runbook
- Scale represented: Local fixture / Single machine / Distributed / Production estimate
- Remaining risk: Untested scale, failure, compatibility, security, or cost assumption

Mark missing examples as Planned rather than adding decorative code.

## Knowledge check

Prefer practical exercises:

1. Explain the mental model and record grain in your own words.
2. Predict a SQL query, Python transform, or state transition before running it.
3. Diagnose a realistic quality, scale, ordering, or recovery failure.
4. Design a repair before viewing the repository solution.
5. Estimate capacity and identify the first likely bottleneck or cost driver.
6. Propose a safe schema change, backfill, cutover, and rollback.
7. Implement and verify one bounded modification manually.

## Key takeaways

- Capture three to seven durable guarantees or reasoning tools.
- Prefer data contracts, execution behavior, and failure reasoning over product trivia.

## Resources

Prefer primary sources:

- Language, SQL dialect, engine, and storage documentation.
- File, serialization, table-format, protocol, and security specifications.
- Authoritative architecture, reliability, and operational guidance.
- Research papers when they define the concept being taught.

Record review dates for version-sensitive behavior.

## Related topics

- Link related curriculum guides.

## Completion checklist

- [ ] Durable concept and mental model explained
- [ ] Prerequisites and explicit non-goals identified
- [ ] Grain, owners, consumers, sources of truth, and trust boundaries identified
- [ ] Scale, freshness, correctness, availability, retention, and cost assumptions explicit
- [ ] SQL and Python behavior covered where relevant
- [ ] Engine, storage, scheduler, broker, catalog, and infrastructure behavior covered where relevant
- [ ] Identity, `NULL`, ordering, consistency, and time semantics covered
- [ ] Empty, invalid, duplicate, late, out-of-order, retry, overload, and recovery behavior addressed
- [ ] Security, privacy, governance, retention, and deletion addressed
- [ ] Correct example linked or marked Planned
- [ ] Failure demonstrated before repair where executable
- [ ] Tests, data-quality checks, and concrete evidence recorded
- [ ] Fixtures and test doubles distinguished from real and distributed integrations
- [ ] Performance, capacity, partitioning, and cost assumptions included
- [ ] Logs, metrics, traces, lineage, alerts, and runbooks covered where relevant
- [ ] Compatibility, migration, backfill, deployment, and rollback covered
- [ ] Tradeoffs tied to requirements and evidence
- [ ] Knowledge check requires prediction, diagnosis, design, and modification
- [ ] `COVERAGE.md` updated accurately
- [ ] Primary resources reviewed and version-sensitive claims dated

