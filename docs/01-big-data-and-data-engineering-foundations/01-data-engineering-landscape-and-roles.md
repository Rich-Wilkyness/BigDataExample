# Data Engineering Landscape and Roles

> Status: Documentation complete  
> Level: Beginner  
> Applies to: Generic data engineering / Platform  
> Data scale: Local fixture through production estimate  
> Example status: Complete conceptual walkthrough  
> Evidence status: Boundary review  
> Last reviewed: 2026-09

## Overview

Data engineering is the design and operation of systems that move, store,
transform, and publish data with explicit meaning and dependable behavior. It
sits between producers such as applications and databases and consumers such as
analysts, dashboards, machine-learning systems, and other applications.

The durable subject is responsibility for data contracts, correctness,
recovery, and lifecycle. Team names and product boundaries vary by company.
This guide does not prescribe an organization chart or a particular tool stack.

## Learning objectives

After completing this guide, you should be able to:

- Distinguish data engineering, analytics engineering, platform engineering,
  data analysis, data science, ML engineering, and application engineering.
- Assign ownership for a dataset, pipeline, platform capability, and business
  definition without relying on job titles alone.
- Identify missing responsibility at a producer-to-consumer handoff.
- Explain how success is measured across role boundaries.
- Evaluate centralized, embedded, and platform/domain ownership tradeoffs.

## Prerequisites

Conceptual prerequisites are records, APIs, databases, and deployed services.
No executable infrastructure is required.

## Topical guide

1. Begin with outcomes and consumers, not a list of technologies.
2. Separate ownership of business meaning, data movement, and shared runtime.
3. Define contracts and escalation paths where responsibilities meet.
4. Measure the end-to-end result rather than each team declaring local success.

## Terminology

| Term | Meaning in this guide |
| --- | --- |
| Data product | A dataset or data-facing capability with named consumers, an owner, a contract, and lifecycle commitments |
| Data platform | Shared capabilities that let teams ingest, process, store, govern, observe, and serve data |
| Steward | Person or group accountable for business definitions, classification, and acceptable use |
| Pipeline owner | Team responsible for transformation behavior, operation, repair, and delivery |
| Contract | Producer-consumer agreement covering structure, semantics, compatibility, and service expectations |

## Requirements, scale assumptions, and invariants

The running scenario has an Android team producing `screen_viewed` events, a
product team consuming daily screen counts, and a data team operating the path.
Assume 100,000 daily active installations, 30 events per active installation,
and approximately 1 KiB per raw event: 3 million events and about 3 GiB/day
before compression and replicas. These are estimates to test the design, not
observations.

Invariants:

- The Android team owns what the event means and when it is emitted.
- The ingestion owner does not silently reinterpret producer fields.
- The analytical dataset declares its own grain and transformation version.
- A platform incident has a named responder; a semantic dispute has a named
  business owner.
- Every consumer-facing promise has one accountable owner, even when several
  teams contribute.

The estimates must be revised if measured event rates, payload distributions,
consumer concurrency, or retention policy differ materially.

## Mental model

Treat the system as a chain of contracts, not a relay race where responsibility
disappears after a handoff:

```text
Android producer -> ingestion -> raw dataset -> transformation -> curated dataset
       |                |             |                |               |
 event meaning     delivery       retained fact    derived logic   consumer contract
       \________________________ end-to-end outcome _______________________/
```

An Android analogy is an app feature crossing UI, domain, repository, and API
boundaries: each layer owns behavior, while the user experiences the whole
path. The analogy stops at data lifetime and fan-out. A historical dataset may
outlive multiple application versions and support consumers the producer never
calls directly.

## Data flow, ownership, and trust boundaries

| Boundary | Input contract | Authority and owner | Failure behavior | Trust level |
| --- | --- | --- | --- | --- |
| App to collection API | `screen_viewed` v1 | Android team owns event semantics | Retry safely or retain locally within policy | Untrusted network input |
| Collection to raw | Valid envelope plus receipt metadata | Ingestion team owns durable receipt | Reject/quarantine invalid input; alert on loss | Validated structure, untrusted meaning |
| Raw to curated | Versioned transformation | Data pipeline owner owns derived rows | Fail closed; preserve raw input for repair | Governed internal |
| Curated to dashboard | Daily metric contract | Product steward owns definition; pipeline owns delivery | Mark stale rather than imply freshness | Approved consumer access |
| Shared runtime | Deployment and service interfaces | Platform team owns availability and guardrails | Contain tenant failure; publish incident state | Privileged control boundary |

The raw accepted-event dataset is authoritative for what ingestion durably
received. The curated table is authoritative only for its defined analytical
interpretation.

## Role boundaries and collaboration

| Responsibility | Typical primary owner | Important collaborators |
| --- | --- | --- |
| Source transaction and event semantics | Application engineering | Product, data engineering, privacy |
| Reliable ingestion and transformation | Data engineering | Source owner, platform, consumers |
| Reusable runtime, identity, storage, deployment | Data platform engineering | Security, SRE, data teams |
| Governed SQL models and metric definitions | Analytics engineering | Domain steward, analysts, data engineering |
| Questions, interpretation, and decisions | Data analysis | Domain owner, analytics engineering |
| Experiments and statistical models | Data science | Domain experts, ML/data engineering |
| Training/serving systems and model operations | ML engineering | Data science, platform, application teams |
| Classification, retention, and permitted use | Data owner/steward | Legal, privacy, security, all implementers |

A title is not a control. Record the accountable team, support path, and service
expectations in the dataset catalog or equivalent maintained metadata.

## Record, job, and dataset lifecycle

The source owner evolves event semantics; the ingestion owner accepts and
retains valid versions; the pipeline owner deploys transformations, reruns and
backfills; the steward approves use and retention; the consumer owner detects
whether the result remains fit for its decision. Deletion must cover raw,
derived, cached, exported, and backed-up copies according to policy.

