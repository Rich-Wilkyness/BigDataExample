# Slowly Changing Dimensions and Bitemporal History

> Status: Documentation complete; executable evidence planned  
> Level: Intermediate to Senior  
> Applies to: Warehouses / Lakehouses / Temporal modeling / Audit  
> Data scale: Local fixture; production estimate  
> Example status: Planned  
> Evidence status: None  
> Last reviewed: 2026-09

## Overview

Historical modeling answers two separate questions: when was a fact true in the
business world, and when did the data system know or record it? Slowly changing
dimension (SCD) patterns choose how descriptive changes appear to analytics;
bitemporal models retain both valid time and system/knowledge time so corrections
do not erase what earlier reports knew.

This guide covers SCD types, half-open validity intervals, late changes,
corrections, temporal joins, audit/reproducibility, and retention. It is not a
vendor-specific temporal-table tutorial.

## Learning objectives

- Distinguish event time, valid time, ingestion time, and system/knowledge time.
- Choose SCD behavior per attribute and consumer question.
- Enforce non-overlapping histories and deterministic as-of joins.
- Model a retroactive correction without destroying prior knowledge.
- Plan history backfills, compaction, deletion, and reproducibility evidence.

## Prerequisites

- Dimensional facts and dimensions from guide 03
- Business/surrogate identity and late binding from guide 04
- SQL ranges, joins, windows, constraints, and transactions from area 03

## Mental model

```text
valid time:   when the business statement applies
system time:  when this analytical system recorded that statement

                     system timeline ->
valid timeline  old belief | corrected belief
       down      historical | retroactive row
```

A Room migration history says when app schema changed, not when a user's address
was valid. Likewise, `updated_at` alone cannot answer both temporal questions.
The analogy to versioned state stops once queries need two independent time axes,
late source facts, and reproducible dataset snapshots.

## Terminology

| Term | Meaning in this guide |
| --- | --- |
| Valid time | Interval when a statement is considered true in the modeled domain |
| System time | Interval when a version is current in this data system |
| As-of query | Query evaluated at a specified point on one or both time axes |
| SCD type 1 | Overwrite attribute; prior analytical value is not retained there |
| SCD type 2 | New dimension row/version with valid interval and new surrogate |
| SCD type 3 | Limited previous value stored beside current value |
| Bitemporal | Retains valid-time and system-time histories independently |

## Requirements and invariants

- Time domains use explicit instants/calendar semantics and UTC normalization;
  business dates retain their named time zone and close rule.
- Valid intervals use `[valid_from, valid_to)` so adjacent versions have one owner
  at the boundary; infinity/current representation is consistent.
- For an entity and system version, applicable valid intervals never overlap.
- System history is append/version based; correcting valid time does not overwrite
  evidence of what prior publications knew.
- Every fact-to-dimension temporal join yields exactly one governed result.
- The model declares whether reports restate after corrections or remain frozen.

## Choosing SCD behavior

| Need | Pattern | Preserved answer | Main cost/risk |
| --- | --- | --- | --- |
| Fix typo with no analytical significance | Type 1 | Current corrected value | Prior labels not reproducible from table alone |
| Group facts by attribute valid then | Type 2 | Historical context | More rows and temporal join discipline |
| Compare current and immediately previous assignment | Type 3 | Limited transition | Cannot represent arbitrary history |
| Separate current table and history archive | Type 4 | Current plus history | Consumer must choose/join correct table |
| Mix type 1/2/3 attributes | Sometimes called type 6 | Several views | Complex semantics; document each attribute |
| Reproduce prior belief after retroactive correction | Bitemporal | Valid truth and knowledge history | Storage/query/operational complexity |

SCD type is an attribute-level policy, not automatically one choice for every
column. Sensitive attributes may require deletion/tokenization even if other
history is retained.

## Type-2 temporal join

Generic SQL; half-open intervals and current-row sentinel must match the actual
engine. This sketch is unexecuted:

```sql
SELECT f.event_id, f.event_time, p.product_key, p.category_name
FROM fact_product_event AS f
JOIN dim_product AS p
  ON p.tenant_id = f.tenant_id
 AND p.product_entity_id = f.product_entity_id
 AND f.event_time >= p.valid_from
 AND f.event_time < p.valid_to;
```

Before aggregation, assert each fact has exactly one match. An overlap duplicates
facts; a gap drops facts under an inner join. A broad sentinel such as
`9999-12-31` must be representable consistently by database, DataFrame engine,
serializer, and JVM/Python clients; otherwise use nullable end with explicit
predicates or a supported infinity representation.

## Bitemporal correction walkthrough

On September 5 the system learns that product P moved category A → B effective
September 1. On September 7 it learns the effective date was actually August 29.

1. The first load records a B valid interval beginning September 1 with a system
   interval beginning September 5.
2. The correction closes those system versions on September 7 without deleting them.
3. New system versions represent B beginning August 29 and adjust A's valid end.
4. “As valid on August 30, using knowledge available September 6” returns A.
5. The same valid date using knowledge available September 8 returns B.

A plain type-2 overwrite of interval endpoints can answer the newest belief but
cannot reproduce step 4.

