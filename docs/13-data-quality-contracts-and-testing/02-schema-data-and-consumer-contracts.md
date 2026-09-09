# Schema, Data, and Consumer Contracts

> Status: Documentation complete; executable contract evidence planned  
> Level: Beginner to Senior  
> Applies to: APIs / Events / Files / Tables / Batch / Streaming  
> Data scale: Local contract fixture; production estimate  
> Example status: Planned  
> Evidence status: Documentation and current primary-source review only  
> Last reviewed: 2026-09

## Overview

A data contract is a versioned agreement at a producer-consumer boundary. A
schema describes structure: names, types, required fields, and sometimes local
value constraints. A complete contract also describes semantics, grain,
identity, units, time, ordering, completeness, privacy, lifecycle, compatibility,
and support. Consumer contracts state the smaller set of behaviors a particular
consumer actually relies on.

This guide covers contract design and enforcement. It does not claim that a
schema registry proves data quality or that one contract format fits every
engine.

## Learning objectives

- Separate structural, semantic, operational, and consumer guarantees.
- Select enforcement points based on what each boundary can know.
- Classify changes by actual consumer compatibility rather than syntax alone.
- Design expand, migrate, and contract rollouts with observable adoption.
- Handle unknown, invalid, duplicate, and mixed-version data explicitly.

## Prerequisites

- [Quality requirements and ownership](01-data-quality-dimensions-requirements-and-ownership.md).
- Area 05 grain and semantics, Area 06 schema evolution, and Area 10 event boundaries.

## Mental model and terminology

```text
producer implementation
      |  structural envelope + semantic promise
      v
boundary enforcement -----> rejected/quarantined evidence
      |
      v
versioned dataset contract
      |---- consumer A projection and assumptions
      `---- consumer B projection and assumptions
```

| Term | Meaning in this guide |
| --- | --- |
| Schema contract | Machine-checkable structure and local constraints under a named dialect/version |
| Data contract | Schema plus semantic, quality, operational, governance, and ownership guarantees |
| Consumer contract | The fields, meanings, timing, and behavior one named consumer depends on |
| Compatibility | Whether old/new producers, stored data, and consumers interoperate for a stated direction and period |
| Enforcement point | Boundary that rejects, quarantines, warns, or blocks publication based on a contract |
| Semantic version | Contract identifier tied to meaning; it need not follow a particular numbering scheme |

This resembles an interface shared between Android modules. It differs because
stored messages and rows remain active after both modules upgrade, multiple
versions coexist, and “same type” cannot prove “same business meaning.”

## Requirements, scale assumptions, and invariants

- Each event declares `contract_version`; the validator records both declared
  version and actual rule-set version.
- The logical grain is one mobile action per `tenant_id,event_id`.
- Event time is an RFC 3339 timestamp with an offset; canonical storage is UTC,
  while the original offset may be retained when required.
- `event_name` is an extensible domain unless a consumer explicitly requires a
  closed set. Unknown values do not become a different known value.
- `product_id` is conditionally required for `product_view`; empty strings do not
  become valid identifiers through silent trimming alone.
- Structural rejection occurs before semantic transformation. Raw bytes and
  source position remain available under governed retention for replay.
- Contract checks are deterministic for a fixed payload, contract/rule versions,
  reference snapshot, and evaluation time.
- Compatibility covers producer, stored history, processor, and every registered
  consumer during the migration window.
- 500 events/s burst and 35 days of mixed historical versions are estimates;
  validation latency, registry availability, and adoption rates are unmeasured.

## Contract layers and enforcement

| Layer | Example guarantee | Best enforcement point | Limit |
| --- | --- | --- | --- |
| Envelope | Required ID/version fields and primitive types | Producer CI and ingestion parser | Cannot prove cross-row or external meaning |
| Record semantics | Product view requires product ID | Producer test and ingestion/domain validator | May require versioned reference data |
| Dataset | Unique logical identity and complete source frontier | Transformation/publication gate | Detected after multiple records arrive |
| Operational | Daily data certified by deadline | Scheduler/quality objective | Does not establish correctness |
| Governance | Classification, retention, permitted use | Catalog/storage/access boundary | Policy metadata needs enforcement and audit |
| Consumer | Dashboard uses UTC daily views and tolerates 15-minute corrections | Consumer contract test and release gate | Protects only the registered dependency |

Validate as early as useful and again where knowledge expands. Producer checks
give fast feedback; ingestion protects shared systems; dataset checks see
cross-record behavior; publication gates protect consumers. Duplicated checks
are justified when they defend different trust boundaries.

## Structural example

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://example.invalid/contracts/mobile-event/v1",
  "type": "object",
  "required": ["contract_version", "tenant_id", "event_id", "event_time", "event_name"],
  "properties": {
    "contract_version": {"const": 1},
    "tenant_id": {"type": "string", "minLength": 1},
    "event_id": {"type": "string", "minLength": 1},
    "event_time": {"type": "string", "format": "date-time"},
    "event_name": {"type": "string", "minLength": 1},
    "product_id": {"type": ["string", "null"]}
  },
  "additionalProperties": false
}
```

