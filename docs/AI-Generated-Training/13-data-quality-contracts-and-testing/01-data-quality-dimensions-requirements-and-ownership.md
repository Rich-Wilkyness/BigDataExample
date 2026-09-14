# Data Quality Dimensions, Requirements, and Ownership

> Status: Documentation complete; executable quality evidence planned  
> Level: Beginner to Senior  
> Applies to: Generic data engineering / Batch / Streaming / Analytical datasets  
> Data scale: Local fixture; production estimate  
> Example status: Planned  
> Evidence status: Documentation and primary-source review only  
> Last reviewed: 2026-09

## Overview

Data quality is fitness for a declared consumer purpose. Dimensions such as
validity, completeness, uniqueness, consistency, accuracy, and timeliness are
question prompts; they become requirements only after a grain, scope,
measurement, threshold, owner, and response are specified. “The table is 99%
accurate” is not actionable without saying what was compared with which
authority, over which rows and time, and what the remaining 1% can harm.

This guide defines durable quality requirements. It does not choose a testing
framework or treat every anomaly as an incident.

## Learning objectives

- Distinguish quality dimensions and fitness from a generic quality score.
- Translate consumer decisions and harms into measurable rules.
- Define grain, denominator, threshold, window, segment, and exception policy.
- Assign producer, dataset, platform, and consumer responsibilities.
- Diagnose conflicts among correctness, availability, freshness, and cost.

## Prerequisites

- Area 01 requirements, boundaries, guarantees, and scale estimates.
- Area 05 grain, business keys, facts, dimensions, and metrics.
- The [area scenario and evidence ladder](README.md).

## Mental model and terminology

```text
consumer decision -> possible harm -> required property -> measurement
       -> threshold/window -> enforcement -> response owner -> evidence
```

| Term | Meaning in this guide |
| --- | --- |
| Validity | A value or record conforms to its declared syntactic or semantic domain |
| Completeness | All required fields, records, intervals, or source contributions are present relative to a stated frontier |
| Uniqueness | No two records represent the same declared identity within the stated scope |
| Consistency | Representations that should agree do agree under named rules and timing |
| Accuracy | A value agrees sufficiently with an independent real-world authority or observation |
| Timeliness | Data becomes usable within a declared delay from the relevant event or readiness time |
| Fitness | The dataset supports a particular use with acceptable risk; fitness is consumer-specific |
| Quality rule | Versioned predicate or measurement plus scope, threshold, severity, owner, and response |

A Kotlin non-null property resembles a structural validity requirement. It does
not establish that a non-empty `productId` exists in the catalog, that all events
arrived, or that the timestamp describes reality. Dataset properties span rows,
systems, and history beyond one object.

## Requirements, scale assumptions, and invariants

For the daily product-view metric:

- Grain is one row per tenant, product, metric version, and UTC date.
- Every certified publication names its raw input frontier and rule-suite version.
- Required tenant/event identity is 100% valid among accepted records; records
  failing identity rules are rejected, never silently coerced.
- Validated logical event identity is unique; exact delivery duplicates do not
  increase metrics, while conflicting duplicates require domain resolution.
- Source completeness is at least 99.9% by the 02:00 UTC certification deadline,
  measured against producer control counts per tenant and UTC date.
- Timeliness is measured from source readiness, not merely job start.
- Product-view totals reconcile after declared exclusions; unexplained variance
  blocks certification.
- Accuracy is not claimed unless compared with an independent authority such as
  a controlled producer counter or audited business transaction.
- Estimates use 3 million events/day and 35% hot-tenant skew; all rates and
  thresholds are hypotheses pending baseline and consumer review.
- Non-goals are perfect detection, one score for every use, and automatic repair
  of semantically ambiguous records.

Evidence that should change these requirements includes observed producer retry
rates, normal late-arrival curves, consumer loss tolerance, source control
reliability, false-positive rate, incident history, and measurement cost.

## Data flow, ownership, and trust boundaries

| Boundary | Requirement and authority | Owner | Failure behavior | Trust level |
| --- | --- | --- | --- | --- |
| Mobile producer | Event meaning and stable event ID; producer release is authority | Producer team | Reject unsupported version; isolate malformed record | Untrusted external input |
| Ingestion | Preserve received bytes/position and classify outcome | Ingestion team | Continue within reject budget; halt on systemic incompatibility | Controlled boundary |
| Validated dataset | Accepted logical event and explicit exclusions | Dataset owner | Publish private candidate only | Derived, uncertified |
| Metric | Consumer definition and source frontier | Metric owner | Block atomic certification on required rule | Governed output |
| Platform | Reliable execution and rule-result storage | Platform owner | Surface unavailable checks; never convert “not run” to pass | Control plane |
| Consumer | Declared use, tolerance, and escalation | Consumer owner | Honor certification/version and communicate changed need | Contracted consumer |

