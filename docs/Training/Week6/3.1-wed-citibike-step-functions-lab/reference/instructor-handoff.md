# Instructor handoff alignment — October 14, 2026

Source: the instructor's ChatGPT handoff supplied by the learner. This is implementation context and reported evidence, not a claim that Richard's personal resources have been migrated or that every instructor result was independently reproduced.

## Final architecture described in the handoff

```text
Independent ingestion:
5-minute Scheduler → citibike-ingestion → S3 Bronze

Downstream processing:
30-minute Scheduler → citibike-class-orchestration
  → PrepareBatch: citibike-batch-coordinator
  → BronzeToSilver: CitiBikeBronzeToSilverIncrementalV2 (.sync)
  → SilverToRedshift: CitiBikeSilverToRedshiftIncrementalV2 (.sync)
  → CompleteBatch: citibike-batch-coordinator
  → PipelineSucceeded
```

The workflow does **not** invoke ingestion. `PrepareBatch` reads `public.citibike_pipeline_checkpoint` for pipeline `citibike_incremental`, starts two hours before `last_completed_utc`, ends ten minutes before the current time, and uses the execution name as the batch ID. The runtime field remains named `START_AFTER_UTC`, but the current executable selection is inclusive start/exclusive end.

`CompleteBatch` calls `public.sp_complete_citibike_batch(VARCHAR, TIMESTAMP)` through the Redshift Data API and polls in Python. That procedure checks landing, calls `public.sp_process_citibike_batch(VARCHAR)`, checks consistency, and advances the checkpoint after successful processing. The exact SQL/transaction/error semantics require the source; this handoff alone does not establish them.

| Responsibility | Instructor implementation | Earlier Richard reconstruction |
| --- | --- | --- |
| Batch preparation | Coordinator reads database checkpoint and computes overlap/lag | Operator/helper supplies a closed interval |
| Batch ID | Step Functions execution name | Operator-supplied validated ID |
| SQL execution | Coordinator Lambda constructs/submits/polls the procedure call | ASL directly submits trusted operator SQL and polls |
| Progress | `public.citibike_pipeline_checkpoint` high-water timestamp and last batch | `citibike_v2_lab.accepted_batch` accepted-batch ledger |
| Accepted detail | `public.citibike_station_snapshot_v2` | `citibike_v2_lab.station_snapshot` |
| Landing | `public.citibike_station_snapshot_landing_v2` | `citibike_v2_lab.station_snapshot_landing` |
| Gold | Physical `gold.dim_station`, `gold.dim_date`, `gold.fact_station_snapshot` | Minimal ordinary summary view; no physical star refresh |
| Workflow resources | Existing state machine, roles and log group retained/imported into Terraform | Separate new lab jobs and two state machines |
| Terraform providers | AWS `~> 5.0`, Archive `~> 2.0`; Terraform `>= 1.5.0` | AWS 6.x; no coordinator packaging/Archive provider |
| Scheduling | Independent five-minute ingestion and thirty-minute downstream schedules | No schedule provisioned in the reconstruction |

The prior reconstruction remains an isolated teaching alternative. Its Terraform and SQL are **not** a migration plan for the instructor's existing deployment. Match his source before building a Richard-specific equivalent of the coordinator/checkpoint/Gold route. Do not apply a fresh empty-state project against instructor resource names or copy his Terraform state into Richard's lab.

## What was independently checked after receiving the handoff

- `GetSchedule` returned `ENABLED` and `rate(30 minutes)` for `citibike-incremental-every-30-min`, targeting `arn:aws:states:us-east-2:866934333672:stateMachine:citibike-class-orchestration`. Target input is `{}`, maximum event age 60 seconds, and maximum delivery retries zero. This resolves the handoff's activation uncertainty at inspection time; it does not prove delivery or workflow completion.
- `GetFunctionConfiguration` confirmed `citibike-batch-coordinator` is `Active`, uses Python 3.12, handler `coordinator.handler`, role `CitiBikeBatchCoordinatorRole`, 240-second timeout, and 128 MB memory. Its actual handler source has not been retrieved.
- The current S3 Silver script contains `if start <= ts < end:`. Its docstring still says the lower bound is exclusive. The retrieved local reference already contains that inclusive condition; the earlier README description based on the stale header was corrected. `START_AFTER_UTC` is a name, not proof of its comparison operator.
- Direct `DescribeStateMachine` and `ListExecutions` calls were denied to Richard's IAM identity. We therefore could not confirm the deployed definition, redrive, unattended executions, or their correlation to the successful Glue runs.
- No resources, schedules, permissions, jobs, or SQL were changed during these checks.

