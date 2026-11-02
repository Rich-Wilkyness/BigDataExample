# Richard Wilkerson: pitch and project notes






Volume - Velocity - Variety - Veracity - Value


Updated: 2026-10-27. Personal interview preparation using the supplied [résumé](resume_v1.md) and project notes. The short pitch introduces the candidate’s overall background; the recent-job narrative explains the role and contributions. This is separate from the curriculum and standalone interview question banks.

**Clarification from Richard:** The résumé is made up. The employment narrative and responsibilities in this file are therefore hypothetical practice material, not verified professional experience. Earlier references to “actual work,” “recollection,” or “details to recover” predate this clarification. The design choices below explain a coherent example system; they do not establish what PayPal implemented or what Richard personally delivered. Use hypothetical language for this scenario and distinguish any future independent implementation from employment history.

## Short pitch: “Tell me about yourself”

Aim for about 30–40 seconds. Introduce your background, strengths, and direction, then pause. First-person wording below is a fictional role-play script based on the supplied profile.

“Hi, I’m Richard Wilkerson. I’m a data engineer with a background across financial services, retail, and other industries. My core strengths are Python, SQL, and Spark, with a focus on building reliable cloud data pipelines and making data useful for business teams. Most recently, I’ve been working as a Lead Data Engineer at PayPal. I enjoy staying hands-on while contributing to technical design and mentoring engineers, and I’m looking for a role where I can bring those strengths to the team.”

## Recent-job narrative: “Tell me about your most recent role”

Aim for about two minutes. Explain the business context, your scope, the main work, and its purpose. This fictional role-play assumes participation in the migration. Connect the assigned pipeline contributions to the broader program’s reported results; the technical notes below provide follow-up practice.

“In my most recent role as a Lead Data Engineer at PayPal, my work covered two main areas: migrating existing data pipelines to Google Cloud and developing new pipelines supporting the Buy Now, Pay Later mobile and web application.

On the migration side, I contributed to consolidating fragmented analytics platforms into BigQuery to improve scalability and support AI.

My scope was the assigned pipelines: transformation logic, Airflow orchestration in Cloud Composer, validation, and publication of curated datasets in BigQuery. I coordinated with upstream owners and downstream consumers as we worked through successive pipelines.

Across the broader migration program, PayPal reported queries running 2.5 to 10 times faster and data available for model training being 16 times fresher, while maintaining business operations without downtime or customer impact. My contribution was delivering the assigned pipelines as part of that effort.

For BNPL, I helped develop an acquisition-funnel pipeline that processed application-event data so Marketing could understand how far users progressed through the application process and where they dropped off. I also helped implement configuration-driven controls that accounted for upstream feature availability by country, product, and application screen, so processing and reporting reflected the active application experience.

My hands-on work included PySpark processing on Dataproc and SQL in BigQuery. Alongside implementation, I contributed to technical design, code reviews, mentoring, and production support. The focus was delivering dependable datasets that downstream teams could use for reporting and analysis.”

## Migration article: context for follow-up questions

