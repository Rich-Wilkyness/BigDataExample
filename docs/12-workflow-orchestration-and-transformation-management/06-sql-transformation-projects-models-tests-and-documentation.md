# SQL Transformation Projects, Models, Tests, and Documentation

> Status: Documentation complete; executable transformation evidence planned  
> Level: Beginner to Senior  
> Applies to: SQL transformation / dbt-style projects / Warehouses / Analytics engineering  
> Data scale: Local SQL fixture; warehouse production estimate  
> Example status: Planned  
> Evidence status: Documentation and current primary-source review only  
> Last reviewed: 2026-09

## Overview

A SQL transformation project turns warehouse relations into a versioned graph of
models with declared sources, dependencies, materializations, tests, and consumer
documentation. A tool such as dbt can compile and execute that graph, but it
cannot infer the correct grain, business definition, incremental boundary, or
recovery policy. Those remain owned data contracts.

This guide teaches dbt-style mechanisms through durable transformation concepts.
It does not install an adapter or select a warehouse.

## Learning objectives

- Organize staging, intermediate, and mart models around grain and ownership.
- Declare dependencies with source/model references instead of hidden names.
- Select view, table, incremental, ephemeral, or snapshot behavior deliberately.
- Design singular/generic data tests and documentation as release evidence.
- Bound macro abstraction, incremental failure, and semantic change.

## Prerequisites

- SQL relations, `NULL`, joins, aggregates, windows, and plans from Area 03.
- Modeling grain and metric ownership from Area 05.
- Incremental/backfill guarantees from Area 07 and storage publication from Area 11.
- Workflow/task concepts from earlier guides in this area.

## Mental model and terminology

```text
declared sources -> staging models -> intermediate models -> marts/metrics
       |                 |                   |                 |
  freshness/schema   normalization       reusable grain    consumer contract
                         \------ compile graph + tests + docs + artifacts ------/
```

| Term | Meaning in this guide |
| --- | --- |
| Model | Versioned query definition producing a relation or reusable logical node |
| Materialization | Strategy for representing a model in the target engine |
| Source | Named external relation with an explicit producer boundary |
| Test | Query/assertion whose failing rows or result violate a declared contract |
| Snapshot | Transformation-managed history captured from a mutable source |
| Macro | Compile-time reusable logic that generates SQL or configuration |
| Manifest | Machine-readable compiled graph/configuration artifact for one invocation/version |

This resembles a Gradle multi-module build in dependency declaration and generated
artifacts. The analogy stops because SQL nodes operate on mutable shared data,
tests inspect runtime contents, and “incremental” state lives in warehouse tables.

## Requirements, scale assumptions, and invariants

- Every model declares grain, business key, owner, source frontier, and consumers.
- Dependencies use explicit graph references where supported; raw relation names
  are isolated at source boundaries.
- Model SQL is deterministic for a fixed input snapshot, parameters, and engine.
- Incremental and full refresh results are equivalent for the declared history.
- Tests block certification according to severity; warnings never silently certify.
- Documentation states semantic meaning, units, `NULL`, time zone, and freshness.
- Macro output is inspected as compiled SQL and kept within adapter compatibility.
- Estimated input is 3 million events/day and 100 million retained fact rows;
  query plans, runtime, and cost are unmeasured.

## Data flow, ownership, and trust boundaries

| Boundary | Input contract | Authority and owner | Failure behavior | Trust level |
| --- | --- | --- | --- | --- |
| Declared source | Named relation, schema, freshness/frontier | Upstream producer | Test/hold on incompatible or stale source | External trusted-by-contract |
| Staging model | One source, renamed/typed fields | Transformation owner | Reject/quarantine outside model as designed | Controlled normalization |
| Intermediate model | Reusable join/aggregation at stated grain | Domain data owner | Build private/transactional candidate | Derived |
| Mart/metric | Consumer-facing semantic contract | Metric/dataset owner | Tests gate publication | Governed output |
| Project artifacts/docs | Graph, compiled SQL, results, descriptions | Build/release owner | Retain with release; sanitize | Operational metadata |
| Orchestrator | Interval and invocation | Platform owner | Coordinates command, not row semantics | Control plane |

## Project and dependency design

Keep sources, staging, intermediate transformations, and marts visibly distinct.
Folder layout is a navigation aid, not a semantic guarantee; each node still
needs contracts and tests.

```sql
-- models/staging/stg_mobile_events.sql
-- Grain: one accepted logical event per tenant_id,event_id.
select
    tenant_id,
    event_id,
    cast(event_time as timestamp) as event_time,
    nullif(trim(product_id), '') as product_id,
    event_name
from {{ source('landing', 'mobile_events') }}
where event_time >= {{ var('interval_start') }}
  and event_time <  {{ var('interval_end') }}
```

