# Metrics, Semantic Layers, and Consistent Meaning

> Status: Documentation complete; executable evidence planned  
> Level: Intermediate to Senior  
> Applies to: Analytical SQL / Warehouses / Lakehouses / BI / Data products  
> Data scale: Local fixture; production estimate  
> Example status: Planned  
> Evidence status: None  
> Last reviewed: 2026-09

## Overview

A metric is a versioned decision contract, not merely a SQL expression. It names
the business concept, source fact grain, population, filters, time semantics,
aggregation, dimensions, units, owner, freshness, correction behavior, and
acceptable uses. A semantic layer makes such definitions reusable and governs
valid joins and aggregations across consumers.

This guide covers measures, dimensions, denominators, ratios, cohorts, funnels,
semantic contracts, certification, and versioning. It does not teach a specific
BI or semantic-layer product.

## Learning objectives

- Write a complete metric contract and identify hidden semantic choices.
- Aggregate ratios from components and reason about additive behavior.
- Define cohorts and funnels with explicit identity, eligibility, and time windows.
- Separate semantic ownership from physical computation.
- Migrate metric definitions while preserving reproducibility and consumer trust.

## Prerequisites

- Fact/dimension grain and additivity from guide 03
- Temporal corrections and snapshots from guides 05 and 06
- SQL aggregation, windows, `NULL`, and join cardinality from area 03

## Mental model

```text
certified facts + dimensions
          |
metric contract: population + measure + time + dimensions + version
          |
governed query/aggregate
          |
dashboard | experiment | alert | API
```

A Kotlin function named `conversionRate()` resembles a metric implementation,
but its signature rarely captures dataset versions, late-data policy, permitted
dimensions, or organization-wide ownership. The semantic contract is closer to
a versioned public API plus tests and an SLO; unlike an API call, results can be
recomputed when historical inputs are corrected.

## Terminology

| Term | Meaning in this guide |
| --- | --- |
| Measure | Quantitative component computed at a stated fact grain |
| Metric | Governed calculation and interpretation used for a decision |
| Semantic layer | Reusable model of measures, dimensions, joins, and access policy |
| Denominator | Eligible population against which a ratio is computed |
| Cohort | Entities sharing a precisely defined qualifying condition/time |
| Funnel | Ordered qualifying steps under identity and timing rules |
| Metric version | Immutable identifier for one complete semantic contract |

## Requirements and invariants

The reference `product_conversion_rate_v1` contract states:

- **Purpose:** proportion of viewed product sessions that contain a qualifying purchase.
- **Population/grain:** one tenant-product-session with at least one valid view.
- **Numerator:** eligible rows with a purchase for the same tenant, product, and session.
- **Denominator:** all eligible viewed tenant-product-sessions, including non-converters.
- **Time:** session assigned to UTC date of first valid view; 30-minute inactivity rule.
- **Window:** purchase must occur at or after first view and before session end.
- **Dimensions:** tenant, product-as-of-view, UTC date, approved channel.
- **Exclusions:** bots/test accounts, quarantined events, unsupported schema versions.
- **Correction:** seven-day late window; later corrections publish a new dataset version.
- **Owner:** product analytics business owner plus event-model data owner.
- **Unit:** ratio `[0,1]`; display percentage is presentation only.

Invariants: numerator ≤ denominator, each eligible session contributes once per
product, all joins preserve the population grain, and a metric result pins model,
data, identity, and calendar versions.

## Correct ratio pattern

Generic SQL; session model is a planned prerequisite artifact:

```sql
WITH components AS (
    SELECT
        tenant_key,
        product_key,
        session_date,
        COUNT(*) AS viewed_sessions,
        COUNT(*) FILTER (WHERE purchased) AS purchasing_sessions
    FROM product_session_outcome
    WHERE is_eligible
    GROUP BY tenant_key, product_key, session_date
)
SELECT
    tenant_key,
    product_key,
    session_date,
    purchasing_sessions,
    viewed_sessions,
    purchasing_sessions * 1.0 / NULLIF(viewed_sessions, 0) AS conversion_rate
FROM components;
```

The ratio is computed after summing compatible components. Averaging subgroup
rates weights each subgroup equally rather than each eligible session. The metric
contract must define the zero-denominator result; `NULL` often means undefined
more honestly than zero.

## Cohorts and funnels

A cohort must declare entity identity, qualifying event, event-time zone,
deduplication, re-entry policy, and late correction. “September users” could mean
registered, active, first active, or paying users and yields different denominators.

A funnel must state whether steps are ordered, repeatable, within one session or
duration, attributable to one product/channel, and exclusive. Joining raw step
events pairwise creates combinatorial fan-out. Reduce each entity to qualifying
step timestamps/flags at funnel grain before counting.

## Semantic-layer responsibility

| Semantic layer should govern | It cannot guarantee alone |
| --- | --- |
| Fact grain and allowed joins | Source event completeness |
| Measure aggregation and units | Correct upstream identity resolution |
| Dimension definitions and hierarchies | Warehouse/storage atomicity |
| Default filters and time/calendar logic | User understanding of causal claims |
| Access rules and certified versions | Every ad hoc export follows policy |