## Data flow, ownership, and trust boundaries

Source systems own business-effective claims where their contract supplies them.
Ingestion records arrival; the dimension owner defines history and correction
policy; the catalog/snapshot records publication knowledge time. Consumers name
both the requested valid time and dataset/system version for reproducibility.

Source `updated_at` is untrusted as valid time unless explicitly guaranteed. A
file modification time or pipeline run time is not a substitute for either axis.

## Failure model and recovery

| Failure | Detection | Recovery |
| --- | --- | --- |
| Overlapping valid intervals | Temporal uniqueness/overlap assertion | Reject publish; recompute entity timeline |
| Gap creates unmatched facts | As-of join match buckets | Route to governed unknown or repair source/history |
| Late change | Source effective time precedes arrival | Insert new version; rebuild affected facts/metrics |
| Retroactive correction overwritten | Prior-snapshot replay differs | Restore system history; republish corrected timeline |
| Boundary/time-zone error | Golden instant at DST/month boundary | Normalize time rule and rebuild affected range |
| Partial multi-row change | Transaction/snapshot consistency failure | Retain prior snapshot; retry atomic history update |

Recovery convergence requires no overlaps, declared gap behavior, one match per
fact, and reconciliation of both current and previous certified as-of results.

## Security, privacy, and governance

History multiplies sensitive data and may conflict with erasure/minimization.
Classify each historical attribute, set purpose and retention, restrict temporal
queries, audit corrections, and propagate deletion/tokenization through closed
versions, backups, facts, and exports under the governing policy. Bitemporal
auditability is not permission for indefinite personal-data retention.

## Data quality, testing, and evidence

| Evidence | Expected result | Result |
| --- | --- | --- |
| Boundary fixture | Exact `valid_to` instant selects next interval only | Pending |
| Overlap/gap mutations | Overlap fails; gap follows declared unknown policy | Pending |
| Late-arrival replay | Affected facts re-key without count drift | Pending |
| Bitemporal correction | Old and new knowledge-time queries return expected values | Pending |
| Time-zone cases | UTC instants and business dates remain correct across DST | Pending |
| Snapshot reproducibility | Pinned model/data version reproduces certified output | Pending |

## Common pitfalls

### Pitfall: calling an `is_current` table historical

It may retain rows but cannot establish valid ranges, prevent overlap, or reproduce
prior knowledge. Store explicit intervals and version lineage.

### Pitfall: using processing time as business-valid time

Late arrival then shifts history forward and attributes old facts to the wrong
context. Preserve all relevant clocks and choose deliberately.

### Pitfall: updating type-2 endpoints to apply a correction

That destroys the old system belief. If reproducibility matters, close system
versions and append corrected ones.

## Performance, operations, and migration

Measure versions/entity distribution, interval overlap/gap counts, unknown and
late-change rates, affected-fact fan-out, temporal-join plans, partition pruning,
compaction, storage growth, and correction latency. Skewed entities with thousands
of versions need explicit bounds and investigation.

Migrate from current-only to history by capturing a consistent baseline, defining
an initial valid/system interval and its limitations, starting change capture,
validating no gaps between baseline and changes, backfilling facts, dual-querying
critical reports, and cutting over by dataset version. Pre-baseline history remains
unknown unless authoritative evidence exists.

## Working example

- SQL/data/tests: planned product category type-2 and bitemporal correction fixture
- Expected result: deterministic boundary/as-of answers and preserved prior belief
- Scale represented: none yet; temporal plans and correction fan-out unverified
- Remaining risk: source effective-time quality, engine range behavior, and retention

## Knowledge check

1. Distinguish event, valid, ingestion, and system time in the correction example.
2. Predict the match for a fact exactly at `valid_to`.
3. Diagnose duplicate revenue caused by overlapping product versions.
4. Model the September 7 correction without erasing September 6 knowledge.
5. Choose SCD policies for product name, regulated classification, and category.
6. Plan migration from current-only product state with honest history limitations.

## Key takeaways

- Valid time and system/knowledge time answer different questions.
- Half-open, non-overlapping intervals make boundary joins deterministic.
- Type 2 preserves valid history; bitemporal history also preserves prior belief.
- Late changes and corrections require bounded rebuild and reconciliation.
- Historical value must be balanced with privacy, storage, and query complexity.

## Resources

- [Kulkarni and Michels: Temporal Features in SQL:2011](https://sigmodrecord.org/2012/09/30/temporal-features-in-sql2011/) (reviewed 2026-09)
- [PostgreSQL documentation: Range Types](https://www.postgresql.org/docs/current/rangetypes.html) (reviewed 2026-09)

## Related topics

- [Business keys, surrogate keys, and identity resolution](04-business-keys-surrogate-keys-and-identity-resolution.md)
- [Snapshots, events, and state reconstruction](06-snapshots-events-and-state-reconstruction.md)

## Completion checklist

- [x] SCD patterns, temporal axes, intervals, corrections, and joins explained
- [x] Reproducibility, failure, privacy, performance, and migration addressed
- [ ] Temporal DDL, fixtures, correction, time-zone, plan, and replay evidence run
