# GCP pipeline resume checkpoint — October 26, 2026

## Verified stopping point

The learner manually triggered the complete GCP workflow successfully. Read-only API verification confirms `jobs-snap-monthly` execution `ccac8dac-e4b0-4bfb-9efe-0712144189a9` is `SUCCEEDED`, running from 08:09:44Z to 08:18:22Z on October 26, 2026. The returned result is `complete`, with 7,050 current state facts, 20,868 current industry facts and zero new measurement-history events.

The completed path is Cloud Run BLS/SNAP ingestion → immutable GCS Bronze → managed Spark Silver → native BigQuery staging and key validation → transactional Gold/current-fact/history publication → committed-run verification. These are fresh cloud captures, not merely replay of the manually uploaded historical files.

Logical refresh: `monthly-ccac8dac-e4b0-4bfb-9efe-0712144189a9`.

Accepted staging manifest: `project-4b0f63f3-e441-4289-b42.jobs_snap_staging.manifest_ade7f8177bf429afec468e7d`.

Accepted Silver summary: `gs://jobs-snap-silver-620503845148/silver/ingestion_date=2026-10-26/run_id=monthly-ccac8dac-e4b0-4bfb-9efe-0712144189a9/summary.json`.

Earlier same-logical-input retry testing returned `already_published`, with exactly one ledger row and no duplicated history. A real nonzero revision publication and concurrent-run rejection have not yet been demonstrated. Local workflow YAML inspection confirms the corrected parameter defaults, job_env/job_arguments names and empty_response assignment are saved.

## Resume here

Scheduling/dashboard work has resumed. The learner selected **08:00 UTC on the first day of each month** (`0 8 1 * *`) and **Looker Studio**. The Scheduler API and `jobs-snap-scheduler` account with Workflows Invoker are verified; no Scheduler jobs were found in us-central1 at this checkpoint. Next learner creates `jobs-snap-monthly-trigger` with OAuth to the Workflows executions endpoint, verifies one Run now dispatch and its resulting workflow completion, then connects the Gold reporting views to the dashboard. A complete manual workflow execution is already accepted; do not rerun historical backfills or repeat completed infrastructure setup by default. Exact console instructions and pending evidence are in steps.md.

Revisit Billing Reports and Live costs after reporting catches up. Screenshots around 02:18 local showed $0 actual and approximately $0 estimated live cost, with $300 trial credit remaining. Actual gross cost is not yet established; do not claim the pipeline was free.

## Resources and ownership

Project: `project-4b0f63f3-e441-4289-b42`. Region: `us-central1`.

Cloud Run jobs: `jobs-snap-bls-ingest`, `jobs-snap-usda-ingest`, `jobs-snap-stage`, and `jobs-snap-publish`.

Workflow: `jobs-snap-monthly`, runtime account `jobs-snap-workflow@project-4b0f63f3-e441-4289-b42.iam.gserviceaccount.com`.

Source/workload accounts: `jobs-snap-ingest`, `jobs-snap-process`, and `jobs-snap-publish`. Buckets: `jobs-snap-bronze-620503845148` and `jobs-snap-silver-620503845148`. BigQuery datasets: `jobs_snap_staging` and `jobs_snap_gold`.

Preserve learner ownership: provide code in chat; learner edits implementation files and creates/deploys/executes cloud resources. Agent may edit documentation and inspect sources/cloud state read-only. Never expose the BLS secret. Full evidence and error corrections are in [steps.md](steps.md); the current GCP roadmap is [gcp-learning-plan.md](gcp-learning-plan.md).

## Bounds to preserve

Historical baseline is January 2015–December 2025, followed by initial catch-up. Ongoing refreshes process only six reporting months ending at each source/series cutoff. Preserve immutable source captures and legitimate NULLs/anomalies. Maintain the two accepted facts, three shared dimensions, five-column monthly date dimension and measurement-history ledger. Do not silently widen into annual historical reconciliation or older-gap backfills.