Production code must render typed, adapter-safe literals or bind values where the
execution mechanism supports them. Quoting text from untrusted runtime variables
inside templates can create injection.

```sql
-- models/marts/fct_daily_product_views.sql
{{ config(materialized='incremental', unique_key=['tenant_id','product_id','metric_date']) }}

select tenant_id, product_id, cast(event_time as date) as metric_date,
       count(*) as view_count
from {{ ref('stg_mobile_events') }}
where event_name = 'product_view' and product_id is not null
{% if is_incremental() %}
  and event_time >= {{ var('recompute_start') }}
{% endif %}
group by tenant_id, product_id, cast(event_time as date)
```

The incremental predicate deliberately recomputes affected intervals rather than
only `event_time > max(target)`, which can miss late records. Exact merge/upsert
semantics, composite-key support, transactions, and atomic replacement depend on
the pinned adapter and warehouse.

## Materialization decision table

| Need | Candidate | Guarantee/tradeoff | Reconsider when |
| --- | --- | --- | --- |
| Thin rename/cast layer | View | Little storage; query cost repeats | Deep view stacks hurt consumers |
| Stable reused dataset | Table | Predictable reads; rebuild cost | Data is too large for full refresh |
| Large changing fact | Incremental | Bounded work; stateful correctness burden | Full/incremental equivalence cannot be proven |
| Reusable compile-only logic | Ephemeral/CTE | No standalone object | SQL becomes huge or needs observation |
| Source history | Snapshot | Captures detected changes | Source has a better authoritative change log |
| Engine-maintained refresh | Materialized view | Engine may manage updates | Semantics/portability/control are insufficient |

## Tests, snapshots, macros, and documentation

Generic tests express reusable properties such as non-nullness, uniqueness,
accepted values, or relationships. Singular tests express domain queries such as
reconciliation or impossible temporal states. Passing basic tests does not prove
accuracy or completeness.

```yaml
models:
  - name: fct_daily_product_views
    description: "Certified UTC daily product-view counts."
    columns:
      - name: tenant_id
        data_tests: [not_null]
      - name: view_count
        data_tests: [not_null]
```

Add a grain uniqueness test over the composite key and a source-to-output
reconciliation query. Syntax varies by project/runtime version and package.

Snapshots are derived history: define unique key, change-detection strategy,
timestamp/time-zone behavior, hard-delete handling, and late correction. Prefer
an authoritative CDC log when it exists. Macros should remove mechanical
repetition, not hide grain, joins, filters, or engine cost. Test dispatched macro
variants and review compiled SQL.

Documentation includes owner, grain, semantic definition, exclusions, units,
freshness, source frontier, sensitivity, retention, examples, and downstream
exposures. Generated docs reflect declarations; review is still required.

## Lifecycle, consistency, identity, and time

Model identity, database relation identity, run invocation, code revision,
compiled artifact, and dataset publication are separate. A successful command
can leave some models from a new invocation and others from an older one unless
the chosen build/publication boundary prevents mixed visibility. Certified marts
therefore record a publication ID and tested upstream versions.

## Failure model and recovery

| Failure | Detection/containment | Recovery and convergence |
| --- | --- | --- |
| Join fans out grain | Uniqueness/reconciliation test | Fix source gate/join; rebuild affected history |
| Incremental predicate misses late rows | Full-versus-incremental differential | Expand correction window and replace partitions |
| Command partially builds graph | Invocation artifacts and publication gate | Keep prior certified version; resume/rebuild candidates |
| Macro compiles unsafe/wrong SQL | Compile/static review and fixture | Fix macro; test every adapter branch |
| Snapshot key not unique | Source uniqueness/history overlap tests | Repair key/history and perform versioned rebuild |
| Schema changes mid-run | Contract/adapter failure | Use expand/migrate/contract and fixed input snapshot |
| Test warns but certification proceeds | Policy review detects ungated warning | Define severity and explicit required receipts |
| Warehouse query cancelled/unknown | Query ID plus target/catalog inspection | Reconcile actual relation before retry |

## Security, privacy, and governance

Use separate development schemas and least-privilege service identities. Never
commit profiles, credentials, rendered secrets, or production samples. Restrict
macro/package provenance because compile-time code can affect queries. Propagate
classification, masking, row/column policy, retention, and erasure through
derived models and snapshots; snapshots can retain deleted sensitive history.

## Data quality, testing, and evidence

| Evidence | Dataset and environment | Procedure | Expected result | Result |
| --- | --- | --- | --- | --- |
| Compile/parse | Project / pinned dbt runtime | Parse and compile all nodes | Stable graph; no unsafe unresolved refs | Pending |
| SQL fixture | Mobile events / local or test warehouse | Build selected staging and mart models | Expected grain and values | Pending |
| Incremental differential | Late/duplicate updates / real adapter | Compare incremental to clean full rebuild | Equivalent declared result | Pending |
| Failure/publication | Test warehouse | Fail middle model/test | Prior certified publication remains complete | Pending |
| Plan/load/cost | Production-shaped data / warehouse | Explain and concurrency sweep | Meets window and cost budget | Pending |