The dialect must be pinned. JSON Schema format handling depends on vocabulary and
validator configuration; test the exact implementation. The schema cannot alone
express reference existence, uniqueness across messages, source completeness, or
consumer freshness.

```python
from dataclasses import dataclass
from datetime import datetime

@dataclass(frozen=True)
class ContractViolation:
    rule_id: str
    path: str
    reason_code: str

def validate_semantics(event: dict[str, object]) -> tuple[ContractViolation, ...]:
    violations: list[ContractViolation] = []
    if event.get("event_name") == "product_view" and not event.get("product_id"):
        violations.append(ContractViolation(
            "product-view-requires-product-v1", "$.product_id", "missing_required_context"
        ))
    value = event.get("event_time")
    try:
        parsed = datetime.fromisoformat(value) if isinstance(value, str) else None
    except ValueError:
        parsed = None
    if parsed is None or parsed.tzinfo is None:
        violations.append(ContractViolation(
            "event-time-offset-v1", "$.event_time", "invalid_or_missing_offset"
        ))
    return tuple(violations)
```

Production validation must bound payload size and parse depth before
materializing untrusted content. Reference-dependent rules also pin the lookup
snapshot; application code cannot make a remote registry or catalog available.

## Compatibility and change decisions

| Change | Usually safe only when | Evidence required |
| --- | --- | --- |
| Add optional field | Old readers ignore unknown fields and new readers handle absence | Old/new reader fixtures and stored-history replay |
| Add required field | Producers populate it only after all readers/processors tolerate it | Expand/migrate/contract adoption proof |
| Widen numeric domain | Serialization and every consumer preserve range/precision | Boundary and historical-value tests |
| Rename field | Old and new names coexist or translation is versioned | Dual-write/read comparison and usage telemetry |
| Change unit/time semantics | New field/semantic version prevents silent reinterpretation | Consumer acceptance and historical backfill plan |
| Remove enum value | No retained record or producer emits it and consumers handle history | Usage scan, retention proof, replay test |
| Allow unknown fields | Security and consumers tolerate extension | Parser and downstream projection tests |

Backward and forward compatibility are directional and format-specific. A schema
tool's compatibility result is necessary evidence for structure, not proof of
semantic or operational compatibility.

## Data flow, ownership, and trust boundaries

| Boundary | Authority and input | Owner | Failure behavior | Trust level |
| --- | --- | --- | --- | --- |
| Contract source | Reviewed versioned artifact | Domain producer + consumers | No unreviewed mutation | Governance control |
| Registry/catalog | Contract distribution and identity | Platform owner | Cache known versions; reject unknown when correctness requires | Control plane |
| Ingestion validator | Untrusted payload + pinned contract | Ingestion owner | Reject/quarantine with bounded safe reason | Enforcement |
| Reference validator | Event + versioned product snapshot | Domain dataset owner | Defer or quarantine if authority unavailable | Cross-system |
| Consumer release | Projection + old/new fixture | Consumer owner | Block incompatible release | Independent boundary |

## Lifecycle, ordering, identity, and time

Publish immutable contract versions and separately move an environment's active
policy. Never alter a version in place. A message's contract version, producer
release, ingestion rule version, reference snapshot, and dataset publication are
distinct IDs. Arrival order is not version order: old clients may emit v1 after
v2 appears, and replay reintroduces historical versions.

Contract retirement therefore depends on producer adoption, retained-data and
replay horizons, consumer usage, quarantine backlog, and rollback windows—not a
deployment completion flag.

## Failure model and recovery

| Failure | Detection/containment | Recovery |
| --- | --- | --- |
| Unknown contract version | Parser routes reason and source position | Add reviewed support or correct producer, then replay |
| Same schema, changed meaning | Consumer differential/reconciliation | Introduce semantic version and rebuild affected data |
| Registry unavailable | Cached immutable contract if policy permits | Restore registry; reconcile validations performed during outage |
| Validator versions disagree | Conformance fixture across implementations | Align dialect/config; revalidate affected interval |
| Required-field rollout races | Mixed-version contract test | Restore optional/dual field; resume staged migration |
| Unknown field carries sensitive data | Classification scanner and restricted quarantine | Contain, delete per policy, correct producer/allowlist |
| Replayed old data fails new rules | Rule/contract version mismatch visible | Validate under historical contract, then explicit migration |

## Security, privacy, and governance

Limit payload size, nesting, regex complexity, and reference lookups to resist
resource exhaustion. Do not log full rejected payloads. Contract artifacts state
classification, allowed purposes, retention, erasure behavior, owner, support,
and schema provenance. Registries and CI require least privilege, immutable
audit, dependency integrity, backup, and restore tests.

