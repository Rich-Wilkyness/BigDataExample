# Testing, Tuning, Failure Diagnosis, and Deployment

> Status: Documentation complete; executable evidence planned  
> Level: Intermediate to Senior  
> Applies to: PySpark / Spark SQL / Batch / Platform / Operations  
> Data scale: Local fixture; distributed and production estimates  
> Example status: Planned  
> Evidence status: None  
> Last reviewed: 2026-09

## Overview

A Spark job is ready for production only when correct results, physical behavior,
failure recovery, packaging, publication, observability, and capacity have been
verified at appropriate layers. A local fixture can prove transformation semantics;
it cannot prove network shuffle, executor loss, real connector permissions,
cluster dependency distribution, or production-scale skew.

Tuning is a measured control loop: define a correctness and service budget,
capture a baseline, identify the dominant operator/resource, change one justified
factor, and compare results and costs. Configuration folklore and “more executors”
are not evidence.

## Learning objectives

- Design a test pyramid from pure logic through local Spark, integrations, and multi-worker failure evidence.
- Build fixtures for nulls, duplicates, invalid data, skew, schema change, and reruns.
- Diagnose SQL queries through plans, stages, tasks, executor metrics, logs, and lineage.
- Tune from bytes, cardinality, distribution, CPU, memory, disk, network, and deadline budgets.
- Package, configure, deploy, backfill, canary, roll back, and operate a PySpark application safely.

## Prerequisites

- All earlier guides in this area
- [Lineage, testing, operating, and evolving batch pipelines](../07-batch-processing-and-etl-elt/08-lineage-testing-operating-and-evolving-batch-pipelines.md)
- [Resource scheduling, backpressure, and capacity](../08-distributed-systems-foundations/08-resource-scheduling-backpressure-and-capacity.md)

## Mental model and evidence ladder

Android has unit, instrumentation, device matrix, release, crash, and performance
evidence. Spark similarly needs layers. The analogy stops because distributed
tasks retry, shuffle over networks, depend on storage/catalog services, and publish
multi-file datasets whose correctness is not represented by one process exit code.

```text
pure transformation/reference tests
              |
              v
local Spark schema + result + plan tests
              |
              v
real format/storage/catalog integration tests
              |
              v
multi-worker shuffle + failure + packaging tests
              |
              v
representative load/skew/cost tests
              |
              v
canary/shadow publication + production reconciliation
```

Higher layers add evidence; they do not replace cheaper lower-layer diagnosis.

| Evidence layer | Proves | Does not prove |
| --- | --- | --- |
| Pure Python/SQL reference | Business examples and edge semantics | Spark schema/plan/runtime behavior |
| Local Spark | API, analyzed execution, real engine semantics on one machine | Remote serialization/network/executor loss |
| Storage/catalog integration | Connector, permissions, format, metadata, commit behavior | Multi-worker shuffle or representative capacity |
| Multi-worker fault test | Task retry, executor loss, shuffle recovery | Production distribution/cost/SLO |
| Representative load test | Capacity and skew for stated workload | Future growth or every failure |
| Production canary | Authorized environment behavior on bounded scope | Safety outside canary scale without extrapolation |

## Requirements, budgets, and invariants

The reference daily job has a 45-minute completion objective plus 15-minute
recovery reserve. Initial input is 3 million events/day and about 3 GiB compressed;
one tenant may account for 35%. Before implementation, define maximum driver
result bytes, task input/shuffle bytes, spill, retry count, output files, candidate
retention, and acceptable cost per run. Values remain hypotheses until measured.

- Pinned input, schema, code, configuration, and dimension versions yield the same business result on rerun.
- Accepted + quarantined records reconcile to observed inputs under documented duplicate handling.
- Strategy/partition/configuration changes cannot bypass result and quality comparisons.
- No failed or partial candidate becomes current.
- Logs, metrics, and tests do not expose sensitive record values.
- Deployment artifacts reproduce the same Python dependencies on driver and executors.
- Backfill and scheduled runs use isolated generation identities and cannot overwrite each other accidentally.

## Data quality, testing, and evidence

### Deterministic contract fixture

Include at minimum:

- empty input and one valid event;
- `NULL`, missing, blank, malformed, and unknown fields;
- minimum/maximum decimals, overflow, timestamp boundaries, and daylight-saving cases;
- exact duplicates and conflicting duplicate IDs;
- matched, missing, duplicate, and overlapping-effective-time dimension rows;
- many small keys, one 35% hot key, and one oversized nested/string value;
- late correction and a rerun with a different partition count;
- injected read, Python-worker, executor, write, quality-gate, and publish failures.

Expected outputs should be hand-checkable and expressed at business grain. Compare
unordered rows unless ordering is explicitly part of the contract. Use a separate
reference implementation only if it is simpler enough not to repeat the same bug.

