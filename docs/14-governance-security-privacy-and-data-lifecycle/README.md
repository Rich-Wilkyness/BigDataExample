# 14 Governance, Security, Privacy, and Data Lifecycle

> Area status: Documentation complete; executable governance evidence planned  
> Level: Beginner to Senior data engineering  
> Applies to: Batch / Streaming / Storage / Warehouses / Data platforms  
> Reference scenario: Classified mobile-event data with governed access, safe analytics, deletion, and audit workflows  
> Evidence boundary: Documentation and current primary-source review; no policy engine, key service, deletion workflow, or production control executed yet  
> Last reviewed: 2026-09

## Purpose

Governance assigns decisions and accountability to data; security constrains who
and what can act; privacy constrains why personal data is processed and the harm
that processing can create; lifecycle controls constrain how long every copy
exists. These are connected guarantees, not four review checklists performed
after a pipeline is built.

Android permissions are a useful first analogy: declaring a permission does not
prove correct runtime use, and granting it once should not give every component
unlimited authority. The analogy stops at the data platform. Analytical copies
outlive app releases, identities include workloads and vendors, one field can be
combined with other datasets, and deletion must converge across distributed
derived state, archives, indexes, and evidence systems.

This area develops a vendor-neutral control system from ownership and discovery
through privacy, authorization, cryptography, safe data, deletion, audit, tenant
isolation, and governance operations. It teaches engineers to turn policy into
enforceable boundaries and verifiable outcomes. It does not provide legal advice
or select a catalog, identity provider, key manager, policy engine, or cloud.

## Prerequisites

- Requirements, trust boundaries, and scale estimates from [Area 01](../01-big-data-and-data-engineering-foundations/README.md).
- SQL and Python boundary behavior from [Area 02](../02-python-for-data-engineering/README.md) and [Area 03](../03-sql-and-analytical-querying/README.md).
- Storage copies and metadata from [Area 04](../04-data-storage-files-and-serialization/README.md), identity and semantics from [Area 05](../05-data-modeling-and-business-semantics/README.md), and source contracts from [Area 06](../06-data-ingestion-and-source-integration/README.md).
- Replay and repair from [Area 07](../07-batch-processing-and-etl-elt/README.md), distributed failure from [Area 08](../08-distributed-systems-foundations/README.md), and publication boundaries from [Area 11](../11-warehouses-lakes-lakehouses-and-serving-systems/README.md).
- Workflow identity and metadata from [Area 12](../12-workflow-orchestration-and-transformation-management/README.md) and evidence design from [Area 13](../13-data-quality-contracts-and-testing/README.md).
- No third-party package, service, or cloud account is required for this documentation pass.

## Learning path

1. [Data ownership, stewardship, catalogs, and lineage](01-data-ownership-stewardship-catalogs-and-lineage.md) establishes accountable decisions and discoverable provenance.
2. [Classification, personal data, and purpose limitation](02-classification-personal-data-and-purpose-limitation.md) connects data meaning and intended use to privacy risk.
3. [Identity, RBAC, ABAC, and least privilege](03-identity-rbac-abac-and-least-privilege.md) turns allowed purposes into decisions for humans and workloads.
4. [Encryption, secrets, keys, and credential lifecycle](04-encryption-secrets-keys-and-credential-lifecycle.md) protects data and credentials without confusing encryption with access control.
5. [Masking, tokenization, and safe nonproduction data](05-masking-tokenization-and-safe-nonproduction-data.md) reduces disclosure while preserving only necessary utility.
6. [Retention, deletion, legal holds, and data-subject workflows](06-retention-deletion-legal-holds-and-data-subject-workflows.md) makes end-of-life behavior explicit and testable.
7. [Audit, policy enforcement, and compliance evidence](07-audit-policy-enforcement-and-compliance-evidence.md) demonstrates what policy and controls actually did.
8. [Tenant isolation, abuse, supply chain, and governance operations](08-tenant-isolation-abuse-supply-chain-and-governance-operations.md) operates the control system under adversarial and organizational failure.

## Shared reference scenario

