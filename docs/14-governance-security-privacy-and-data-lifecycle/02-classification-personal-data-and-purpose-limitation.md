# Classification, Personal Data, and Purpose Limitation

> Status: Documentation complete  
> Level: Beginner to Senior  
> Applies to: Generic data engineering / Batch / Streaming / Storage / Analytics  
> Data scale: Production estimate  
> Example status: Planned  
> Evidence status: None  
> Last reviewed: 2026-09

## Overview

Classification describes the harm and handling needs of data in context.
Personal data can identify or be linked to a person directly or through
combination. Purpose limitation connects collection and each later use to a
specific approved outcome. Minimization asks whether each field, precision,
population, and retention period is necessary for that purpose.

This is engineering education, not legal advice. Applicable definitions, lawful
bases, rights, and obligations depend on jurisdiction, contract, role, and facts;
qualified privacy/legal owners make those decisions.

## Learning objectives

After completing this guide, you should be able to:

- Classify fields and combinations using impact, identifiability, and context.
- Model purpose and lawful/organizational authority separately from access.
- Minimize collection, precision, linkage, population, and retention.
- Trace classification and purpose through derived data and logs.
- Diagnose purpose drift, unexpected payloads, and unsafe derived features.

## Prerequisites

- [Ownership, catalogs, and lineage](01-data-ownership-stewardship-catalogs-and-lineage.md).
- Planned classified fixture and policy evaluator for executable evidence.

## Mental model and terminology

A Kotlin data class describes shape, while classification describes consequence.
`String userId` says nothing about whether it identifies a person, tenant, or
device. The analogy stops further because risk can emerge only after joining two
otherwise low-sensitivity datasets.

```text
business purpose -> necessity test -> collection contract -> transformations
       |                  |                  |                    |
       +-------- approval/version ----------+------ lineage -----+
                                                          |
                                            reclassify every output/use
```

| Term | Meaning in this guide |
| --- | --- |
| Direct identifier | Attribute that identifies a subject in the relevant context |
| Quasi-identifier | Attribute that can identify when combined with other information |
| Sensitive data | Data whose disclosure or misuse can cause elevated harm under policy |
| Purpose | Specific, documented outcome for which processing is approved |
| Minimization | Limiting data, precision, population, access, and lifetime to necessity |
| Derived data | Output inferred or computed from source data; it can remain personal/sensitive |

## Requirements, scale assumptions, and invariants

For each dataset and purpose record owner, subject/population, fields, sensitivity,
authority decision, recipients, location, retention, prohibited uses, and review
date. Assume 80 event fields, 12 purposes, 30 derived datasets, and 100 tenants.

Invariants:

- Missing classification or purpose is not equivalent to public or unrestricted.
- An approved purpose is necessary but does not itself authorize an identity.
- Classification propagates conservatively until a documented transformation and risk review changes it.
- Derived, aggregated, logged, quarantined, and inferred data are in scope.
- Optional app consent/permission and server-side purpose state are versioned and time-bounded.
- Collection rejects or isolates fields outside the declared contract.

## Data flow, ownership, and trust boundaries

| Boundary | Input contract | Authority and owner | Failure behavior | Trust level |
| --- | --- | --- | --- | --- |
| Mobile envelope | Allowed fields, consent/context version | Producer/domain owner | Quarantine unknown sensitive fields | Untrusted |
| Classification registry | Field and combination rules | Privacy owner + data owner | Unknown defaults restricted | Privileged metadata |
| Purpose registry | Purpose, necessity, authority, expiry | Business/privacy approvers | Expired purpose denies new processing | Governed control state |
| Transform | Inputs, output schema, purpose | Pipeline owner | Block incompatible output/use | Workload boundary |
| Consumer request | Dataset, fields, purpose, identity | Consumer owner | Deny and record reason | Untrusted claim until verified |

## Classification and purpose decisions

Classify at multiple levels: dataset defaults, field overrides, row/population
conditions, and risky combinations. A coarse location may be internal while a
precise trace linked to device ID is restricted. Aggregation lowers risk only
when group size, outliers, differencing, auxiliary data, and query repetition are
considered.

