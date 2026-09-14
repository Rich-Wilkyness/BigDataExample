# Logs, Metrics, Traces, Lineage, and Correlation

> Status: Documentation complete; executable telemetry evidence planned  
> Level: Intermediate to Senior  
> Applies to: Batch / Streaming / SQL / Data platforms / Operations  
> Data scale: Production estimate  
> Example status: Planned  
> Evidence status: Documentation and current primary-source review only  
> Last reviewed: 2026-09

## Overview

Observability is the ability to infer relevant internal state from external
evidence. Logs record events, metrics aggregate measurements, traces connect
causal work, and lineage connects data transformations and dataset versions.
None is complete alone, and telemetry is itself a delayed, lossy data pipeline.

This guide designs signal contracts, correlation, privacy, cardinality, sampling,
and telemetry-failure behavior for asynchronous pipelines. It does not select an
observability vendor or claim that instrumentation automatically explains a fault.

## Learning objectives

- Select logs, metrics, traces, lineage, profiles, and quality results by diagnostic question.
- Propagate stable correlation across scheduler, engine, storage, and publication boundaries.
- Bound label cardinality and telemetry cost without losing critical evidence.
- Protect sensitive data in signals and distrust inbound correlation context.
- Detect and represent telemetry delay, loss, duplication, and schema drift.

## Prerequisites

- [Reliability requirements and failure domains](01-data-system-reliability-requirements-and-failure-domains.md).
- [Area 12 metadata and lineage](../12-workflow-orchestration-and-transformation-management/07-metadata-lineage-artifacts-and-data-aware-scheduling.md) and [Area 14 audit evidence](../14-governance-security-privacy-and-data-lifecycle/07-audit-policy-enforcement-and-compliance-evidence.md).
- Planned collector/backend integration for executable evidence.

## Mental model and terminology

```text
one logical interval/publication
  scheduler run -> task attempt -> engine job -> query/stages -> output version
       |                |              |               |
       +-------- trace/context --------+               |
       +-------- structured events + metrics ----------+
       +-------- dataset/run lineage ------------------+

telemetry heartbeat + independent receipts expose gaps in this evidence path
```

| Signal | Best question | Weakness |
| --- | --- | --- |
| Metric | Is a bounded population changing or breaching a threshold? | Aggregation hides individual context; cardinality costs state |
| Structured log/event | What happened to this run/attempt/record class? | Volume, parsing, privacy, and missing-event risk |
| Trace | Where did causal time/failure travel through one execution? | Sampling and asynchronous-link gaps |
| Lineage | Which job/version read or wrote which dataset/version? | Often incomplete or inferred; not request causality |
| Profile | Which code/operator consumed CPU, memory, I/O, or allocation? | Sampling/overhead; needs representative workload |
| Quality result | Is a defined data invariant or distribution satisfied? | The check/authority can share the defect |

Kotlin coroutine context propagation is a useful analogy for trace context. The
analogy stops when work is queued for hours, replayed, fanned out across engines,
or resumed from durable state; an explicit link may be more truthful than a
single synchronous parent-child span tree.

## Requirements, scale assumptions, and invariants

For each signal define producer, schema/version, unit, temporality, time origin,
population, labels/attributes, privacy class, expected delay, retention, sampling,
owner, consumer, and loss behavior. Assume 10,000 task instances/day, 1,000
datasets, 100 tenants, and potentially millions of row-level events; measure before
choosing actual retention or sampling.

Invariants:

- Every publication can be followed through workflow run, task attempt, engine/query job, input frontier, output version, and quality receipt.
- Run, attempt, publication, dataset-version, and event identifiers are distinct and stable within their documented scope.
- Metric labels come from bounded vocabularies; raw IDs and error text do not become labels.
- Sensitive payloads, credentials, query literals, and direct personal identifiers are excluded by default.
- Untrusted propagated context cannot grant authorization or become trusted identity.
- Missing/stale telemetry is observable independently and is not interpreted as success.
- Sampling retains or separately accounts for errors and high-value control events according to policy.