Generated SQL must remain inspectable. Validate its result and plan against known
fixtures and realistic cardinalities; abstraction does not remove fan-out,
`NULL`, skew, or engine behavior.

## Data flow, ownership, and trust boundaries

Source owners define emitted events; fact/dimension owners certify model inputs;
business and data owners jointly approve metric meaning; platform owners operate
the semantic engine; consumer owners choose whether the metric is fit for a
decision. A dashboard label is not authoritative documentation.

Semantic queries inherit data classifications. Row/column policies must apply
below or within the semantic boundary so alternate clients cannot bypass them.

## Failure model and recovery

| Failure | Detection | Recovery |
| --- | --- | --- |
| Denominator filter drift | Component reconciliation/version diff | Restore certified contract; publish new version |
| Fan-out after dimension join | Grain uniqueness and count checks | Repair join; recompute affected outputs |
| Average of averages | Golden unequal-size subgroup case | Aggregate numerator/denominator components |
| Late event changes cohort | Completeness/late-age metric | Restate within policy and annotate version |
| Identity merge shifts users | Identity-version lineage | Recompute or freeze per contract; disclose break |
| Semantic service unavailable | Query/API errors and cache age | Serve last certified result within freshness SLO or fail closed |

Recovery needs input reconciliation, golden metric results, consumer/version
inventory, and confirmation that alerts or decisions based on wrong data are handled.

## Security, privacy, and governance

Metrics can leak sensitive facts through small groups, differencing, filters, or
high-cardinality dimensions. Enforce purpose-based access, minimum group sizes or
approved privacy controls, query auditing, export restrictions, and safe caching.
Do not expose raw user identifiers as dimensions. Record classification, owner,
certification, lineage, retention, deprecation, and incident contacts.

## Data quality, testing, and evidence

| Evidence | Expected result | Result |
| --- | --- | --- |
| Hand fixture | Components and final metric match manual calculation | Pending |
| Unequal subgroup mutation | Weighted component ratio differs correctly from average rates | Pending |
| Join fan-out mutation | Duplicate dimension/step fails before publication | Pending |
| Null/zero denominator | Declared undefined behavior is stable | Pending |
| Late/identity correction | Versioned output follows restatement policy | Pending |
| Cross-interface contract | SQL, semantic API, and BI result agree | Pending |

## Common pitfalls

### Pitfall: publishing a metric name and SQL only

The population, time window, exclusions, unit, owner, and corrections remain
ambiguous. Publish the complete contract and golden cases.

### Pitfall: using a dashboard filter as business logic

Filters are easily changed or omitted by another consumer. Govern them in the
metric model when they define eligibility.

### Pitfall: treating semantic consistency as causal correctness

A consistently calculated correlation still does not prove an intervention
caused an outcome. Statistical/experimental validity is a downstream discipline.

## Performance, operations, and migration

Measure base and aggregate rows scanned, cache hit/age, generated-query latency,
concurrency, warehouse time/cost, dimension cardinality, fan-out, freshness,
late corrections, and failure rate. Restrict high-cardinality dimensions and
pre-aggregate only when the aggregate grain can answer the contract exactly.

For a breaking semantic change, create `v2`, compute v1/v2 over the same pinned
inputs, explain and quantify differences, dual-publish, migrate named consumers,
retain historical reproducibility, then deprecate v1. Aliasing v1's name to new
logic silently corrupts comparisons.

## Working example

- SQL/data/tests: planned product-session outcome and conversion metric fixtures
- Expected result: components reconcile and all interfaces return the same version
- Scale represented: none yet; engine plans, concurrency, and cost unverified
- Remaining risk: sessionization, identity correction, privacy leakage, and consumer misuse

## Knowledge check

1. Write the missing clauses in a metric contract for daily active customers.
2. Compute the correct combined rate for unequal subgroup denominators.
3. Diagnose a conversion increase caused by an inner join dropping non-converters.
4. Define a cohort's identity, entry, re-entry, time, and late-data rules.
5. Plan a v1-to-v2 denominator change with consumer comparison and rollback.
6. Add a campaign dimension and identify join and privacy tests required.

## Key takeaways

- A metric is a versioned semantic and operational contract.
- Ratios aggregate through compatible components, not averages of averages.
- Cohort and funnel definitions require identity and time rules.
- Semantic layers centralize meaning but cannot repair bad upstream contracts.
- Breaking meaning changes require parallel versions and consumer migration.

## Resources

- [dbt Semantic Layer documentation](https://docs.getdbt.com/docs/use-dbt-semantic-layer/dbt-sl) (reviewed 2026-09)
- [dbt documentation: Metrics overview](https://docs.getdbt.com/docs/build/metrics-overview) (reviewed 2026-09)

## Related topics

- [Dimensional modeling: facts, dimensions, and stars](03-dimensional-modeling-facts-dimensions-and-stars.md)
- [Data marts, domain products, and model evolution](08-data-marts-domain-products-and-model-evolution.md)

## Completion checklist

- [x] Metric contracts, ratios, cohorts, funnels, and semantic layers explained
- [x] Ownership, privacy, failure, operations, and version migration addressed
- [ ] Metric fixtures, mutations, cross-interface, plans, and cost evidence run