SQLite or a local SQL double cannot prove adapter SQL, warehouse transactions,
incremental merge, permissions, concurrency, or production query plans.

## Debugging guide

1. Capture invocation, model unique ID, compiled SQL, adapter/runtime, target, query ID, and publication.
2. Confirm grain and source frontier before reading orchestrator state.
3. Inspect graph parents/children, failing rows, row counts, checksums, and query plan.
4. Compare development and deployed compilation inputs, macros, packages, and variables.
5. Retain the prior certified relation; isolate candidates and stop downstream refresh.
6. Rebuild the minimum affected closure, reconcile with a full reference, then certify.

## Common pitfalls

### Pitfall: `ref` makes the data correct

It declares graph dependency and naming, not grain, freshness, or completeness.
Add source and model contracts plus reconciliation.

### Pitfall: incremental means append new timestamps

Late changes, deletes, and key updates are missed. Define change identity and a
bounded recomputation/merge strategy, then compare with a full rebuild.

### Pitfall: abstract all SQL into macros

Generated SQL becomes hard to reason about and tune. Keep business relations
visible and inspect compilation.

## Performance, capacity, and cost

Measure selected nodes, compiled SQL size, relation count, bytes scanned/written,
warehouse slots, spill, model critical path, test cost, incremental window,
snapshot growth, and concurrency. Selection can reduce work only when the saved
state/artifact and upstream data assumptions are valid.

## Compatibility, migration, backfill, and delivery

Pin runtime, adapter, packages, Python, and warehouse. For a breaking model
change, add new fields/relations, dual-build representative intervals, run old
and new consumer tests, backfill private targets, atomically redirect consumers,
observe, and contract only after rollback retention. Never reuse an old manifest
with incompatible project or schema state without validation.

## Working example

- Transformation project: Planned under `sql/transformation/`
- Fixtures: Planned under `data/fixtures/`
- Tests: Planned SQL/unit, incremental differential, and publication tests
- Orchestration: Planned one-interval invocation from the area DAG
- Try it: Planned pinned compile/build/test/document commands
- Expected result: Correct composite grain and identical full/incremental outputs
- Evidence: Planned manifest, compiled SQL, run results, plans, and reconciliation
- Scale represented: Documentation and production estimate only
- Remaining risk: All dbt, adapter, warehouse, performance, and failure behavior unverified

## Knowledge check

1. Explain what a model dependency guarantees and what it does not.
2. Predict the late-event result of the naive `> max(event_time)` incremental filter.
3. Diagnose a passing non-null suite with doubled revenue.
4. Design full-versus-incremental differential evidence.
5. Choose materializations for staging casts, reused facts, and a large late-changing fact.
6. Plan a compatible metric-definition rollout and backfill.
7. Add composite-grain and reconciliation tests to the planned project.

## Key takeaways

- Transformation tools manage a graph; contracts define data meaning.
- Materialization choice changes freshness, cost, state, and recovery.
- Incremental correctness must equal a declared full-rebuild reference.
- Tests and docs become release evidence only when publication policy requires them.
- Compiled SQL and artifacts are essential diagnostic and delivery inputs.

## Resources

- [dbt: projects](https://docs.getdbt.com/docs/build/projects) (reviewed 2026-09)
- [dbt: models](https://docs.getdbt.com/docs/build/models) (reviewed 2026-09)
- [dbt: materializations](https://docs.getdbt.com/docs/build/materializations) (reviewed 2026-09)
- [dbt: data tests](https://docs.getdbt.com/docs/build/data-tests) (reviewed 2026-09)
- [dbt: snapshots](https://docs.getdbt.com/docs/build/snapshots) (reviewed 2026-09)
- [dbt: Jinja and macros](https://docs.getdbt.com/docs/build/jinja-macros) (reviewed 2026-09)

## Related topics

- [Metadata, lineage, and artifacts](07-metadata-lineage-artifacts-and-data-aware-scheduling.md)
- [Area 05 models and semantics](../05-data-modeling-and-business-semantics/README.md)
- [Area 07 batch processing](../07-batch-processing-and-etl-elt/README.md)

## Completion checklist

- [x] Project, model, source, materialization, test, snapshot, macro, and docs contracts defined
- [x] SQL examples state grain, interval, `NULL`, and adapter limitations
- [x] Incremental, partial-build, semantic, security, and recovery failures addressed
- [x] Evidence, performance, compatibility, backfill, and cutover covered
- [x] Working example and all executable evidence accurately marked Planned
- [ ] Pinned project, adapter, warehouse, fault, differential, plan, and load evidence executed