### Planned test shape

```python
def test_daily_metrics_are_partition_invariant(spark, event_fixture, products):
    expected = expected_daily_metrics()

    for partitions in (1, 2, 8):
        actual = build_daily_metrics(
            event_fixture.repartition(partitions), products
        )
        assert_rows_equal_unordered(actual, expected)


def test_duplicate_dimension_key_fails_before_publish(spark, events, bad_products):
    with pytest.raises(DimensionContractError):
        build_candidate(events, bad_products)
    assert_current_generation_unchanged()
```

The code is planned, not executed. Tests should configure a fresh, owned Spark
session/warehouse/temp directory and stop/clean it predictably. Exact helpers and
framework integration belong in the future executable pass.

### Evidence matrix

| Evidence | Dataset/environment | Command/procedure | Expected result | Result |
| --- | --- | --- | --- | --- |
| Unit/reference | Hand-calculated fixture | Future Python test command | Exact transform and validation semantics | Pending |
| Local Spark contract | Same fixture / pinned local Spark | Future test suite | Schema, SQL/DataFrame, null/time, rerun pass | Pending |
| Plan contract | Selective, small-side, skew fixtures | Capture normalized initial/final plans | Pruning/exchanges/strategy explained | Pending |
| Data quality | Valid/invalid/duplicate/late fixtures | Reconcile counts, keys, sums, freshness | All declared equations pass | Pending |
| Storage/catalog integration | Real selected provider | Write, interrupt, register, read | Atomic current generation | Pending |
| Multi-worker fault | Distributed test cluster | Kill executor/drop shuffle during run | Exact result after retry | Pending |
| Packaging | Clean driver/executor images | Submit pinned artifact/environment | Imports and versions match | Pending |
| Load/skew | Representative widths/distribution | Baseline then one-change trials | Meets runtime/recovery/resource/cost budgets | Pending |
| Backfill/rollback | Isolated historical scope | Shadow, reconcile, cut over, roll back | No mixed or lost generation | Pending |

## Tuning method

1. Freeze input manifest, schema, code, configuration, cluster shape, and expected result.
2. Record baseline end-to-end and per-stage runtime, plan, rows/bytes, shuffle, spill, GC, task distribution, files, and cost.
3. Identify the dominant wait/resource: admission, scan/listing, CPU, serialization, shuffle/network, memory/GC, spill/disk, skew, output commit, or quality/publish.
4. Choose one causal change: prune/project, repair cardinality, update statistics, adjust join strategy, rebalance partitions, compact files, remove UDF, change cache, or right-size resources.
5. Re-run the same input; first prove exact/tolerance-defined result equivalence and quality, then compare the full budget.
6. Test a failure and representative skew after the improvement.
7. Record the result with versions and either keep or revert the change.

| Symptom | First evidence | Likely next action |
| --- | --- | --- |
| Long planning, short tasks | File count/listing/catalog timing | Compact files or repair metadata/layout |
| Few long scan tasks | Task input bytes/file distribution | Split/compact source layout appropriately |
| Huge join shuffle | Cardinality, projections, sizes, strategy | Fix multiplicity, prune columns, or safe broadcast/pre-aggregate |
| One long reduce task | Max/median shuffle rows/bytes and hot keys | AQE, isolate/pre-aggregate/salt proven skew |
| High JVM GC/spill | Peak memory, row width, concurrent tasks, cache | Reduce per-task state/cache or right-size after proof |
| Slow Python stage | Python operator, batch/group sizes, CPU | Replace with built-in or benchmark vectorized/native option |
| Driver failure | Collected/result/broadcast bytes | Remove/unbound driver materialization |
| Many tiny outputs | Output task/file histogram | Separate compute partitions from controlled file layout |

## Failure model and recovery

| Failure | Detection and containment | Recovery owner and convergence proof |
| --- | --- | --- |
| Invalid or incompatible input | Schema/quality gate rejects or quarantines the declared scope | Dataset owner repairs/replays; input = accepted + rejected under duplicate policy |
| Driver loss | Application ends or stops progressing; candidate stays private | Orchestrator restarts the pinned run; prior generation remains current |
| Executor/Python-worker loss | Failed attempt, executor event, or shuffle fetch loss | Spark retries pure work; cluster test proves exact reconciled output |
| Skew/OOM/disk exhaustion | Task maxima, spill, GC, worker exit, or no-progress alert | Job/platform owner repairs plan/layout/resources and reruns within recovery budget |
| Storage/catalog outage or throttling | Bounded timeout/error and publication failure | Platform/dataset owner retries only safe operations; no mixed generation is visible |
| Partial candidate or failed quality gate | File inventory, schema, count, or metric mismatch | Candidate is abandoned/repaired in a new generation; consumers retain prior version |
| Bad release or dependency mismatch | Startup/import/plan/result regression in canary | Release owner rolls back artifact/config and catalog pointer, then reconciles |
| Telemetry/control-plane degradation | Missing event logs/metrics/lineage or alert health failure | Operations restores visibility; correctness-critical uncertainty blocks publication |

