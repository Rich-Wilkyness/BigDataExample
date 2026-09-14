# Data Architecture Patterns and Trust Boundaries

> Status: Documentation complete  
> Level: Beginner to Intermediate  
> Applies to: Generic data engineering / Batch / Streaming / Storage / Platform  
> Data scale: Local fixture through distributed production estimate  
> Example status: Complete architecture review  
> Evidence status: Architecture / Security boundary review  
> Last reviewed: 2026-09

## Overview

A data architecture arranges ownership, contracts, storage, processing, and
consumer boundaries to meet requirements. Patterns such as direct integration,
layered batch, event-driven flows, warehouses, lakes, lakehouses, and domain data
products are reusable shapes—not goals or complete designs.

A trust boundary is where identity, authority, validation, classification, or
failure assumptions change. Explicit boundaries prevent invalid input, tenant
failures, accidental access, and partial publication from spreading unchecked.
This guide compares patterns without selecting vendor products.

## Learning objectives

After completing this guide, you should be able to:

- Draw a system context and label data, control, ownership, and trust boundaries.
- Compare direct, layered, event-driven, and domain-oriented architecture shapes.
- Place validation, quarantine, access control, and publication boundaries.
- Analyze blast radius, tenancy, coupling, and recovery paths.
- Choose the smallest architecture that meets current requirements and can evolve.

## Prerequisites

Read guides 01–06 in this area, especially
[Sources, sinks, authority, and derived data](05-sources-sinks-authority-and-derived-data.md)
and [Correctness, freshness, latency, throughput, and cost](06-correctness-freshness-latency-throughput-and-cost.md).

## Terminology

| Term | Meaning in this guide |
| --- | --- |
| Architecture pattern | Reusable arrangement of components and responsibilities with known forces |
| Trust boundary | Point where security or data-validity assumptions change and controls must be enforced |
| Blast radius | Maximum consumers, data, tenants, or operations affected by a failure |
| Layer | Boundary with a distinct contract and responsibility, not merely a folder name |
| Tenant | Workload, domain, customer, or organization whose resources/data require isolation |
| Data product | Owned, discoverable, contracted dataset or capability intended for consumers |

## Requirements, scale assumptions, and invariants

The shared scenario needs a daily dashboard, 30-day replayable raw data, 3
million baseline events/day, correction support, pseudonymous identifiers, and
source isolation. The current system has one producer domain and a small number
of consumers. A future hourly consumer is plausible but not approved scope.

Invariants:

- External input is authenticated where possible, structurally and semantically
  validated, bounded, and never trusted merely because it is inside the network.
- Raw accepted data is immutable within retention and not a general consumer API.
- Derived publication is atomic at the dataset-version boundary.
- Least privilege and purpose restrictions apply at every copy.
- Tenant or workload overload is contained before shared capacity collapses.
- Architecture components exist only to supply a named guarantee or constraint.

## Mental model

```text
UNTRUSTED / PRODUCER TRUST        RESTRICTED DATA TRUST          CONSUMER TRUST

[Android] --TLS/auth/limits--> [Collector] --commit--> [Raw version]
                                                  | validation/quarantine
                                                  v
                                           [Transform staging]
                                                  | quality + atomic publish
                                                  v
                         [Catalog/policy] ---> [Curated version] ---> [Dashboard]
                              ^                      |
                              +--- lineage/audit ----+

CONTROL TRUST: deployment, identities, secrets, schemas, policy, catalog, scheduler
```

Clean Architecture on Android is a useful analogy: explicit boundaries control
dependency direction and make policies testable. The analogy stops because data
is copied across boundaries, persists beyond process lifetime, and may have many
independent consumers and historical versions.

## Pattern comparison

| Pattern | Useful when | Guarantee it can support | Main risks |
| --- | --- | --- | --- |
| Direct source-to-consumer | One controlled consumer, low scale, stable source | Minimal delay and components | Source coupling/load, weak history, hidden contract |
| Layered raw/validated/curated | Replay, quality isolation, multiple consumers | Traceable correction and controlled publication | Duplicate storage, unclear layers, small files |
| Event log with independent consumers | Multiple consumers need ordered-per-key change stream | Decoupled consumption and replay within retention | Schema evolution, lag, duplicates, state and broker operations |
| Central analytical platform | Shared governance and cross-domain analysis | Consistent access and reusable controls | Central bottleneck and large blast radius |
| Domain data products on shared platform | Domain meaning and autonomy at organizational scale | Local accountability with common guardrails | Contract/version sprawl and governance coordination |

