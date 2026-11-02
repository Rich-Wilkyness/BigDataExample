# Citi Bike: guided incremental S3 → Glue → Redshift pipeline

> Status: Guided adaptation for the [Wednesday homework](../3.2_HW.md). Implementation TODOs remain learner-owned. This guide does not constitute a deployed or tested pipeline. Primary documentation reviewed: 2026-10-15.

## Overview and reading order

The target behavior is one accepted analytical observation per documented business key, even when a batch is retried. Raw captures remain available for recovery, and the completed checkpoint moves only after required downstream writes and checks succeed.

Read Part 1 of the homework first, then follow this guide one checkpoint at a time. Use the existing [capture reader](capture.py) and [event contract](contract.py) to understand the source before adapting them. The Monday Kinesis producer and its failure demonstration remain useful for learning retries, but the homework route below uses scheduled Lambda ingestion directly into S3. Kinesis and Firehose are not prerequisites for this route.

```text
Ingestion schedule → Lambda → S3 Bronze raw captures

Processing schedule → Step Functions Standard workflow
                       │
                       ├─ read completed checkpoint and freeze batch input
                       ├─ Glue Bronze-to-Silver, wait for completion
                       ├─ Glue Silver-to-Redshift landing, wait for completion
                       ├─ Redshift canonical → dimensions → fact → checks
                       └─ save completed checkpoint → successful completion
```

Use the existing [Wednesday follow-along files](../3.1-wed-citibike-step-functions-lab/README.md) as comparison material. Their accepted-batch ledger and reporting view differ from this assignment's completed checkpoint and physical fact/dimension requirements. Copying that workflow unchanged would leave these requirements unfinished.

## Learning objectives

- Distinguish the raw capture, selected processing batch, canonical observation, and fact-table grain.
- Select a bounded set of new input without transforming all history on each run.
- Explain recovery after each stage, including a failure after warehouse writes.
- Build and validate your own canonical and dimensional transformations.
- Separate Terraform provisioning evidence from pipeline execution evidence.

## Prerequisites and ownership

Use your own S3 bucket/prefixes, Glue jobs, Redshift schema, workflow, schedules, and Terraform state. Confirm access and resource ownership before execution. Reuse an existing resource only when its owner and lifecycle are clear. No AWS resources are created by reading this guide or running the existing local demonstration.

Keep the source contract, Python code, SQL, workflow definition, and Terraform configuration in Git. Store credentials, Terraform state, raw captures, and execution artifacts outside committed source. Choose one project directory for the new pipeline so the older streaming examples remain easy to trace.

## What to reuse and what to build

| Existing material | Reuse for | Homework adaptation still required |
| --- | --- | --- |
| [capture.py](capture.py) | GBFS feed discovery and raw response handling | Scheduled Lambda handler, full intended station set, S3 writes, logs |
| [contract.py](contract.py) | Validation, source-field preservation, identity reasoning | Explicit canonical key and conflicting-observation policy |
| [demonstrate-retries.py](demonstrate-retries.py) | Understanding repeat delivery and ambiguous outcomes | Warehouse replay and checkpoint recovery evidence |
| [PostgreSQL idempotency demo](sql/idempotency-demo.sql) | Seeing a repeated write leave one logical result | Redshift staging/merge logic; PostgreSQL `ON CONFLICT` is not the Redshift approach |
| [Glue streaming source template](glue-source.template.json) | Comparing streaming and batch sources | New bounded S3 batch reader; do not point this Kinesis template at S3 |
| [Policy notes](policies/README.md) | Trust versus permissions versus network access | Permissions for Lambda, both Glue jobs, workflow, schedules, and database users |
| [Wednesday incremental jobs](../3.1-wed-citibike-step-functions-lab/incremental/bronze-to-silver.py) | Studying bounded inputs and batch paths | Review metadata timing, late files, key semantics, and your own destination |

Create the following files as you reach each checkpoint. These are implementation TODOs, not files already supplied by this adaptation.

| Artifact to create in your project | Responsibility |
| --- | --- |
| `lambda/ingest.py` | Retrieve raw station status/information and publish an identifiable capture |
| `lambda/coordinate-batch.py` | Read completed progress, select/freeze batch inputs, and support safe recovery |
| `glue/bronze-to-silver.py` | Read selected Bronze objects, validate/transform, write one identifiable Parquet batch |
| `glue/silver-to-redshift.py` | Load only that batch into landing, retaining its batch ID |
| `sql/create-tables.sql` | Define landing, canonical, dimensions, fact, and checkpoint metadata |
| `sql/process-batch.sql` | Prepare unique source keys, merge canonical, load dimensions/facts, check and complete |
| `sql/data-quality-checks.sql` | Detect duplicate keys, invalid counts, and orphan references |
| `sql/analytics.sql` | Answer at least three useful business questions |
| `workflows/incremental.asl.json` | Order tasks, wait for completion, and route errors |
| `terraform/` | Manage workflow, schedules, and their IAM roles/policies; add other resources if chosen |
| `evidence/` | Document actual manual/automatic runs, replay, failure, checks, and checkpoint movement |