### Diagnosis and recovery workflow

1. Declare affected dataset generation, consumers, freshness/correctness impact, and whether prior data is still safe.
2. Freeze publication if correctness is uncertain; preserve the input and failed-run manifests.
3. Locate the boundary: admission, driver, scan, stage/task, shuffle, Python worker, output commit, quality gate, catalog/publish, or consumer read.
4. Correlate application, run, SQL execution, job, stage, partition, task attempt, executor, input object, and generation IDs.
5. Compare plans and configuration with the last known-good run; compare task distributions rather than only averages.
6. Reproduce on the smallest fixture that preserves the fault, key distribution, width, or dependency mismatch.
7. Repair into a new candidate; reconcile records/keys/metrics/files and prove convergence after retry.
8. Publish atomically, monitor consumers, document root cause and prevention, then clean abandoned data under retention policy.

The Spark UI exposes jobs, stages, executors, storage, and SQL queries; the History
Server reconstructs completed application views from persisted event logs. These
are operational metadata systems with access and retention requirements. Preserve
event logs before an incident, not after the driver disappears.

## Observability and runbook contract

Structured lifecycle events should include `run_id`, `application_id`, input and
output generation IDs, code/config/schema versions, and coarse status/reason—not
raw sensitive values. Metrics should have bounded labels and units:

- run admission wait, duration, freshness lag, and success/failure;
- input files/bytes/rows, accepted/rejected/duplicate rows, and reconciliation delta;
- job/stage/task counts, failed/retried tasks, executor loss, max/median task ratio;
- scan/shuffle/spill/output bytes, peak memory, GC time, cache usage, and Python time where available;
- candidate files/bytes, quality-gate duration, publication duration, and abandoned candidates;
- estimated monetary/resource cost per successful generation.

Alert on consumer-impacting objectives or actionable precursors: missed freshness,
no progress, correctness/reconciliation failure, retry storm, executor churn,
extreme skew, storage errors, or publication failure. Each alert needs an owner,
safe first action, escalation, and evidence required to close it.

## Packaging, configuration, and submission

```text
versioned Python application artifact
  + exact PySpark/Python/Java compatibility
  + connector/catalog packages
  + executor Python environment
  + reviewed non-secret configuration
  + runtime secret references/identity
  + schema and metric-definition versions
  -> spark-submit / platform submission API
```

Use a real module entry point rather than notebook state. Keep environment-specific
paths, resource sizing, and credentials outside transformation code; validate
required configuration at startup. Package Python dependencies so every executor
uses a compatible environment. Spark's documented options include `--py-files`
for Python code and archive mechanisms for environments, with cluster-manager
specific constraints. Choose one delivery mechanism and verify it on clean nodes.

Configuration precedence can span command line, `SparkConf`, properties files,
environment, SQL/session settings, and platform defaults. Emit an allowlisted
effective configuration snapshot and reject dangerous/missing combinations. Do
not log secrets.

## Deployment, migration, backfill, and rollback

Use expand/migrate/contract:

1. Add backward-compatible readers/schema and versioned metric logic.
2. Produce shadow candidates for bounded recent dates using the new artifact.
3. Compare schema, counts, keys, values, plans, resources, and consumer queries.
4. Canary a non-critical or small scope with explicit current-generation commit.
5. Expand while watching freshness, correctness, task distribution, and cost.
6. Backfill history into isolated generation namespaces; reconcile each closed scope.
7. Contract old fields/config/artifacts only after consumer and rollback windows.

Rollback switches consumers to the last certified generation and prior compatible
code/config. If an irreversible schema/catalog change or external side effect
prevents that, the release is not rollback-ready and needs a forward-repair plan
before deployment.

## Security, privacy, and governance

- Authenticate submitters and use least-privilege driver/executor/storage/catalog identities.
- Scan and sign/version artifacts according to platform policy; prohibit arbitrary dependency downloads at runtime.
- Protect secrets through platform references and rotate without rebuilding transformation logic.
- Restrict UI, history, logs, plans, environment pages, thread/heap diagnostics, quarantine, and event logs.
- Use synthetic/de-identified fixtures; control production samples and debug exports.
- Track lineage from input generation through code/config/schema to candidate/current generation.
- Exercise retention and deletion across raw, curated, candidates, cache/spill, event logs, backups, and derived outputs.

## Common pitfalls