For the current scenario, a simple layered batch flow is adequate. An event log
or domain mesh is not justified by one daily consumer.

## Layer responsibilities

| Boundary/layer | Input contract | Owner/authority | Required controls | Failure containment |
| --- | --- | --- | --- | --- |
| Collection | Versioned bounded event | Ingestion owns acceptance | Authentication, size/rate limits, schema routing | Reject/quarantine; backpressure |
| Raw | Accepted immutable envelope | Raw owner owns durable receipt | Encryption, restricted access, manifest, retention | No consumer sees partial version |
| Validated | Parsed event under rule version | Pipeline owns validation result | Semantic checks, safe rejects, reconciliation | Bad records isolated; raw preserved |
| Curated | Declared aggregate grain | Data product owns interpretation | Quality gates, lineage, atomic publication | Old good version remains visible |
| Serving | Consumer projection/version | Serving/consumer owner | Query/access limits, cache versioning | Consumer/load isolated |
| Control plane | Desired state and metadata | Platform/governance owners | Strong identity, audit, review, backup | Fail closed for unsafe policy changes |

Layers are contracts. Creating `bronze`, `silver`, and `gold` directories without
authority, quality, or publication behavior provides labels rather than an
architecture.

## Dependency direction and tenancy

Consumers depend on curated contracts, not raw paths. Transformations depend on
versioned raw input and schemas, not dashboard implementation. Producers depend
on collection contracts, not warehouse tables. Control-plane components govern
data-plane work but do not redefine domain facts.

Separate tenant identity in authorization, storage namespace, compute quota,
metadata, encryption scope where required, and telemetry. Logical partitions are
not sufficient isolation when a shared administrator, key, catalog, or worker
can cross them. Choose isolation proportional to confidentiality and blast radius.

## Failure model and recovery

| Failure | Boundary that contains it | Recovery owner/action | Consumer-visible behavior |
| --- | --- | --- | --- |
| Malformed/oversized payload | Collector | Reject safely; rate-limit; retain minimal audit | No partial curated effect |
| Poison record crashes parser | Validated boundary | Quarantine under rule; fix/replay raw | Version delayed or approved exclusion visible |
| One tenant floods input | Admission/quota boundary | Throttle tenant; protect shared reserve | Affected tenant delayed, others within objective |
| Partial transform output | Staging/publication boundary | Remove/reuse safe staging; rerun | Prior complete version remains |
| Bad quality rule/config | Versioned control boundary | Roll back rule; re-evaluate affected interval | Publication held/corrected |
| Curated permission leak | Access boundary | Revoke, audit, rotate as needed, incident response | Access stopped; impact assessed |
| Regional/platform loss | Storage/control failure domain | Restore/fail over per RPO/RTO | Explicit unavailable/stale state |

Containment is not recovery. Reconcile accepted identities, published aggregates,
permissions, and affected consumers after the failing component returns.

## Security, privacy, and governance

Threats include spoofed clients, injection into parsers or SQL, decompression
bombs, path traversal, unsafe deserialization, cross-tenant reads, credential
leakage, overly broad exports, and sensitive logs. Apply authenticated workload
identity, strict parsers and size bounds, parameterized SQL, least privilege,
encryption, network controls, secret rotation, egress restrictions, and audit.
Minimize collection and define retention/deletion before replication. Quarantine
is more restricted than ordinary curated data, not a dumping ground.

## Data quality, testing, and evidence

| Evidence | Dataset and environment | Procedure | Expected result | Result |
| --- | --- | --- | --- | --- |
| Architecture review | Shared paper scenario | Label owners, authority, contracts, trust, commit, and failure boundaries | Every component supplies a named behavior | Passed; documented above |
| Threat/boundary review | Paper data flow | Trace invalid, oversized, unauthorized, cross-tenant, and partial output cases | Control and containment point named | Passed by design; not executed |
| Negative access/fault tests | Real components with synthetic data | Attempt unauthorized reads and interrupt each commit | Denial and convergence match contract | Pending |
| Capacity isolation test | Representative multi-tenant load | Overload one workload | Other workloads stay within objective | Pending |