## Checkpoint 1 — define the data contract

**TODO:** Inspect one actual `station_status` response and its matching station-information metadata. Record the GBFS version and field names you will use. Keep `station_id` as a string. Distinguish polling time from station `last_reported` and feed update time.

Choose and document the canonical grain before writing SQL. One possible policy is one station observation per source report timestamp, with a stated rule for conflicting payloads at that timestamp. Another is one station per collected snapshot; it preserves repeated unchanged reports across different polls. These policies answer different questions. The existing content-derived `event_id` can change when content changes at the same timestamp, so it is not automatically equivalent to either policy.

**Checkpoint:** Explain which two captures should collapse into one canonical observation and which should remain separate. State how station metadata timing affects historical accuracy.

## Checkpoint 2 — scheduled Bronze ingestion

**TODO:** Adapt HTTP discovery/fetching into a Lambda handler that writes the raw source responses under a unique capture path. The local capture script selects a small sample; the homework collector must intentionally select its real coverage. Preserve source JSON rather than saving only transformed station rows.

Write a manifest after all required objects for a capture exist. Include capture ID, ingestion time in UTC, source/version, and object keys. Process published manifests so a partial capture does not look complete. A retry can leave more raw copies; downstream business identity must still prevent duplicate analytical results.

**Checkpoint:** Run ingestion manually first. Inspect saved raw objects and their manifest, then enable ingestion scheduling and observe a fresh capture without a manual invocation. An ingestion interval and a thirty-minute processing interval serve different purposes; document each.

## Checkpoint 3 — deterministic batch selection

**TODO:** Initialize a completed checkpoint at a documented collection boundary. Choose its clock explicitly. A capture-time checkpoint is distinct from a station event-time checkpoint, which needs event lateness handling.

At workflow start, fix the prior checkpoint, lookback-adjusted lower bound, exclusive upper bound, batch ID, input manifest/object list, and Silver path. Save that batch context so retries reuse the same intended work. Do not recompute the upper bound from the current time midway through recovery.

Use `[start, end)` boundaries consistently. If checkpoint time is capture time, select captures with that clock while keeping station event time for analysis. If it is event time, design source discovery so older events in newly received objects are still inspected. Partition pruning or a manifest index should avoid repeatedly listing/scanning the whole history.

**Checkpoint:** Show two consecutive input windows and identify the handling of a record exactly at their shared boundary. Explain what happens to a capture published after the manifest list was frozen. A two-hour lookback cannot recover arbitrarily late data; define a catch-up procedure.

## Checkpoint 4 — bounded Bronze-to-Silver

**TODO:** Accept batch context as Glue arguments. Read the intended raw objects, apply an explicit schema, flatten station rows, parse timestamps, and validate identifiers/counts. Resolve duplicates using your documented grain and conflict policy. Enrich with station metadata according to a stated temporal policy.

Write to an identifiable path such as `silver/observations/batch_id=<batch-id>/`. A batch directory alone does not make a write idempotent: decide how a failed/partial write is detected and safely rebuilt or published before downstream reads. Do not overwrite all Silver history.

**Checkpoint:** Read the published Parquet back and inspect its schema, count, timestamp range, key uniqueness, and batch identity. Explain your no-input policy: a verified empty interval can advance progress, while a missing required capture or malformed input should fail visibly.

## Checkpoint 5 — load only this batch into landing

**TODO:** Configure the second Glue job to read the published batch path and load Redshift landing with `batch_id`. Use a reviewed Glue connection or IAM-based mechanism and the required S3/network access. Avoid hardcoded credentials.

Landing may contain duplicate rows after an interrupted load and retry. Filter the intended batch and reduce it to one row per canonical key before merging. Do not assume Redshift enforces a declared unique constraint.

**Checkpoint:** Compare the Silver logical keys with the landing batch, not just whole-table row counts. Repeat a landing load and explain how canonical/Gold processing will absorb the replay.

## Checkpoint 6 — build canonical and Gold yourself