Ownership is not transferred to the quality platform. A generic rule runner can
execute checks; the producer owns source meaning, the dataset owner owns derived
semantics and repair, and each consumer owns whether a guarantee is sufficient.

## From dimension to executable requirement

| Weak claim | Bounded requirement | Detection | Response |
| --- | --- | --- | --- |
| IDs are valid | `tenant_id` and `event_id` are non-empty canonical strings for 100% of accepted events | Record validator by contract version | Reject and count reason |
| Data is complete | Per tenant/date, accepted + rejected + documented duplicates equals producer control count by frontier | Reconciliation query | Hold publication; investigate source or accounting |
| No duplicates | One logical accepted event per `tenant_id,event_id`; identical redelivery is benign | Uniqueness/conflict query | Deduplicate exact copies; quarantine conflicts |
| Values are consistent | `product_id` exists in the effective-dated product snapshot used by the metric | Temporal relationship query | Hold or route according to late-dimension policy |
| Counts are accurate | Metric equals independent audited sample/control within declared tolerance | External reconciliation | Correct affected publication; notify consumers |
| Data is fresh | 99% of eligible source intervals certify within 120 minutes of source readiness over 28 days | Publication SLI | Page only on fast actionable burn; ticket slow burn |

Validity is often deterministic. Accuracy usually needs an external authority;
recomputing a transform from the same defective input is consistency evidence,
not accuracy evidence.

## SQL and Python models

```sql
-- Dialect-neutral assertion query. Grain: one failing tenant/date measurement.
-- NULL producer_count means unverifiable, not zero and not pass.
select tenant_id, metric_date, producer_count, accounted_count
from daily_control_reconciliation
where producer_count is null
   or accounted_count <> producer_count;
```

```python
from dataclasses import dataclass
from decimal import Decimal

@dataclass(frozen=True)
class QualityRequirement:
    rule_id: str
    dataset: str
    dimension: str
    minimum_ratio: Decimal
    owner: str
    blocking: bool

    def passes(self, valid: int, eligible: int) -> bool:
        if eligible < 0 or valid < 0 or valid > eligible:
            raise ValueError("invalid measurement counts")
        # Empty eligibility needs an explicit dataset policy; it is not 100% good.
        if eligible == 0:
            raise ValueError("empty denominator requires explicit disposition")
        return Decimal(valid) / Decimal(eligible) >= self.minimum_ratio
```

This model keeps counts and policy separate. A distributed engine must still
produce the counts from a consistent dataset snapshot and prevent lost or
double-counted partitions.

## Lifecycle, identity, consistency, and time

A rule moves through proposed, shadow, enforced, revised, and retired states.
Store rule version and dataset version with every result so historical passes
remain interpretable. Event time defines the metric date; ingestion time helps
measure arrival delay; source-ready time starts the completeness obligation; and
certification time ends it. Wall-clock `now()` inside an unreproducible query
makes historical evaluation drift.

“Duplicate” always names identity and scope. The same event ID across tenants may
be legal; the same tenant/event pair with identical payload is redelivery; that
pair with conflicting payload is a contract violation rather than a row to pick
arbitrarily.

## Failure model and recovery

| Failure | Detection and containment | Recovery and convergence |
| --- | --- | --- |
| Missing source partition | Control-count/frontier gap; hold certification | Restore/reingest partition, rerun checks, certify new version |
| Threshold hides one tenant outage | Segmented result and minimum denominator | Add tenant-aware rule and correct affected outputs |
| Rule runner fails | Explicit unavailable status | Repair runner and reevaluate; never reuse stale pass |
| Producer changes meaning without schema change | Consumer reconciliation/incident | Version semantic contract, rebuild history if feasible |
| External authority is wrong | Independent audit and discrepancy triage | Correct authority or rule; retain decision trail |
| Baseline learns an incident | Baseline-version review | Exclude incident interval and rebuild approved baseline |

## Security, privacy, and governance

Rules and failure samples can expose identifiers and rare values. Store counts
and bounded reason codes by default, restrict row samples, tokenize identifiers,
apply source retention/deletion policy to rejected copies, and audit access.
Quality metadata needs owner, classification, rule provenance, approvals,
exceptions, and lineage to each certified version.

## Data quality, testing, and evidence

| Evidence | Dataset and environment | Procedure | Expected result | Result |
| --- | --- | --- | --- | --- |
| Requirement review | Scenario contract / documentation | Trace every rule to consumer harm and owner | No ownerless score or ambiguous denominator | Reviewed in this guide |
| Dimension fixture | Planned faulty event fixture / local | Trigger one controlled violation per dimension | Correct rule and disposition | Pending |
| Segmentation test | Planned skewed tenant fixture / local SQL | Hide a tenant outage in global totals | Segmented rule catches it | Pending |
| Accuracy control | Planned independent control / integration | Inject shared and independent defects | Only independent comparison supports accuracy | Pending |
| Threshold baseline | Production-like history | Backtest candidate thresholds | Bounded false positives and detection delay | Pending |