## Data flow, ownership, and trust boundaries

| Boundary | Contract/owner | Failure behavior | Trust |
| --- | --- | --- | --- |
| Instrumented job | Versioned event/metric/span producer; workload owner | Buffer/drop by explicit priority; never block unsafe indefinitely | Application assertions |
| Propagated context | Trace/run links; platform owner | Validate size/format; create new internal identity | Untrusted inbound metadata |
| Collector/agent | Batch, retry, redact, route; observability owner | Backpressure with bounded storage and drop accounting | Privileged telemetry path |
| Backend/index | Queryable signal and retention; platform owner | Expose ingest lag/gaps and partial query | Derived operational evidence |
| Lineage/catalog | Run/job/dataset/version edges; metadata owner | Mark confidence and missing edges | Not business-data authority |
| Dashboard/alert | Versioned queries; service owner | Show stale/unknown source | Human decision boundary |

## Signal design and correlation

Use a correlation envelope rather than one overloaded identifier:

```json
{
  "event_name": "publication.certification.completed",
  "event_schema_version": 1,
  "occurred_at_utc": "2026-09-07T04:12:03Z",
  "workflow_run_id": "scheduled-2026-09-06",
  "task_attempt_id": "aggregate-attempt-2",
  "engine_job_id": "engine-opaque-reference",
  "publication_id": "daily-2026-09-06-v3",
  "dataset_version": "snapshot-1842",
  "tenant_tier": "standard",
  "outcome": "certified",
  "duration_ms": 84231
}
```

Real schemas need canonical identity, limits, producer deployment, safe error
taxonomy, trace/span links, serialization rules, and compatibility tests. Tenant
IDs usually belong in protected event storage, not global metric labels.

### SQL model

```sql
-- Compare an independent expected-run ledger with terminal telemetry.
SELECT r.workflow_run_id,
       r.expected_terminal_at_utc,
       MAX(t.observed_at_utc) AS last_observed_at_utc,
       COUNT(t.event_id) AS terminal_event_count
FROM expected_run r
LEFT JOIN telemetry_event t
  ON t.workflow_run_id = r.workflow_run_id
 AND t.event_name IN ('run.completed', 'run.failed', 'run.aborted')
GROUP BY r.workflow_run_id, r.expected_terminal_at_utc
HAVING COUNT(t.event_id) <> 1;
```

This detects absent or duplicate terminal events only because `expected_run` is
independent. Late-arrival and deduplication windows must be explicit.

### Python model

```python
from collections.abc import Iterable

ALLOWED_METRIC_LABELS = {"job_name", "environment", "outcome", "tenant_tier"}

def label_cardinality(rows: Iterable[dict[str, str]]) -> dict[str, int]:
    values: dict[str, set[str]] = {key: set() for key in ALLOWED_METRIC_LABELS}
    for row in rows:
        for key in ALLOWED_METRIC_LABELS:
            values[key].add(row.get(key, "unknown"))
    return {key: len(found) for key, found in values.items()}
```

The bounded check catches unexpected vocabulary growth. A production SDK/backend
may enforce different cardinality and overflow behavior, which must be pinned and tested.

## Signal selection and sampling

| Need | Prefer | Why | Reconsider when |
| --- | --- | --- | --- |
| Page on freshness harm | Low-cardinality SLI metric | Cheap window evaluation | Eligible population is too sparse |
| Diagnose one failed attempt | Structured event plus trace links | Preserves identity and timeline | Sampling dropped necessary spans |
| Find downstream blast radius | Versioned lineage graph | Traverses datasets/consumers | Edges are inferred/stale |
| Explain CPU regression | Profile plus plan/stage metrics | Attributes resource use | Workload is not representative |
| Investigate one bad row | Restricted quality/quarantine reference | Protects raw data from telemetry | Forensic access is unavailable |