## Debugging guide

Start with consumer/version impact, then follow lineage and correlation IDs across
trust boundaries. Inspect authentication/authorization decisions, rate limits,
rejection reasons, manifests, quarantine counts, run attempts, publication state,
tenant resource usage, and catalog/policy versions. Do not copy raw payloads into
general logs. Mitigate at the narrowest boundary, preserve evidence, restore from
an authoritative version, and reconcile before reopening access or publication.

## Common pitfalls

### Pitfall: architecture by fashionable nouns

A lakehouse, streaming platform, or mesh does not state grain, owner, guarantee,
or recovery. Start with the requirement and show which component satisfies it.

### Pitfall: internal equals trusted

Internal producers can be buggy or compromised. Validate at ownership and
privilege changes, and authorize every workload identity.

### Pitfall: layers that only copy data

Every copy adds cost and governance burden. A layer should change a contract:
durability, validation, semantics, publication, or consumer isolation.

## Performance, capacity, cost, and operations

Each boundary adds latency, storage, network I/O, metadata, and on-call surface.
Estimate read/write amplification, file counts, catalog calls, concurrent jobs,
tenant quotas, and recovery capacity. Track per-boundary rates, rejected bytes,
queue age, quality outcomes, publication freshness, access denials, lineage gaps,
resource saturation, and unit cost with privacy-safe, bounded labels.

## Compatibility, migration, backfill, and delivery

Prefer replaceable boundaries: versioned schemas, immutable inputs, isolated
staging, contract-facing outputs, and catalog identities not hard-coded storage
paths. Introduce a new architecture path beside the old, replay a bounded range,
compare semantics and service indicators, migrate consumers, preserve rollback,
then decommission data and permissions. Avoid permanent dual-write authority.

## Engineering tradeoffs

The smallest current design is collector -> immutable raw -> daily validated
aggregate -> governed table. Add a broker for independent replaying consumers or
bursty decoupling; a serving cache for measured query latency/concurrency; stronger
tenant isolation for demonstrated risk; and more layers only for explicit
contracts. Every addition must include owner, SLO, failure model, and retirement path.

## Working example

The architecture diagram, pattern decision, layer contract, and threat review are
complete conceptual evidence. Real access, fault, and isolation tests are pending.

## Knowledge check

1. Mark all trust and commit boundaries in the diagram and explain why each exists.
2. Predict the blast radius if staging and curated paths share one mutable location.
3. Diagnose why a three-layer design still exposes partial data.
4. Design isolation for two tenants with different confidentiality requirements.
5. Remove one component from the proposed architecture and state the lost guarantee.

## Key takeaways

- Patterns are reusable tradeoffs, not complete solutions or maturity levels.
- Trust changes require validation, authorization, bounds, and observable policy.
- Layers need distinct contracts; copies without responsibility create risk.
- Containment limits blast radius; reconciliation proves recovery.
- Begin with the simplest design and add components for measured requirements.

## Resources

- [NIST Zero Trust Architecture, SP 800-207](https://csrc.nist.gov/pubs/sp/800/207/final)
- [C4 model for visualising software architecture](https://c4model.com/)
- [AWS Well-Architected: Data Analytics Lens](https://docs.aws.amazon.com/wellarchitected/latest/analytics-lens/analytics-lens.html)

## Related topics

- [Data lifecycle, control plane, and data plane](02-data-lifecycle-control-plane-and-data-plane.md)
- [Sources, sinks, authority, and derived data](05-sources-sinks-authority-and-derived-data.md)
- [First end-to-end data pipeline](08-first-end-to-end-data-pipeline.md)

## Completion checklist

- [x] Architecture patterns, boundaries, tenancy, and dependency direction explained
- [x] Requirements, grain, authority, owners, trust, and non-goals explicit
- [x] Failures, containment, recovery, security, observability, cost, and migration covered
- [x] Paper review separated from negative, fault, and isolation evidence
- [ ] Real-component security, fault, capacity, and recovery tests executed