Source: [PayPal-authored Google Cloud article](https://cloud.google.com/blog/products/databases/paypals-historic-data-migration-is-the-foundation-for-its-gen-ai-innovation), published February 27, 2026; reviewed October 27, 2026.

| Topic | Published program context |
| --- | --- |
| Why migrate? | Growth and acquisitions fragmented customer data across Teradata, Hadoop, Redshift, Snowflake, and other systems. |
| Customer example | Online PayPal sales and local Venmo transactions were difficult to combine into one merchant view. |
| Why BigQuery? | Independently scalable storage and compute, plus AI integration. |
| How? | Stakeholder alignment, dependency mapping, modernization decisions, security/governance rules, automation, progress dashboards, and FinOps tracking. |
| Results | Faster queries, fresher training data, and uninterrupted operations, as summarized in the narrative. |
| AI direction | Potential applications included fraud prevention, merchant financial insights, and risk assessment. |

**Practice assumption and attribution:** Richard is treating this scenario as participation in the migration. The narrative therefore describes assigned pipeline work as a contribution to that program and attributes the published metrics to the broader effort. The article’s February 2026 publication and the résumé’s March 2026 start remain a chronology mismatch to resolve if the practice materials need a consistent timeline. The 16× metric concerns training-data freshness, not training speed or accuracy. AI opportunities are future directions, not personally delivered outcomes.

Keep the spoken narrative to the motivation and reported results. Use these notes if asked about the wider program’s approach; they do not establish personal ownership of stakeholder alignment, automation, governance, or FinOps.

## Airflow and Cloud Composer: personal reminder

Apache Airflow is the workflow orchestration software. Cloud Composer is Google Cloud’s managed service for running Airflow. “Airflow running in Cloud Composer” describes the relationship clearly; naming both does not imply two independent orchestration systems or an old/new pipeline split.

Google’s current documentation calls the service Managed Service for Apache Airflow, formerly Cloud Composer. Using the name used during the engagement is appropriate.

Airflow coordinates tasks: what runs, in what order, under which conditions, and with what retry behavior. In the example architecture, PySpark performs the event transformations and BigQuery stores the analytics datasets. Airflow is not the application’s feature-flag service.

## Answering: “How did you use configuration and feature flags?”

### Short answer based on the work described

“The upstream application had feature flags that changed which countries, products, or screens were active. Our pipeline controls accounted for those settings when deciding which downstream processing should run. The important distinction was whether missing activity was expected because a feature was disabled or unexpected because data had not arrived. That helped us avoid treating intentional gaps as failures.”

This states the purpose Richard described. Before adding details about where configuration lived, how it was refreshed, or which Airflow operators implemented the controls, recover those details from actual work artifacts or recollection.

### What configuration-driven means

The processing code reads settings instead of requiring a separate code change for every market or product combination. The application feature flag controls the user experience; the pipeline’s configuration represents the availability and processing rules it needs to follow. Those settings could come from an approved flag export, a configuration table, or a versioned file. The actual storage and synchronization mechanism is still to confirm.

Illustrative settings:

| Country | Product | Acquisition enabled | Eligibility screen enabled |
| --- | --- | --- | --- |
| DE | BNPL | No | No |
| FR | BNPL | Yes | No |
| GB | BNPL | Yes | Yes |

These are invented teaching examples, not actual PayPal settings. Country/product settings alone may be insufficient if a rollout also varies by application version, cohort, or session. The configuration needs to represent the scope that actually governed the events.

### Example processing flow

```text
Airflow task reads configuration for the processing period
                         |
              Determines eligible scopes
                         |
              Starts PySpark processing
                         |
        PySpark applies the appropriate funnel rules
                         |
                 Validates results
                         |
              Publishes BigQuery tables
```

This is a possible implementation to understand, not a confirmed reconstruction. A useful design is to use a consistent configuration snapshot throughout a run and retain effective dates for historical reprocessing.

### Scenario walkthrough

| Scenario | Interpretation | Possible handling |
| --- | --- | --- |
| DE acquisition disabled; no new acquisition events | Expected inactivity | Skip affected acquisition processing or mark the scope inactive; continue other countries. |
| DE acquisition enabled; expected events absent past the agreed deadline | Unexpected gap requiring investigation | Check delivery, freshness, and expected activity; alert or hold affected publication as required. |
| One product disabled within DE | Only that country/product combination is inactive | Apply the gate to that combination; continue unaffected combinations. |
| Eligibility screen bypassed in FR | The valid application journey has changed | Use the applicable funnel path rather than requiring an event the app no longer generates. |
| Configuration cannot be read | Availability expectations are unknown | Follow an explicit fallback policy; do not interpret configuration failure as every feature being disabled. |

Missing country or product values do not usually break a group-by or filter over existing rows. However, a successful job can still produce incomplete reporting, retain stale outputs, or misclassify drop-off. Absence of events is not itself evidence that a feature was disabled.

Example: `Start → Eligibility → Details → Submit` becomes `Start → Details → Submit` when a screen is bypassed. A funnel that still requires Eligibility can incorrectly classify successful attempts as drop-offs. Adapting funnel logic is a possible requirement; confirm whether Richard’s team owned that calculation or passed availability information to the analytics team.

Disabling new acquisition does not necessarily disable servicing, repayments, or delayed events from earlier activity. Apply controls to the affected event types and time periods. Preserve valid historical and late-arriving data according to the agreed rules.

### Where the tools fit

| Component | Possible responsibility |
| --- | --- |
| Configuration source | Record availability, scope, effective dates, and processing rules. |
| Airflow in Cloud Composer | Read settings at runtime, select branches, skip affected tasks, and coordinate validation and publication. |
| PySpark on Dataproc | Process eligible scopes and apply event-level transformation rules. |
| BigQuery | Store curated results and availability/status metadata for consumers. |
| Quality checks and monitoring | Compare expectations with observed data and surface unexpected gaps. |

Airflow supports branching and conditional skipping. Downstream trigger rules must account for expected skips. If one Spark job processes all countries, conditional processing inside that job can be more appropriate than creating an Airflow branch for every country. Exact operators and DAG structure remain unconfirmed.

Use “skip processing,” “pause processing,” “hold publication,” and “change funnel rules” precisely: they describe different actions. Do not claim the entire pipeline stopped if only one scope or downstream task was affected.

## Migration ownership and relationships with other teams

### Working ownership boundary

Our team’s role was pipeline/domain engineering for assigned workloads. As we completed one pipeline migration, we moved to another. This was a contribution within the enterprise migration program.

Our work started at the agreed source interface: the source tables, landed files, or event feed made available for the assigned pipeline. The exact ingestion boundary should be confirmed separately for each pipeline.

Our work covered the assigned transformation logic, task orchestration, validation, and publication of curated datasets. Publication means making validated tables or views available under the agreed delivery contract. It does not automatically include building dashboards or owning every consuming application.

Our delivery boundary was the published dataset and agreed handoff to consumers. Pipeline ownership could continue through monitoring, incident support, and changes after that handoff; publication does not imply all operational responsibility ended.

### Team relationships to explain

The following is an ownership model to compare with the actual engagement, rather than a verified PayPal organization chart.

| Team | Their responsibility | Our relationship |
| --- | --- | --- |
| Source/application owners | Application behavior, emitted events, source schemas, and feature flags | Agree on source contracts, availability signals, schema changes, and expected activity. |
| Ingestion/platform teams, where separate | Shared source extraction, landing, infrastructure, permissions, and common tooling | Use the agreed inputs and platform services; coordinate dependencies and access. |
| Our pipeline/domain engineering team | Assigned transformations, orchestration, technical validation, and curated publication | Implement and migrate the pipeline, investigate failures within our scope, and coordinate delivery. |
| Analysts/analytics engineers/Marketing | Reporting definitions, consumption models, dashboards, and business interpretation as assigned | Agree on output contracts, validate usability, and support consumer testing. |
| Migration coordination and business owners | Cross-team sequencing, cutover approval, and acceptance as assigned | Supply reconciliation evidence and readiness information; coordinate switchover and dependencies. |

### Follow-up answer: “Did you own the pipeline end to end?”

Use this if the boundary above matches the actual work:

“For our assigned pipelines, our team owned transformation logic, orchestration, validation, and publication of curated datasets. We coordinated with source and platform teams for upstream dependencies and with analytics teams for downstream acceptance. Our scope was the assigned pipeline and its data contract within the broader migration program.”

For migration validation, prepare one actual example: what legacy output was compared with what new output, which keys and measures mattered, what tolerances applied, and who accepted the result. Row counts alone do not establish business equivalence. Reconciliation, parallel runs, cutover procedures, and legacy retirement are possible migration activities; claim each only if personally supported.

## Application-event data and Datadog

Use “application-event data” in the pitch. Datadog was discussed as providing live visibility, but the pipeline’s exact event source has not been established. Events could have reached Datadog and the data platform through parallel routes, or the pipeline could have extracted events from Datadog. Datadog’s RUM API makes extraction possible; it does not prove that architecture was used here.

The business value described is helping Marketing understand application progression and drop-off. A recorded error near a drop-off supports investigation but does not establish that the error caused abandonment. Recover the ingestion endpoint or source configuration before naming Datadog as the source.

## Results and enterprise scale

PayPal’s public migration account describes an approximately 400 PB estate across multiple systems and more than 300 PB migrated. Those are enterprise program figures, not the volume owned by this team or Richard personally. Keep them out of the short pitch unless enterprise context helps; do not describe this as personally migrating 400 PB.

Current outcome language can focus on delivered capabilities: migrated pipelines, published curated datasets, acquisition-funnel visibility, and feature-aware processing. Quantified improvements require supporting evidence. Useful evidence to recover includes assigned pipelines completed, reconciled datasets, consumers accepting cutover, a real gating incident, and measurable runtime or manual-effort changes.

## Details to recover before deeper technical interviews

- Exact contract title, dates, personal leadership responsibilities, and team size.
- One migrated pipeline’s source platform, input interface, transformations, target tables, validation, and handoff.
- Whether ingestion was owned by this team or supplied by another team for each example.
- Configuration location, refresh method, effective dates, and behavior when configuration was unavailable.
- Whether gates skipped tasks, stopped jobs, held publication, or changed transformation rules.
- Whether funnel definitions were owned by this team or downstream analytics teams.
- Actual event identifiers, delivery frequency, late-event handling, and duplicate handling.
- Exact Datadog role and the pipeline’s ingestion source.
- One defensible result with a concrete example; add numbers only when supported.

## Reference sources

- [Google Cloud: Managed Service for Apache Airflow documentation](https://docs.cloud.google.com/composer/docs) — Composer/Airflow relationship and current service naming.
- [Apache Airflow: DAGs and control flow](https://airflow.apache.org/docs/apache-airflow/stable/concepts/dags.html) — branching, skipping, and trigger rules; use the installed version’s documentation for implementation.
- [Google Cloud: Migrate data pipelines](https://docs.cloud.google.com/bigquery/docs/migration/pipelines) — pipeline migration and orchestration dependencies.
- [PayPal-authored enterprise migration account](https://cloud.google.com/blog/products/databases/paypals-historic-data-migration-is-the-foundation-for-its-gen-ai-innovation) — published enterprise scale, not evidence of individual responsibilities.
- [Datadog: Export RUM events and graphs](https://docs.datadoghq.com/real_user_monitoring/explorer/export/) — programmatic event retrieval capability.

These sources informed the preceding discussion. Public documentation supports product capabilities and public program claims; it does not verify the internal implementation or individual ownership described in interview preparation.



datadog gives us data on the pipeline, throughput, number of shards, technical on infrastructure

airflow is a scheduler and decides if a task gets scheduled based on parameters from upstream applications
- so we decide that certain pipeline paths are not taken based on country specific regulatory compliance

## Teacher clarification: kill-switch and quality-gating narrative

### Practice narrative

The following retains the proposed narrative as a fictional role-play script. First-person wording is part of the exercise and is not an employment claim.

“Within our pipeline engineering work, one area I contributed to was a country-aware kill-switch and circuit-breaker framework.

The problem was that an upstream job completing successfully wasn’t enough to establish that downstream processing should proceed. We also needed to account for country-specific configuration, application feature flags, and upstream data quality results.

My contribution was implementing and enhancing the pipeline controls that enforced those decisions through Airflow. The kill-switch side supported intentionally disabling affected processing paths, while the quality-gating side prevented downstream propagation when upstream checks breached the configured thresholds.

Airflow served as the orchestration layer: it checked the required conditions and controlled whether dependent tasks could proceed. The quality checks could run separately; the framework used their results to enforce the gate.

The capability we delivered was controlled downstream processing based on both business configuration and data readiness.”

For a truthful design discussion, introduce this as “In a hypothetical country-aware pipeline, I would…” rather than describing an invented production delivery.

### Two reasons to block processing

| Reason | Meaning | Example |
| --- | --- | --- |
| Policy or feature restriction | Processing is intentionally disabled for a scope. | A country/product combination is disabled by an authorized configuration change. |
| Quality failure | Processing is enabled, but input data fails the agreed checks. | A completeness or reconciliation check fails for the relevant batch. |

Country configuration can represent regulatory restrictions, operational decisions, or rollout settings. An approved policy owner supplies regulatory decisions; the pipeline engineering team implements their enforcement. A disabled product is not automatically evidence of a regulatory restriction.

### Sensor explanation and decision flow

A sensor waits for a condition, such as a validation result becoming available. A normal Python sensor returning `False` means keep waiting until the condition is met or a timeout occurs; it does not mean permanently disable a country. Deliberate disablement and known validation failures need explicit handling.

```text
Is processing enabled for this scope?
    No  → Skip or block the affected path
    Yes → Has upstream validation completed?
              No  → Wait, subject to a deadline
              Yes → Did validation pass?
                        No  → Block affected downstream tasks
                        Yes → Continue
```

Practice explanation: “The sensors check readiness conditions or validation status. The workflow distinguishes data that is not ready yet from data that has completed validation and failed. Configuration determines whether the processing path is eligible to run in the first place.”

Airflow evaluates task dependencies and configured control logic; it does not automatically understand upstream flags or compliance policy. Sensors, tasks, and configuration integrations must implement those checks. Blocking future tasks also does not terminate an independently running streaming job.

### Scenario for explaining the behavior

Hypothetical example: A country/product path is enabled, but its upstream dataset fails a completeness check. The gate prevents the affected downstream processing from proceeding. Separately, if that country/product path is intentionally disabled through configuration, the workflow treats it as a configuration decision rather than an unexpected data failure.

Unaffected countries can continue only if processing and publication are isolated at the appropriate scope. A TaskGroup organizes tasks visually; it does not by itself establish failure or data-write isolation. Blocking publication preserves a previous dataset only if writes and publication are designed to retain it. Retained data must be identified as stale rather than presented as a fresh successful delivery.

## Hypothetical design choices for deeper practice

These are explicit choices for an educational system based on the scenario, not recovered facts about an employer. They provide answers to the ownership, signals, enforcement, and recovery questions without inventing personal experience.

### Ownership

Assume the domain team enhances a shared gating pattern for its assigned pipelines. The domain engineer implements the gate tasks, integrates configuration and validation results, adds run-status records, and coordinates output contracts. Source teams own event emission; approved business/policy owners authorize restrictions; platform engineers operate the shared Composer environment. Analytics partners help define the meaning of funnel measures.

This scope supports a discussion of implementing and enhancing controls. “Architected” would require actual design responsibility and evidence of the decisions made; a title alone does not establish that responsibility.

### Signals and configuration

Use a control dataset in BigQuery for this example, alongside the analytics platform already discussed. Store versioned processing rules with country, product, pipeline path, effective interval, enabled state, reason, and an audit reference. Application feature settings arrive through a hypothetical approved export; the pipeline does not infer flags from missing events. Policy restrictions and product availability remain distinct inputs.

Store validation results separately, keyed by pipeline, country, product, batch identifier, and processing interval. Each result identifies a check, its observed value, threshold, status, and completion time. The gate must match the intended batch rather than accepting an old passing result. Freeze the ordinary configuration version for reproducibility, while rechecking an emergency administrative disablement before publication. An emergency disablement governs new publication even during a historical rerun.

### Enforcement

For clarity, use one DAG run per country/product/processing interval in this example. This is a design choice, not a requirement or a claim about the original scenario.

| Condition | Example action |
| --- | --- |
| Explicitly disabled scope | Record `DISABLED` as an application-level status and skip the processing path; notify according to policy. |
| Configuration absent or unreadable | Fail the gate and alert; do not proceed on an assumed enabled state. |
| Validation result pending | Sensor waits for completion, with a finite deadline. |
| Validation completed and failed | Fail the quality gate immediately and block dependent transformation/publication tasks. |
| Required validation passed | Continue eligible tasks. |
| Emergency disablement detected before publication | Block publication for that scope and record the reason. |

`DISABLED` is a custom audit value, not a built-in Airflow task state. Configure downstream dependencies so failed or intentionally skipped gates cannot accidentally permit publication; cleanup and notification tasks may need different trigger rules. Separate runs improve control boundaries, but shared destination writes and global reports still need explicit isolation and completeness rules.

### Quality checks

Use event-level contract checks such as required identifiers, valid timestamps, and duplicate event IDs. Check completeness against an upstream batch manifest or agreed source counts where available. Reconcile submission events against backend application records only after defining matching identifiers, time windows, late-arrival allowances, and tolerances. Zero events alone do not prove failure. Thresholds are agreed contracts, not arbitrary numbers added for a résumé.

### Recovery and publication

Choose controlled manual recovery for the example rather than claiming a fully automatic stateful circuit breaker. The operator investigates the failed checks, corrects or replaces the input, produces validation results for the corrected batch, and reruns the affected gate and downstream tasks. An authorized owner must separately remove any administrative restriction; data passing validation does not override a kill switch.

Write candidate outputs to staging first and publish only after the required checks pass. Use a repeatable replacement or merge strategy keyed to the scope and batch so reruns do not append duplicates. Track published batch and freshness separately from run failure status. This is a publication design to implement and verify, not a guarantee provided by an Airflow sensor.

A gate that blocks on validation failure can be described precisely as a quality gate. A stateful circuit breaker additionally maintains an open/closed state and a defined recovery policy; automated half-open probing would be a further design choice. Do not imply those mechanisms exist merely because the résumé uses “circuit breaker.”

### Capability to demonstrate independently

An independent lab could demonstrate an enabled scope publishing, an intentionally disabled scope skipping, pending validation timing out, failed validation blocking publication, and a corrected batch rerunning without duplicates. No such lab was implemented or executed by this documentation update. Describe it as a proposed design until built and tested, and as an independent project afterward.

Reference: [Apache Airflow sensors](https://airflow.apache.org/docs/apache-airflow/stable/core-concepts/sensors.html) documents waiting, timeouts, and skip-on-timeout configuration. Operator names and behavior should be checked against the version used in any future lab.
