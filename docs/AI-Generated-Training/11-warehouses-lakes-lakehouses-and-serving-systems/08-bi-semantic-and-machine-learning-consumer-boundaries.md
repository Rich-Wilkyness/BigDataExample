# BI, Semantic, and Machine-Learning Consumer Boundaries

> Status: Documentation complete; executable evidence planned  
> Level: Intermediate to Senior  
> Applies to: BI / Semantic layer / Machine learning / Serving / Governance  
> Data scale: Local contract design; distributed and production estimates  
> Example status: Planned  
> Evidence status: None  
> Last reviewed: 2026-09

## Overview

Consumer boundaries turn governed data into decisions and application behavior.
BI dashboards need stable metrics and reproducible extracts; semantic layers need
owned definitions and compatible dimensions; machine-learning pipelines need
point-in-time-correct features and matching training/serving transformations.

Data engineering owns reliable data contracts and delivery, not the correctness
of every visualization, business decision, statistical model, or application.
That ownership boundary must still include joint acceptance, incident routing,
and change coordination.

## Learning objectives

- Define a metric contract with grain, population, time, owner, and version.
- Distinguish live queries, extracts, semantic models, and feature datasets.
- Prevent fan-out, mixed freshness, look-ahead leakage, and training/serving skew.
- Establish producer/consumer responsibilities, deprecation, and reconciliation.
- Design end-to-end evidence from source frontier to a representative consumer.

## Prerequisites

- [Facts, dimensions, and stars](../05-data-modeling-and-business-semantics/03-dimensional-modeling-facts-dimensions-and-stars.md)
- [Metrics, semantic layers, and consistent meaning](../05-data-modeling-and-business-semantics/07-metrics-semantic-layers-and-consistent-meaning.md)
- [Serving layers, materialized views, caches, and federation](07-serving-layers-materialized-views-caches-and-federation.md)

## Mental model and terminology

```text
governed facts/dimensions + publication/frontier
                  |
          semantic definition v4
           /             |              \
          v              v               v
 dashboard query     certified extract   feature computation
 publication P12     snapshot S42         as-of event time T
          |              |               |
       analyst       downstream tool   training + online serving
```

A semantic metric resembles a shared Kotlin function with a versioned signature:
callers should not reimplement it inconsistently. The analogy stops because the
metric depends on mutable historical datasets, late corrections, access policy,
calendar rules, and aggregation across many records and engines.

| Term | Meaning in this guide |
| --- | --- |
| Metric contract | Owned definition of population, grain, measure, filters, time, dimensions, nulls, and version |
| Semantic layer | Governed model exposing reusable metrics, entities, joins, dimensions, and access policy |
| Extract | Materialized bounded dataset delivered to a consumer/tool |
| Feature | Model input with entity, event/as-of time, availability time, transformation, and version |
| Point-in-time correctness | Feature computation uses only information available at the prediction time |
| Training/serving skew | Training and online inference compute or source materially different feature values |
| Consumer contract | Producer and consumer obligations for schema, semantics, SLO, access, change, and support |

## Requirements, scale assumptions, and invariants

Assume 20 BI readers, daily executive certification at 02:00 UTC, operational
metrics within 15 minutes, 100K products, tenant isolation, weekly model training,
and online feature lookup at 200 ms p95. Treat these as hypotheses.

- Every metric has one definition owner, grain, population, time zone/calendar, null policy, and semantic version.
- Joins declare cardinality and preserve or intentionally change grain.
- One report/extract/model run records compatible dataset publications and definitions.
- Extracts are immutable, checksummed, access-controlled, expiring deliverables.
- Offline feature values are computed as of prediction time without future leakage.
- Online and offline features share transformation semantics or are differentially tested.
- Breaking consumer changes use notice, compatibility, migration, and observed adoption.

## Data flow, ownership, and trust boundaries

| Boundary | Producer obligation | Consumer obligation | Failure behavior |
| --- | --- | --- | --- |
| Governed dataset | Grain, schema, snapshot/frontier, quality, access | Use supported keys/versions | Hold prior certified publication |
| Semantic metric | Definition/version, valid dimensions, reconciliation | Do not silently redefine | Fail or label uncertified result |
| BI query/dashboard | Stable parameters and publication context | Own visual interpretation and use | Display freshness/error state |
| Extract/export | Manifest, checksum, schema, expiry, delivery status | Secure, validate, delete on schedule | Retry by delivery ID; no partial consume |
| Offline feature set | Entity/as-of grain and lineage | Pin training dataset/code | Reject leakage/duplicate entity-time |
| Online feature service | Lookup key, value/version, freshness | Define fallback and prediction impact | Fail/degrade per model contract |

## Metric and semantic contracts