Use a purpose record rather than a free-text ticket:

| Attribute | Example |
| --- | --- |
| Purpose ID | `product-analytics-v3` |
| Outcome | Measure daily product interaction trends |
| Necessary fields | Tenant, coarse product, UTC day, event kind |
| Explicit exclusions | Advertising, individual profiling, precise location |
| Population/recipient | Participating tenants; approved analytics roles |
| Retention/review | Aggregates 13 months; review every 6 months |

### SQL model

```sql
SELECT u.field_name
FROM declared_use_field u
LEFT JOIN approved_purpose_field p
  ON p.purpose_id = u.purpose_id
 AND p.purpose_version = u.purpose_version
 AND p.field_name = u.field_name
WHERE u.job_version = :job_version
  AND p.field_name IS NULL;
```

An empty result proves only that declared fields are allowed by the selected
registry snapshot. Runtime schema inspection and lineage reconciliation must
detect undeclared reads and dynamically constructed outputs. Bind parameters.

### Python model

```python
from dataclasses import dataclass

@dataclass(frozen=True)
class PurposeDecision:
    purpose_id: str
    version: int
    allowed_fields: frozenset[str]
    expires_at_utc: str

def excess_fields(read_fields: set[str], decision: PurposeDecision) -> set[str]:
    return read_fields - decision.allowed_fields
```

This pure comparison does not validate approval, expiry, subject state, or
runtime reads; those are authoritative boundary responsibilities.

## Lifecycle, identity, consistency, and time

Classification begins before collection and follows data through raw, validated,
derived, aggregate, export, log, cache, archive, and deletion evidence. Purpose
state is evaluated at job admission and, for long work, rechecked at bounded
intervals. A revoked optional purpose stops future processing; historical repair
is a separate policy decision, not a guessed technical behavior.

Identity includes tenant and data subject scope. Device, account, household, and
person are not interchangeable. Store the mapping authority and effective time
needed for access/deletion without copying direct identifiers everywhere.

## Failure model and recovery

| Failure | Detection/containment | Recovery and proof |
| --- | --- | --- |
| Producer sends undeclared field | Schema diff and safe quarantine | Owner classifies or removes; replay approved records |
| Purpose expires mid-backfill | Admission/lease check stops new partitions | Reapprove or cancel; enumerate outputs already created |
| Join creates re-identification risk | Lineage plus combination rule/review | Restrict output, reduce detail, or remove linkage |
| Classification registry unavailable | Deny risky new use; cached bounded policy | Restore and reconcile decision versions |
| Consent/purpose event arrives late | Effective-time state and correction queue | Recompute scoped outputs under approved policy |
| Model infers sensitive attribute | Output review and monitoring | Classify output; restrict/delete and assess incident |

## Security, privacy, and governance

Keep purpose and classification metadata tamper-evident and access-controlled.
Do not put raw values in catalog descriptions, rule failures, logs, samples, or
tickets. Threats include insiders relabeling data, consumers declaring a false
purpose, inference from repeated aggregate queries, and exports escaping policy.

## Data quality, testing, and evidence

| Evidence | Dataset and environment | Procedure | Expected result | Result |
| --- | --- | --- | --- | --- |
| Classification fixture | Direct, quasi, derived, and combined fields | Planned rule tests | Expected class and conservative unknown | Pending |
| Purpose policy | Approved/expired/incompatible cases | Planned decision tests | Only necessary fields allowed | Pending |
| Runtime reconciliation | Real test query/job metadata | Compare declared with observed reads | Excess reads surfaced | Pending |
| Lineage propagation | Derived graph fixture | Planned propagation cases | Restricted inputs do not silently become public | Pending |

## Debugging guide

Identify dataset/schema/purpose/policy/job versions and affected subjects,
tenants, fields, outputs, and consumers. Inspect producer contract, raw schema,
runtime reads, lineage, registry history, decision reason, exports, logs, and
caches. Contain further processing before relabeling. Close only after copies are
enumerated, policy is corrected, affected outputs are repaired, and owners record
the decision.