## Failure model and recovery

| Failure | Detection | Containment and recovery owner | Consumer behavior |
| --- | --- | --- | --- |
| Producer changes meaning without versioning | Contract and distribution checks | Producer rolls back or publishes compatible version | Metric held or marked unreliable |
| Platform is healthy but pipeline is stale | Freshness objective | Pipeline owner reruns from durable input | Dashboard shows last successful cutoff |
| Pipeline is timely but metric is wrong | Reconciliation and domain review | Data and metric owners repair and backfill | Corrected version is communicated |
| No team owns an export | Catalog/access review | Domain leader assigns owner or retires it | Access denied until governed |

Recovery is complete only after repaired output is reconciled and affected
consumers know which time range and version changed.

## Security, privacy, and governance

Role separation supports least privilege: producers should not gain warehouse
administration by emitting events, and analysts should not need raw personal
identifiers for aggregate metrics. Stewards classify fields, approve purposes,
and set retention; platform and pipeline owners enforce those policies. Logs and
quarantine data are still data products and must not become policy bypasses.

## Data quality, testing, and evidence

| Evidence | Dataset and environment | Procedure | Expected result | Result |
| --- | --- | --- | --- | --- |
| Responsibility review | Running scenario / paper design | Assign semantic, delivery, runtime, policy, and consumer owners | No promise or recovery step is ownerless | Passed; documented above |
| Scale arithmetic | Estimated workload | `100,000 * 30 * 1 KiB` | About 3 million events and 3 GiB/day | Passed as estimate |
| Real organization review | Production organization | Confirm teams, contacts, and escalation paths | Named accountable owners | Pending |

The review proves the example is internally assigned; it does not prove that a
real organization follows the model.

## Debugging guide

Start with the affected consumer and the last trustworthy dataset version. Use
event ID, ingestion batch/run ID, transformation version, and publication time
to traverse lineage. Decide whether the defect is semantic, data-plane,
control-plane, or consumer-side before paging a team. Preserve samples safely,
record the impacted interval, and require reconciliation before closure.

## Common pitfalls

### Pitfall: ownership by technology

“The Kafka team owns the events” confuses platform operation with business
meaning. Name separate owners for the broker, event contract, pipeline, derived
dataset, and business metric.

### Pitfall: successful jobs equal successful data

A green scheduler says code ran; it does not prove completeness or correctness.
Pair operational status with data-quality and consumer-facing indicators.

### Pitfall: a central data team owns every decision

Centralization can standardize operation but cannot manufacture domain meaning.
Keep semantic accountability with a knowledgeable domain owner and make the
handoff explicit.

## Performance, capacity, cost, and operations

Organizational boundaries affect incident latency and platform utilization.
Track time to detect, time to identify the owner, time to restore, freshness,
failed records, consumer impact, and cost by workload. Avoid unbounded metric
labels such as raw `event_id`. Capacity and spend remain shared outcomes even
when the platform provides quotas and the domain chooses volume and retention.

## Compatibility, migration, and delivery

Contract changes use expand/migrate/contract: accept old and new forms, migrate
producers and consumers, reconcile both paths, then retire the old form after
its retention and replay window. The source owner cannot declare migration
complete while supported consumers still depend on the old contract.

## Engineering tradeoffs

| Model | Strength | Risk | Prefer when |
| --- | --- | --- | --- |
| Central data team | Consistent standards and scarce expertise | Queueing and weak domain context | Organization is small or capability is forming |
| Embedded data engineers | Close domain feedback | Duplication and inconsistent controls | Domains are distinct and platform guardrails exist |
| Shared platform plus domain ownership | Reuse with local accountability | Interface and governance investment | Multiple domains need autonomy at scale |

## Working example

The role and boundary walkthrough above is complete conceptual evidence. Python,
SQL, tests, and real runtime evidence are planned in later curriculum areas.

## Knowledge check

1. For a failed daily product metric, assign owners for meaning, source emission,
   ingestion, transformation, runtime, access policy, and consumer response.
2. Diagnose why a successful orchestration run can still produce bad data.
3. Design an escalation path for a breaking event change discovered after three
   days of publication.
4. Modify the scenario to add an ML feature consumer. Which responsibilities
   change, and which do not?

## Key takeaways

- Data engineering owns dependable data behavior, not merely data movement.
- Ownership is assigned per guarantee and boundary, not inferred from job title.
- Semantic, pipeline, platform, governance, and consumer responsibilities differ.
- End-to-end consumer outcomes require evidence across team boundaries.

## Resources

- [DAMA International: Data Management Body of Knowledge](https://www.dama.org/cpages/body-of-knowledge)
- [Google SRE: Monitoring Distributed Systems](https://sre.google/sre-book/monitoring-distributed-systems/)
- [Team Topologies](https://teamtopologies.com/key-concepts)

## Related topics

- [Data lifecycle, control plane, and data plane](02-data-lifecycle-control-plane-and-data-plane.md)
- [Sources, sinks, authority, and derived data](05-sources-sinks-authority-and-derived-data.md)
- [Data architecture patterns and trust boundaries](07-data-architecture-patterns-and-trust-boundaries.md)

## Completion checklist

- [x] Durable concept, mental model, roles, and non-goals explained
- [x] Grain, owners, consumers, sources of truth, and trust boundaries identified
- [x] Scale, service, privacy, retention, and cost concerns introduced
- [x] Failure, recovery, observability, compatibility, and migration addressed
- [x] Conceptual evidence recorded with limitations
- [x] Practical prediction, diagnosis, design, and modification exercises included
- [ ] Real organizational ownership and escalation paths verified