```yaml
metric: product_purchase_rate
version: 4
grain: [tenant_id, product_id, utc_date]
population: accepted product_view and purchase events
numerator: distinct purchase event identities
denominator: distinct product_view event identities
zero_denominator: null
event_time: occurred_at UTC, half-open day
dimensions: product as known at event time
owner: product-analytics
freshness: 15m operational; certified daily at 02:00 UTC
```

```sql
-- Generic semantic check at one pinned publication.
SELECT tenant_id, product_id, utc_date,
       COUNT(DISTINCT CASE WHEN event_type = 'purchase' THEN event_id END)
       / NULLIF(COUNT(DISTINCT CASE WHEN event_type = 'product_view' THEN event_id END), 0)
         AS purchase_rate
FROM semantic_product_event
GROUP BY tenant_id, product_id, utc_date;
```

Integer division and `NULL` behavior vary by dialect; cast deliberately and test.
The dimension join must be as-of event time if historical product attributes are
part of the definition. Current-state joins can rewrite historical metrics.

### Dashboard and extract contracts

A dashboard reports dataset publication, metric version, filter/time zone, refresh
time, completeness, and degraded state. Multiple queries should share a pinned
publication token when cross-widget consistency matters.

An extract has `delivery_id`, consumer, purpose, source publications, semantic
versions, schema, row count, checksum, classification, created/expiry time, and
acknowledgement. Write privately, validate, publish atomically, and retry by stable
identity. Email attachments and manually named files are not governed delivery.

## Feature boundaries and point-in-time joins

For an example at prediction time `t`, use the most recent feature whose event
time and availability time satisfy the contract at `t`. Event time alone is not
enough: a value calculated tomorrow from late data was unavailable today.

```sql
-- ANSI-style point-in-time sketch; QUALIFY syntax varies.
SELECT label.entity_id, label.prediction_time, feature.feature_value
FROM training_labels AS label
LEFT JOIN feature_history AS feature
  ON feature.entity_id = label.entity_id
 AND feature.event_time <= label.prediction_time
 AND feature.available_at <= label.prediction_time
QUALIFY ROW_NUMBER() OVER (
  PARTITION BY label.entity_id, label.prediction_time, feature.feature_name
  ORDER BY feature.event_time DESC, feature.available_at DESC, feature.version DESC
) = 1;
```

Define deterministic ties and missing-feature/default policy. The feature store or
model platform does not automatically prevent leakage or semantic skew.

## Consumer ownership limits

| Concern | Primary owner | Joint contract |
| --- | --- | --- |
| Source completeness and publication | Dataset owner | Consumer acceptance and incident notification |
| Metric definition | Business/domain metric owner | Data implementation and reconciliation |
| Dashboard visual/decision use | BI/product owner | Version/freshness display and query review |
| Feature transformation/data | Feature/data owner | Model owner validates predictive use |
| Model quality/fairness | ML/model owner | Data lineage, drift, privacy, deletion inputs |
| Serving fallback | Application/model owner | Data service SLO and version reporting |

Ownership is not a handoff that ends collaboration. The producer must know material
consumers; consumers must not build undeclared dependencies on internal tables.

## Lifecycle, consistency, identity, and time

Definitions move through proposal, review, version, shadow, certification,
adoption, deprecation, and retirement. A report or model run pins dataset,
semantic, code, and policy versions. Distinguish event, availability, processing,
publication, query, extract, prediction, and label times. Record identity at every
boundary so duplicate reports, extract deliveries, entity features, and predictions
can be reconciled.

## Failure model and recovery

| Failure | Detection | Containment and recovery |
| --- | --- | --- |
| Join fan-out inflates metric | Grain/cardinality gates and reconciliation | Block certification; fix dimension contract and recompute |
| Dashboard mixes publications | Query metadata/publication token | Pin compatible version; mark prior result stale |
| Partial/stale extract | Manifest/checksum/ack and expiry | Keep invisible; retry same delivery ID |
| Breaking metric change | Version/adoption telemetry and differential test | Run both versions; migrate or restore route |
| Look-ahead leakage | Availability-time and temporal mutation tests | Rebuild features/training; invalidate evaluation |
| Training/serving skew | Offline-online sampled comparison | Stop rollout/fallback; align transformation and backfill |
| Consumer overload | Workload/query attribution | Throttle/isolate; preserve certified publication |

Recovery includes corrected publications/features, downstream impact inventory,
consumer acknowledgement, reconciliation, and reissued decisions/models where
required—not only repaired source rows.

## Security, privacy, and governance

Semantic layers, BI tools, extracts, notebooks, feature stores, training sets,
model artifacts, and online caches are separate access and deletion boundaries.
Enforce tenant/row/column purpose policy, minimize features, protect credentials,
expire extracts, audit downloads/shares, and use safe logs/samples. Derived features
can be sensitive even when source fields are individually harmless. A deletion
workflow must decide whether retraining or model-artifact action is required.