Tail sampling can retain traces after an error is known but needs buffering and a
complete decision boundary. Head sampling is cheaper but may miss rare failures.
Never sample audit or accounting evidence unless the bounded control explicitly
permits it; retain aggregate accounting for whatever is sampled.

OpenTelemetry defines traces, metrics, logs, and baggage as distinct signals and
supports context propagation. OpenLineage models job, run, and dataset metadata.
Neither standard proves producer completeness, backend delivery, or semantic truth.

## Lifecycle, consistency, identity, and time

An observation is created, timestamped, buffered, exported, retried/deduplicated,
processed, indexed, queried, aggregated, archived, and deleted. Record occurrence,
observation, ingestion, and query times; late telemetry can rewrite recent windows.
Trace IDs express causality, not authorization. Lineage run IDs express execution,
not dataset identity. A metrics counter reset or exporter temporality change must
not masquerade as real negative work.

## Failure model and recovery

| Failure | Detection/containment | Recovery |
| --- | --- | --- |
| Collector stalls | Heartbeat, queue age, independent expected events | Mark dashboards unknown; drain/replay bounded buffer |
| High-cardinality label exhausts backend | Series/attribute overflow and cost alarms | Drop/rewrite unsafe dimension; preserve diagnostic events |
| Trace context lost at queue | Parent/run reconciliation reveals orphan | Add durable link field; do not invent causality |
| Duplicate export inflates count | Event identity and monotonic/accounting checks | Deduplicate where semantics require; recompute window |
| Clock skew reverses timeline | Compare occurrence/ingest times and source sequence | Correct presentation; retain original timestamps |
| Sensitive value reaches telemetry | Scanner/access alert | Restrict, purge per policy, rotate secrets, incident review |
| Lineage producer reports false edge | Compare query plan/catalog/write receipts | Correct with confidence/provenance; assess blast radius |

## Security, privacy, and governance

Telemetry concentrates system topology, tenant activity, identities, SQL, errors,
and sometimes payload fragments. Minimize at instrumentation, sanitize untrusted
text to prevent log injection, apply per-tenant and role access, encrypt, audit
queries/exports, retain deliberately, and propagate deletion where applicable.
OpenTelemetry baggage can cross process/network boundaries and has no inherent
integrity guarantee; allowlist safe fields and strip it before untrusted egress.

## Data quality, testing, and evidence

| Evidence | Environment/procedure | Expected result | Result |
| --- | --- | --- | --- |
| Schema/PII contract | Deterministic safe/unsafe events | Unsafe fields reject/redact; versions decode | Pending |
| Correlation | Local scheduled-to-published fixture | Every boundary links without conflating IDs | Pending |
| Cardinality | Synthetic tenants/runs/errors | Series remain within stated budget | Pending |
| Collector fault | Integration delay/drop/duplicate exercise | Gaps and lag display unknown; replay accounts exactly | Pending |
| Lineage completeness | Real engine/catalog comparison | Missing/wrong edges quantified | Pending |
| Load/cost | Representative event/span/metric volume | Ingest, query, retention, and spend budgets measured | Pending |

## Debugging guide

Start with consumer symptom and publication, then traverse quality receipt,
lineage, workflow run, task attempt, engine job, trace/span links, structured
events, and metrics. Check telemetry source version, collector lag, sampling
decision, dropped/overflow counters, clock skew, backend query range, and dashboard
definition. Compare against independent scheduler, storage, and publication
receipts. Treat missing evidence as a telemetry incident, not proof of no event.

## Common pitfalls

### Pitfall: put every identifier in metric labels

Run/tenant/query/error text creates unbounded series and cost. Keep bounded
dimensions in metrics and link to restricted events by exemplars or identifiers.

### Pitfall: log the whole row for convenience

It creates an uncontrolled sensitive copy. Emit safe metadata and a protected
quarantine/forensic reference with explicit access and lifecycle.

### Pitfall: force asynchronous work into one span tree