## Common pitfalls

### Pitfall: classify by column name only

Names miss payload content and risky combinations. Validate values at ingress,
classify semantic fields, and review joins/outputs.

### Pitfall: equate consent with every purpose

Consent, another authority, product permission, and authorization are different
states. Model the applicable decision explicitly and do not invent legal rules in code.

### Pitfall: assume aggregates are anonymous

Small groups, differencing, outliers, and auxiliary data can reveal individuals.
Apply release controls and risk review proportional to the threat model.

## Performance, observability, and cost

Measure unclassified fields/datasets, incompatible-purpose attempts, decision
latency, registry freshness, unknown schemas, lineage propagation delay, and
review expiry. Classification at field/read time can add catalog lookups and plan
analysis; cache only versioned policy with bounded staleness. Cost minimization
may align with data minimization, but cheaper storage never justifies extra use.

## Compatibility, migration, and delivery

Version field semantics, classes, purposes, decisions, and consumer declarations.
For stricter classification, inventory affected copies and consumers, deploy
controls before the label becomes authoritative, validate negative access, then
cut over. Rollback may restore service behavior but cannot undo an unauthorized
disclosure; incident and repair paths remain necessary.

## Engineering tradeoffs

| Choice | Prefer when | Cost/risk | Reconsider when |
| --- | --- | --- | --- |
| Dataset class | Uniform sensitivity | Over-restricts safe fields | Field controls are enforceable |
| Field/combination class | Mixed schemas and joins | Policy complexity | Engines cannot enforce reliably |
| Collect then filter | Boundary cannot filter safely | Excess data and exposure | Producer contract can minimize |
| Pre-approved purpose set | Stable repeated processing | Purpose drift | New use or population appears |

## Working example

- Models: Planned classification/purpose registry under `src/big_data_example/governance/`
- SQL: Planned declared-versus-observed field checks under `sql/governance/`
- Tests: Planned unknown-field, purpose-expiry, join-risk, and lineage cases
- Expected result: Unknown/excess data is contained and cannot silently reach consumers
- Scale represented: Local policy fixture and production estimate; no engine enforcement
- Remaining risk: Jurisdiction decisions, inference, dynamic queries, policy staleness, and shadow exports

## Knowledge check

1. Explain why type, classification, authorization, and purpose are separate.
2. Predict classification after joining coarse location with a device map.
3. Diagnose a new JSON payload field that appears only in quarantine logs.
4. Design a minimum purpose record for reliability telemetry.
5. Estimate policy checks for 10,000 jobs/day with admission and hourly renewal.
6. Plan a change from internal to restricted classification.
7. Remove one unnecessary field and define proof that collection stopped.

## Key takeaways

- Classification is contextual and includes combinations and derived inferences.
- Purpose limits collection and every later use; access is a separate decision.
- Missing metadata is uncertainty, not permission.
- Minimize fields, precision, population, linkage, lifetime, and visibility.
- Policy changes require inventory, lineage, enforcement, repair, and evidence.

## Resources

- [NIST Privacy Framework](https://www.nist.gov/privacy-framework) (reviewed 2026-09; 1.1 was an initial public draft)
- [NIST SP 800-188: De-Identifying Government Datasets](https://csrc.nist.gov/pubs/sp/800/188/final) (reviewed 2026-09)
- [EU General Data Protection Regulation, official text](https://eur-lex.europa.eu/eli/reg/2016/679/oj) (reviewed 2026-09; applicability requires qualified legal review)

## Related topics

- [Ownership and lineage](01-data-ownership-stewardship-catalogs-and-lineage.md)
- [Safe nonproduction data](05-masking-tokenization-and-safe-nonproduction-data.md)
- [Retention and deletion](06-retention-deletion-legal-holds-and-data-subject-workflows.md)

## Completion checklist

- [x] Classification, personal/derived data, purpose, minimization, lifecycle, failure, security, scale, and migration covered
- [x] Legal boundary and planned evidence explicit
- [x] Working example accurately marked Planned
- [ ] Policy, runtime-read, lineage, inference, access, and production evidence executed