## Reported runtime evidence and its limits

The instructor reports a successful controlled end-to-end execution after a redrive of `citibike-retry-20261014T194303Z`. Initial failures concerned database grants, first on the checkpoint and then on landing. The coordinator's Redshift identity was `IAMR:CitiBikeBatchCoordinatorRole`. IAM authentication and SQL authorization are separate; grants applied for that role do not grant Richard's eventual coordinator identity access.

The handoff reports 1,579,415 canonical and Gold fact observations before the final workflow, zero canonical station/timestamp duplicates, and no orphan station/date dimension references. Those are historical baseline results. A post-run audit and updated checkpoint were not supplied; do not use those counts as today's expected output or as proof of complete source-window coverage. The initial checkpoint was seeded from the latest known observation, not a complete historical audit.

The thirty-minute schedule is now confirmed enabled, but successful unattended runs, advancing checkpoints and post-run integrity remain pending verification. Two-hour overlap revisits late files only within its chosen lookback; it does not cover arbitrary lateness. A ten-minute lag gives recent ingestion time to settle, but does not freeze the object set. No atomic execution-admission lock or dedicated failure notifications were reported. `GetSchedule` delivery retries are separate from workflow/job retries.

## Active Terraform ownership

The instructor's active project is `~/Work/aws-citi-bike-pipeline-example/terraform_scripts/citibike-stepfunctions-terraform/`, using AWS CLI profile `company`. This is his machine's path/profile, not automatically a directory or authenticated profile on Richard's machine. The separate `terraform2` troubleshooting directory is not the active project.

The handoff states that pre-existing infrastructure was imported into the original Terraform state. His final apply reported zero added, four changed, zero destroyed, retaining the state-machine ARN. Preserve that ownership when he modifies his deployment. For a Richard deployment, use Richard resource names, a separate reviewed state, and deliberate reuse/import decisions; do not inherit the teacher's state ownership.

## Prompt to request the exact missing source

Copy the following into the instructor's existing ChatGPT conversation:

```text
Please prepare a sanitized, source-only handoff bundle from the ACTIVE project:
~/Work/aws-citi-bike-pipeline-example/terraform_scripts/citibike-stepfunctions-terraform/
Use the actual final files, not terraform2 and not newly reconstructed examples.

Include:
1. Every active .tf file: main.tf, orchestration.tf, scheduler.tf, and any referenced variables, outputs, versions/provider files, JSON/ASL templates or local modules.
2. The final coordinator.py, any helper modules/requirements/packaging inputs, and a redacted nonsecret configuration example showing all required environment-variable names.
3. .terraform.lock.hcl, plus a short README with the correct working directory and Terraform/init/import history. Describe state ownership without sharing state files.
4. The final deployed ASL definition for citibike-class-orchestration, including complete Lambda payloads, result paths, Glue arguments, error handling, and logging settings.
5. Exact Redshift DDL for landing, canonical, checkpoint, gold.dim_station, gold.dim_date, and gold.fact_station_snapshot; full definitions of sp_process_citibike_batch and sp_complete_citibike_batch, including signatures and transaction/security modes; the grants needed by the coordinator database identity; and the checkpoint bootstrap/catch-up instructions.
6. The final two incremental Glue scripts and their job arguments/configuration. Confirm that the executable window is start-inclusive/end-exclusive despite the stale START_AFTER_UTC docstring.
7. Streamlit source, requirements and a redacted configuration example if written. Otherwise label it NOT YET WRITTEN and state which Gold queries/columns it will use.
8. A manifest listing every included file's relative path and role, which files are deployed versus planned, and which files were unavailable. Keep original file names.
9. Read-only verification outputs, if available: schedule state/target, recent unattended workflow statuses, current checkpoint, and post-run duplicate/count/orphan audits. Label reported versus freshly verified evidence and include timestamps.

Exclude terraform.tfstate, backup state, saved plans/plan JSON, .terraform/, AWS credentials, tokens, passwords, secret values and private keys. Redact sensitive .tfvars; provide variable-name examples instead. Do not deploy, import, apply, enable schedules, change grants, or recreate resources while preparing this bundle.

If you cannot access the files, say exactly which are missing; do not invent them. Provide a zip if possible, or each source file in a separate labeled code block. The goal is to adapt the existing coordinator/checkpoint/Gold architecture for a student named Richard, not redesign it.
```

The highest-priority files are the active Terraform `.tf` files, `coordinator.py`, and exact stored-procedure/table DDL. They determine how to adapt the remaining workflow and dashboard correctly.