```text
mobile producers -> raw restricted events -> governed validated events
                         |                         |
                  identity map/token vault        +-> purpose-approved metrics
                         |                         +-> restricted support view
                         v                         +-> safe nonproduction fixture
                  deletion subject map

catalog + lineage: describes every dataset, owner, class, purpose, and copy
policy plane:      evaluates identity, purpose, data class, tenant, and time
evidence plane:    records decisions, access, changes, deletion, and exceptions
```

| Boundary | Grain and authority | Classification | Default access/lifecycle |
| --- | --- | --- | --- |
| Raw event | One received envelope; ingestion is copy owner, producer owns meaning | Restricted; may contain personal identifiers and payload surprises | Workload-only, short hot retention, quarantined fields protected |
| Subject map | One scoped subject-to-event identity association | Highly restricted personal data | Privacy workflow only; separately keyed and audited |
| Governed event | One accepted logical event per `tenant_id,event_id` | Field-level classes and approved purposes | Analysts use approved columns/views, not raw identifiers |
| Daily metric | One tenant, UTC date, product, and metric version | Internal unless small groups or joins raise risk | Consumer roles; minimum useful retention |
| Audit decision | One actor/action/resource/policy decision | Confidential security evidence | Append-oriented, integrity protected, separately administered |
| Deletion case | One request scope and decision version | Highly restricted case data | Privacy operators; retained by an approved evidence schedule |

Starting design estimates are 3 million events/day (about 3 GiB encoded), 100
million retained governed events, 1,000 human and 200 workload identities, 100
tenants, 35 days of hot replay, and 30 derived datasets. These are estimates, not
measurements or policy decisions.

## Durable governance contract

Every governed dataset or processing purpose must answer:

- What is the record grain, authoritative source, owner, steward, consumers, and lineage?
- Which fields and combinations identify, harm, or materially affect a person or tenant?
- Which stated purpose permits collection, transformation, sharing, and retention?
- Which human or workload identity may perform which action, under which context?
- Where are plaintext, keys, tokens, secrets, cached results, logs, exports, and backups?
- What retention rule, deletion identity, legal hold, and proof applies to every copy?
- Which preventive, detective, recovery, and independent evidence demonstrates the guarantee?
- Which exception owner, expiry, compensating control, and incident path applies when policy cannot be met?

Policy metadata is versioned input to data processing. A label without enforcement
is documentation; enforcement without observable decisions is an unverifiable
claim; evidence collected by the same failing component is not independent proof.

## Evidence ladder and scope

| Evidence | What it can demonstrate | What remains unproven |
| --- | --- | --- |
| Ownership/classification review | Decisions, scope, and accountable approvers are explicit | Runtime enforcement or inventory completeness |
| Policy/static test | Expected decisions for known identities and resources | Integration with every storage/query path |
| Negative-access integration test | A named engine denies forbidden actions | Other engines, exports, caches, or administrator bypass |
| Lineage/inventory reconciliation | Known sources and derived copies are mapped | Undiscovered shadow data or runtime completeness |
| Key/secret rotation drill | Consumers survive rotation and old authority is revoked | Provider outage or compromise outside drill scope |
| Deletion/restore drill | Located copies converge after deletion and restore | Unknown copies or legally different obligations |
| Audit/control review | Decisions link to policy, identity, resource, and outcome | Real-world intent or evidence-system independence |
| Production review | Observed access, exceptions, drift, and response over time | Behavior outside observed threats and jurisdictions |

This pass provides mental models, SQL/Python sketches, decision tables, failure
models, procedures, and precise pending evidence. It does not claim legal
compliance, anonymity, cryptographic assurance, distributed isolation, or
production operation.

## Area completion checklist

- [x] Eight inventory guides authored in planned order
- [x] Ownership, classification, access, cryptography, safe data, lifecycle, audit, isolation, and operations covered
- [x] Grain, identity, purpose, trust, failure, recovery, scale, cost, migration, and evidence boundaries explicit
- [x] Primary standards and official guidance linked with review dates
- [x] Examples and executable evidence accurately marked Planned
- [ ] Catalog/lineage, policy, negative-access, key/secret, masking, and tenant-isolation evidence executed
- [ ] Deletion/restore, audit-integrity, incident, load, supply-chain, and production evidence executed