### Pitfall: local mode called an integration or distributed test

Local Spark is real-engine evidence on one machine. Label it accurately and add
real storage/catalog and multi-worker fault layers.

### Pitfall: tuning from aggregate application duration

One number cannot distinguish queue time, listing, scan, shuffle, skew, Python,
commit, or quality gates. Diagnose operator/stage/task distributions and bytes.

### Pitfall: configuration changes without result comparison

A faster result can be wrong due to join multiplicity, overflow, pruning bug,
nondeterminism, or changed UDF coercion. Correctness and reconciliation gate every
performance result.

### Pitfall: using notebook success as a deployable artifact

Notebook state hides initialization order, dependencies, credentials, and cleanup.
Extract a versioned application with a deterministic entry point and tests.

## Engineering tradeoffs

| Decision | Prefer when | Cost/risk |
| --- | --- | --- |
| Local Spark tests | Fast structured-engine feedback | No remote/network/failure proof |
| Ephemeral multi-worker cluster | Retry, packaging, and shuffle evidence | Infrastructure setup and test time |
| Cache | Measured reuse benefit | Memory, spill, cleanup, sensitive copies |
| More executor cores | Tasks are CPU-bound and memory per concurrent task is safe | More simultaneous memory/I/O pressure |
| More executors | Enough balanced tasks and cluster/storage capacity exist | Startup, network, shuffle, and monetary cost |
| AQE | Runtime statistics can correct uncertain estimates | Version/config variability; final-plan review |
| Durable intermediate | Expensive recovery/reuse boundary | Storage, governance, compatibility, cleanup |

## Working example

- Source: planned `src/big_data_example/...` PySpark application
- SQL: planned Spark SQL equivalents and quality assertions
- Tests: planned unit, local Spark, integration, fault, and load suites
- Data: planned deterministic, schema-edge, and skew fixtures
- Infrastructure: planned reproducible multi-worker test environment
- Try it: no command yet; no Spark dependency has been selected or installed
- Expected result: exact reconciled metrics, prior generation visible on any pre-publish failure
- Evidence: documentation review only
- Scale represented: none
- Remaining risk: all runtime, compatibility, distributed failure, capacity, security integration, and cost assumptions

## Knowledge check

1. Place five proposed tests on the evidence ladder and state what each cannot prove.
2. Diagnose a run where p50 tasks are fast but one task exceeds the batch window.
3. Design a one-change tuning experiment for a suspected broadcast problem.
4. Specify the IDs and artifacts needed to trace a bad consumer metric back to one task/input generation.
5. Plan a Spark/Python/connector upgrade with canary, backfill, rollback, and reconciliation.
6. Design an executor-loss test that detects duplicate external side effects.
7. Add one bounded fixture and corresponding invariant before viewing a solution.

## Key takeaways

- Evidence must progress from deterministic semantics to real engine, integration, distributed failure, and representative load.
- Tune only after freezing correctness and measuring the dominant boundary.
- Plans plus task distributions and byte metrics explain behavior better than total duration alone.
- Reproducible packaging and effective configuration are part of data correctness.
- Candidate validation and atomic generation publication protect consumers through failure and deployment.

## Resources

- [Spark testing PySpark applications](https://spark.apache.org/docs/4.2.0/api/python/getting_started/testing_pyspark.html) (reviewed 2026-09)
- [Spark web UI](https://spark.apache.org/docs/4.2.0/web-ui.html) (reviewed 2026-09)
- [Spark monitoring and instrumentation](https://spark.apache.org/docs/4.2.0/monitoring.html) (reviewed 2026-09)
- [Spark configuration](https://spark.apache.org/docs/4.2.0/configuration.html) (reviewed 2026-09)
- [Submitting Spark applications](https://spark.apache.org/docs/4.2.0/submitting-applications.html) (reviewed 2026-09)
- [Python package management in PySpark](https://spark.apache.org/docs/4.2.0/api/python/tutorial/python_packaging.html) (reviewed 2026-09)

## Related topics

- [Batch pipeline operations and evolution](../07-batch-processing-and-etl-elt/08-lineage-testing-operating-and-evolving-batch-pipelines.md)
- [Reliability, observability, performance, cost, and operations inventory](../COVERAGE.md#15-reliability-observability-performance-cost-and-operations)

## Completion checklist

- [x] Test layers, fixtures, evidence, tuning, diagnosis, observability, packaging, deployment, backfill, and rollback explained
- [x] Correctness, failure, security, privacy, capacity, cost, compatibility, and publication addressed
- [x] Local, integration, distributed, load, and production evidence distinguished
- [ ] Unit/reference and local Spark evidence run
- [ ] Storage/catalog, multi-worker fault, packaging, load/skew, and rollback evidence run