## Debugging guide

1. Identify the affected consumer decision, publication, rule version, and first bad interval.
2. Inspect the numerator, denominator, segmentation, exclusions, `NULL` handling, and input snapshot.
3. Compare source frontier, accepted/rejected/duplicate accounting, and last known good result.
4. Determine whether data, the authority, the rule implementation, or its threshold changed.
5. Hold or label affected publications; reproduce on a protected minimal sample.
6. Repair, replay, reconcile, and obtain consumer acknowledgement before closure.

## Common pitfalls

### Pitfall: average all dimensions into one score

A perfect freshness result can conceal a catastrophic identity failure. Preserve
dimension-specific measurements and blocking rules tied to harms.

### Pitfall: define completeness as non-nullness

Non-nullness asks whether present rows contain a field. Completeness asks whether
all expected fields, records, intervals, or sources are present relative to an
authority and frontier.

### Pitfall: set thresholds from intuition

An arbitrary threshold pages on normal behavior or tolerates harmful loss.
Backtest by segment and connect tolerance to consumer impact.

## Performance, observability, and cost

Record scanned rows/bytes, distinct-key state, rule latency, scheduler delay,
false-positive rate, detection delay, sample volume, and per-check cost. Reuse a
consistent aggregate profile when it preserves semantics; do not combine rules
whose filters, snapshots, or denominators differ. Bound metric label cardinality:
tenant-level diagnosis may belong in queryable result tables rather than metric
labels.

## Compatibility, migration, and delivery

Introduce a new rule in shadow mode, compare historical and current behavior,
review exceptions with producers and consumers, then enforce it on new
publications. For changed semantics, assign a new rule/metric version; dual-run,
backfill a private generation, compare, cut over atomically, and retain rollback
until consumers accept the result. Never rewrite past quality receipts silently.

## Working example

- Source and tests: Planned under `src/big_data_example/quality/` and `tests/quality/`
- SQL: Planned dimension and segmented assertion queries under `sql/quality/`
- Fixtures: Planned good, missing, duplicate, inconsistent, inaccurate-control, and late cases under `data/fixtures/quality/`
- Try it: Planned standard-library unit suite plus a pinned SQL-engine procedure
- Expected result: Every deliberate defect maps to one named rule and disposition
- Evidence: Planned result receipts, false-positive review, and detection-delay measurement
- Scale represented: Documentation and production estimate only
- Remaining risk: Thresholds, external authority, SQL behavior, skew, and production distributions unverified

## Knowledge check

1. Explain why validity and accuracy are different for a well-formed `product_id`.
2. Predict the result of treating an empty denominator as a perfect pass.
3. Diagnose how a 99.9% global completeness score can hide one tenant's total outage.
4. Design an independent accuracy check for product-view metrics.
5. Estimate check state and scan cost for 100 million events and a composite key.
6. Plan a threshold change without invalidating historical evidence.
7. Write a bounded requirement for duplicate mobile events, including conflicts.

## Key takeaways

- Quality exists relative to a consumer decision and harm.
- A dimension becomes actionable only with scope, measurement, threshold, owner, and response.
- Grain, identity, authority, and time frontiers precede implementation.
- Accuracy requires evidence independent enough to detect a shared defect.
- A failed or unavailable check is not a pass, and a passed snapshot is not a future guarantee.

## Resources

- [ISO/IEC 25012 data quality model overview](https://www.iso.org/standard/35736.html) (reviewed 2026-09)
- [DAMA International body of knowledge overview](https://dama.org/learning-resources/dama-data-management-body-of-knowledge-dmbok/) (reviewed 2026-09)
- [Google SRE Workbook: implementing SLOs](https://sre.google/workbook/implementing-slos/) (reviewed 2026-09)

## Related topics

- [Schema, data, and consumer contracts](02-schema-data-and-consumer-contracts.md)
- [Reconciliation and runtime checks](06-reconciliation-freshness-volume-and-distribution-checks.md)
- [Quality objectives and evidence](08-quality-objectives-observability-and-evidence-portfolios.md)

## Completion checklist

- [x] Dimensions, fitness, requirements, grain, authority, ownership, and time defined
- [x] SQL/Python models, failure, security, cost, migration, and debugging covered
- [x] Requirements tied to consumer harm and evidence boundaries
- [x] Working example and executable evidence accurately marked Planned
- [ ] Fixture, SQL, external-control, threshold, scale, and production evidence executed