Retries, queues, and replays can have multiple causal parents. Use explicit span
links and durable run/publication identity rather than a misleading parent.

## Performance, capacity, and cost

Budget events/second, bytes/event, metric series, histogram buckets, active spans,
profile samples, collector CPU/memory/disk/network, backend ingest/query latency,
retention tiers, and money. Signal value differs: retain aggregate trends longer,
detailed diagnostic events for a shorter approved period, and critical evidence
according to governance. Measure instrumentation overhead under representative load.

## Observability and operations

Observe the observability system: accepted/rejected/dropped records, retry queue,
oldest age, export failure, series overflow, sampling rates, clock skew, backend
query errors, lineage lag, dashboard data timestamp, and alert evaluation health.
Canary telemetry should exercise the entire path. Runbooks state how to distinguish
application recovery from telemetry recovery.

## Compatibility, migration, and delivery

Version event schemas, semantic conventions, metric names/units/temporality,
attribute vocabularies, trace propagation, lineage facets, sampling, dashboards,
and alerts. Dual-emit only with a cost/cardinality bound; compare old/new queries,
annotate discontinuities, and retain readers across the compatibility window.

## Working example

- Models: Planned typed telemetry envelope and cardinality checker under `src/big_data_example/operations/`
- SQL: Planned expected-versus-observed terminal event query under `sql/operations/`
- Tests: Planned schema, privacy, correlation, duplicate, drop, delay, cardinality, and lineage cases
- Expected result: One publication is diagnosable across boundaries; telemetry loss becomes unknown
- Scale represented: Local fixture and production estimate; no backend integration or load run
- Remaining risk: SDK/backend semantics, sampling bias, high cardinality, lineage completeness, privacy, and cost

## Knowledge check

1. Choose a signal for objective alerting, one-run diagnosis, blast radius, and CPU attribution.
2. Predict what a run ID used as a metric label does to series count.
3. Diagnose a green dashboard while the collector queue age grows.
4. Design correlation across scheduler, queue, engine retry, and publication.
5. Estimate daily telemetry bytes and active metric series.
6. Plan a metric-unit and event-schema migration without breaking alerts.
7. Add a safe failure event and a negative privacy test.

## Key takeaways

- Signals are complementary data products with their own failure modes.
- Correlation uses several scoped identities; one ID should not mean everything.
- Cardinality, sampling, retention, and privacy are correctness and cost decisions.
- Telemetry health needs independent evidence.
- A lineage or trace assertion is only as trustworthy as its producer and delivery path.

## Resources

- [OpenTelemetry signals](https://opentelemetry.io/docs/concepts/signals/) (reviewed 2026-09; signal/profile status is version-sensitive)
- [OpenTelemetry context propagation](https://opentelemetry.io/docs/concepts/context-propagation/) (reviewed 2026-09)
- [OpenTelemetry metrics data model](https://opentelemetry.io/docs/specs/otel/metrics/data-model/) (reviewed 2026-09)
- [OpenLineage object model](https://openlineage.io/docs/spec/object-model/) (reviewed 2026-09; implementation version must be pinned)
- [OWASP Logging Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Logging_Cheat_Sheet.html) (reviewed 2026-09)

## Related topics

- [Data SLIs, SLOs, alerts, dashboards, and runbooks](03-data-slis-slos-alerts-dashboards-and-runbooks.md)
- [Performance profiling and query plans](06-performance-profiling-query-plans-and-capacity-modeling.md)
- [Area 12 metadata and lineage](../12-workflow-orchestration-and-transformation-management/07-metadata-lineage-artifacts-and-data-aware-scheduling.md)

## Completion checklist

- [x] Signal choice, schema, identity, correlation, time, sampling, cardinality, privacy, failure, operations, cost, and migration covered
- [x] SQL/Python models and product-specific limits identified
- [x] Working example and executable evidence accurately marked Planned
- [ ] Schema, correlation, collector-fault, lineage, load, cost, and production evidence executed