**TODO:** Use the small SQL walkthrough in [homework Part 1](../3.2_HW.md#3-idempotency-and-deduplication) to design your own canonical merge. Choose a deterministic conflict policy before accepting different values for the same business key.

Design at least two dimensions and one physical fact table. Station and date are possible dimensions; choose attributes and keys based on your analytical questions. Populate/resolve dimension rows before facts. Document whether station attributes use Type 1 current state or Type 2 history. Availability is a snapshot measure: summing it across time is not a count of trips or unique bikes.

**Checkpoint:** Write three business questions, then queries that answer them. Check fact grain, duplicate canonical/fact keys, null/invalid counts, and orphan dimension references. A view that simply repeats Silver is insufficient for this assignment.

## Checkpoint 7 — complete progress safely

**TODO:** Coordinate required warehouse changes, data-quality checks, and checkpoint advancement. One approach is a warehouse transaction that includes canonical/Gold changes and the completed checkpoint update, rolling back on failed checks. Ensure the chosen SQL operations actually support that transaction design. Glue/S3 writes remain outside this database transaction.

If checkpoint completion is a separate operation, every prior accepted write must tolerate replay. Require the expected prior checkpoint when advancing it so stale work cannot move progress incorrectly. Serialize processing with a durable single-owner mechanism, such as an atomic lease acquired before selection, with defined expiry and recovery behavior. A schedule interval alone does not prevent overlap; manual starts and long runs can overlap too.

**Checkpoint:** Force a failure after landing but before acceptance, and another after downstream writes if your completion is separate. Show unchanged completed progress on failure and safe recovery. Record lock ownership/release behavior on both success and error.

## Checkpoint 8 — automate orchestration

**TODO:** Build a Standard Step Functions workflow with Glue `.sync` tasks. Pass batch context through state outputs. Wait for asynchronous SQL to finish, inspect its final status, and route SQL failure away from checkpoint completion. Configure retries only for classified transient failures where repeat execution is safe.

Add a processing schedule after the manual workflow has succeeded and its failure/replay checks pass. Terraform must manage at least the workflow, schedules, and the IAM roles/policies created for them. Read/import existing resource ownership before applying changes. Keep state between deployments, and review replacements or destruction in the plan.

**Checkpoint:** Observe at least two automatic processing executions, compare their frozen inputs and completed boundaries, and show that concurrent execution attempts cannot accept conflicting progress.

## Permission boundaries

| Component | AWS-side responsibility | Separate database responsibility |
| --- | --- | --- |
| Ingestion Lambda | Fetch public source; write designated Bronze objects; write logs | None for direct S3 ingestion |
| Coordinator Lambda | Access batch metadata; submit/inspect Data API requests if used | Read checkpoint and invoke permitted completion logic |
| Bronze-to-Silver Glue | Read selected Bronze/scripts; write batch Silver/logs | None unless explicitly designed otherwise |
| Silver-to-landing Glue | Read batch Silver; connection/temp-S3 access required by chosen connector | Write the intended landing table |
| Step Functions | Invoke required tasks and monitor completion | SQL permissions belong to the database identity used by its SQL integration |
| Scheduler | Start the intended workflow or invoke ingestion using its execution role | None |

Review actual identities rather than copying the Monday producer/Firehose policies. Schema `USAGE`, table privileges, and procedure `EXECUTE` remain separate from AWS API permission. The homework Part 1 table explains these boundaries.

## Completion checklist and evidence

- [ ] Actual source contract and observation grain documented.
- [ ] Automatic raw ingestion with identifiable, complete captures observed.
- [ ] Bounded input selection and repeatable batch context demonstrated.
- [ ] Silver schema, quality, and batch read-back verified.
- [ ] Landing replay leaves canonical and Gold logically unchanged.
- [ ] Physical fact and at least two dimensions support three analytical queries.
- [ ] Controlled failure leaves completed checkpoint unchanged and recovery succeeds.
- [ ] Overlap/late-data and concurrent-execution policies exercised.
- [ ] Two automatic processing runs and reviewed Terraform checks recorded.
- [ ] Cost ownership and schedule/service cleanup documented from actual resources.

Existing local Kinesis tests establish only their original retry/contract behavior. They do not verify any unchecked item above. Record expected versus observed counts, execution IDs, batch IDs, and checkpoint values in your own evidence; leave unrun steps marked pending.

## Sources

- [Glue bookmarks](https://docs.aws.amazon.com/glue/latest/dg/monitor-continuations.html): input tracking and target/replay limitations.
- [Glue `.sync` integration](https://docs.aws.amazon.com/step-functions/latest/dg/connect-glue.html): waiting for job completion.
- [Step Functions ResultPath](https://docs.aws.amazon.com/step-functions/latest/dg/input-output-resultpath.html): preserving JSONPath workflow context.
- [Redshift MERGE](https://docs.aws.amazon.com/redshift/latest/dg/r_MERGE.html) and [constraints](https://docs.aws.amazon.com/redshift/latest/dg/t_Defining_constraints.html): merge source/target requirements and unenforced keys.
- [Terraform import](https://developer.hashicorp.com/terraform/language/import): adopting existing resources before managing changes.