## Data quality, testing, and evidence

| Evidence | Dataset/environment | Expected result | Result |
| --- | --- | --- | --- |
| Metric | Hand fixture, null/zero/fan-out/time cases | Exact versioned values and grain | Pending |
| Dashboard | Multi-query publication/freshness cases | Consistent version or explicit disclosure | Pending |
| Extract | Crash/retry/checksum/expiry fixture | One complete acknowledged delivery | Pending |
| Feature | Point-in-time and late-availability mutations | No future information; deterministic ties | Pending |
| Online/offline | Sampled differential and fault cases | Values within declared tolerance and fallback | Pending |
| Consumer E2E | Representative BI/API/model workflow | Contract, SLO, policy, lineage, recovery pass | Pending |

SQL fixtures do not prove BI-tool caching, extract delivery, online-store latency,
model behavior, access enforcement, or production consumer adoption.

## Debugging guide

Begin with affected consumer and decision, then capture request/report/model/run,
tenant, dataset publication/frontier, metric/feature version, query ID, filters,
time zone, extract delivery, entity/prediction time, and policy version. Trace
lineage to source dispositions. Check join cardinality, cache/extract age, temporal
availability, offline-online differences, workload queues, and recent definition
or dashboard/model releases. Communicate known impact and version boundaries.

## Common pitfalls

### Pitfall: metric defined only by a SQL expression

SQL omits owner, grain, population, calendar, availability, correction, and
compatibility. Treat the definition as a versioned consumer contract.

### Pitfall: dashboard refresh time equals data freshness

A new query can read an old or incomplete publication. Show source frontier and
certification state, not only UI refresh time.

### Pitfall: same feature code guarantees parity

Different data availability, window state, defaults, precision, and update order
can create skew even with shared source code. Compare actual keyed values.

## Performance, capacity, and cost

Measure query/refresh/extract/feature latency percentiles, concurrency, scan/result
bytes, cache behavior, extract size and delivery rate, feature key cardinality,
online QPS/tail latency, training scan/shuffle, consumer attribution, and cost per
decision/use case. Limit dashboard fan-out and refresh storms. Reserve rebuild and
correction capacity while current consumers continue.

## Compatibility, migration, backfill, and delivery

Classify additive versus semantic-breaking changes. Version definitions and
datasets, run old/new concurrently, backfill pinned history, differential-test by
key and segment, canary dashboards/models, measure adoption, communicate deadlines,
and remove only after consumers have migrated. Rollback needs retained inputs,
previous routes/artifacts, and compatible caches/extracts; corrected data may
require forward repair instead.

## Working example

- SQL/contracts: planned purchase-rate metric, extract manifest, and point-in-time feature query
- Tests/data: planned fan-out, mixed publication, leakage, parity, fault, and access fixtures
- Infrastructure: no BI, semantic, feature, or model-serving product selected
- Try it: no command yet
- Evidence: documentation review only
- Remaining risk: actual tool semantics, consumer adoption, online/offline parity, load, security, and recovery

## Knowledge check

1. Write a complete contract for purchase rate beyond its SQL formula.
2. Diagnose a dashboard whose widgets disagree despite recent refresh times.
3. Find look-ahead leakage in a feature with event time but no availability time.
4. Assign producer, metric, dashboard, feature, model, and application ownership.
5. Design an extract protocol that survives a lost acknowledgement.
6. Plan a breaking metric migration and identify rollback versus forward-repair limits.
7. Implement and verify one new dimension without changing metric grain.

## Key takeaways

- Consumer boundaries require versions, freshness, ownership, policy, and recovery—not just data access.
- Metrics are governed semantic contracts; dashboards must disclose publication context.
- Point-in-time correctness and offline-online comparison prevent feature leakage and skew.
- End-to-end evidence ends at a representative consumer, not at a successful table write.

## Resources

- [dbt Semantic Layer documentation](https://docs.getdbt.com/docs/use-dbt-semantic-layer/dbt-sl) (reviewed 2026-09; product example)
- [Feast point-in-time joins](https://docs.feast.dev/getting-started/concepts/point-in-time-joins) (reviewed 2026-09; product example)
- [Google Rules of Machine Learning](https://developers.google.com/machine-learning/guides/rules-of-ml) (reviewed 2026-09)

## Related topics

- [Metrics, semantic layers, and consistent meaning](../05-data-modeling-and-business-semantics/07-metrics-semantic-layers-and-consistent-meaning.md)
- [Serving layers, materialized views, caches, and federation](07-serving-layers-materialized-views-caches-and-federation.md)

## Completion checklist

- [x] BI, semantic, extract, feature, ML, ownership, and consumer contracts explained
- [x] Grain, time, identity, failure, security, capacity, migration, and evidence addressed
- [ ] Metric, dashboard, extract, point-in-time, parity, end-to-end, and consumer evidence run