## Data quality, testing, and evidence

| Evidence | Dataset/environment | Procedure | Expected result | Result |
| --- | --- | --- | --- | --- |
| Schema examples | Good/bad JSON fixture / exact validator | Validate boundary and format cases | Stable accepted/rejected set | Pending |
| Producer/consumer matrix | v1/v2 payloads and readers | Run every supported pairing | Declared compatibility holds | Pending |
| Semantic contract | Conditional and reference fixtures | Run pinned rule/reference versions | Correct reason and disposition | Pending |
| Historical replay | Retained version corpus | Validate new processor against all supported versions | No silent reinterpretation | Pending |
| Registry fault | Real registry/test service | Remove/restore availability | Policy contains and recovers safely | Pending |

## Debugging guide

1. Capture raw source identity, declared contract version, validator implementation/configuration, rule version, and reference snapshot.
2. Reproduce with protected exact bytes; distinguish parse, structural, semantic, dataset, and consumer failure.
3. Compare producer release and consumer compatibility matrix, including retained history.
4. Inspect rejection counts by low-cardinality reason without exposing payloads.
5. Freeze activation or revert the active policy; immutable versions remain intact.
6. Correct, revalidate, replay, reconcile, and confirm adoption before retirement.

## Common pitfalls

### Pitfall: schema equals contract

Structure can pass while units, grain, identity, or business meaning changes.
Document and test semantic, operational, and governance guarantees separately.

### Pitfall: additive is always compatible

A strict reader may reject unknown fields, a projection may use positional
layout, or the added field may change meaning. Test actual old/new participants.

### Pitfall: mutate a published version

Historical evidence becomes irreproducible. Publish an immutable successor and
record the policy transition.

## Performance, capacity, and cost

Measure validation CPU and p95/p99 latency, allocations, registry/cache hit rate,
payload and nesting limits, reference-lookup latency, reason cardinality,
quarantine storage, and replay throughput. Sampling may reduce observational
cost, but boundary rejection for required identity cannot be sampled.

## Compatibility, migration, backfill, and delivery

Use expand/migrate/contract: publish a reader that accepts old and new; deploy
and observe it; enable producers; backfill or translate retained data if needed;
verify every consumer and replay path; then retire old behavior after rollback
and retention windows. A breaking semantic change usually deserves a new field,
dataset, or metric version rather than an in-place reinterpretation.

## Working example

- Contract artifacts: Planned under `data/contracts/mobile-event/`
- Validators: Planned under `src/big_data_example/quality/`
- Tests: Planned producer/consumer compatibility matrix under `tests/quality/`
- Try it: Planned pinned JSON Schema validator plus standard-library semantic tests
- Expected result: Deliberate structural and semantic failures have stable reason codes
- Evidence: Planned conformance, mixed-version, replay, registry-fault, and performance results
- Scale represented: Documentation and estimate only
- Remaining risk: Validator dialect, registry, real clients, historical diversity, and throughput unverified

## Knowledge check

1. Explain why a schema-compatible unit change can break every consumer.
2. Predict what a strict v1 reader does with an added v2 field.
3. Diagnose two validators disagreeing about `format: date-time`.
4. Design an enforcement map for identity, referential integrity, and freshness.
5. Estimate validation/replay work for 35 days at 3 million events/day.
6. Plan an optional-to-required field migration with rollback.
7. Add a consumer contract for a dashboard that uses only UTC product views.

## Key takeaways

- Schemas constrain representation; data contracts also constrain meaning and operation.
- Compatibility is directional, participant-specific, and historical.
- Enforce each rule where the required knowledge and recovery boundary exist.
- Immutable versions and recorded rule context make evidence reproducible.
- Consumer tests catch dependencies that producer-side schema checks cannot see.

## Resources

- [JSON Schema Draft 2020-12](https://json-schema.org/draft/2020-12) (reviewed 2026-09)
- [JSON Schema validation vocabulary](https://json-schema.org/draft/2020-12/json-schema-validation) (reviewed 2026-09)
- [RFC 3339 date and time on the Internet](https://www.rfc-editor.org/rfc/rfc3339) (reviewed 2026-09)

## Related topics

- [Quality requirements and ownership](01-data-quality-dimensions-requirements-and-ownership.md)
- [Integration and contract testing](04-integration-contract-and-end-to-end-pipeline-testing.md)
- [Area 06 ingestion and schema evolution](../06-data-ingestion-and-source-integration/README.md)

## Completion checklist

- [x] Structural, semantic, operational, governance, and consumer contracts separated
- [x] Enforcement, compatibility, mixed versions, security, failure, and migration covered
- [x] Python/JSON examples and evidence boundaries explicit
- [x] Working example and executable evidence accurately marked Planned
- [ ] Validator, compatibility matrix, registry, replay, fault, and load evidence executed
