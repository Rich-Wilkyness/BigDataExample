# Citi Bike follow-along files: initial → backfill → incremental → dashboard

Start with the [Wednesday walkthrough](../3_Wed_Step_Functions.md). This directory keeps the code and configuration beside the lesson so you can read the file used at each checkpoint.

**These files are local learning artifacts, not an already deployed pipeline.** The instructor's six deployed Glue scripts were retrieved from his S3 bucket on 2026-10-14. His Terraform project, actual state-machine definition, merge/Gold SQL, and Streamlit app were not available. The Richard adaptations and supporting infrastructure/SQL/dashboard are labeled reconstructions. They are not presented as his exact finished project or evidence that his complete workflow succeeded.

**New instructor handoff:** read [the alignment and exact-source request](reference/instructor-handoff.md) first. His completed design uses a coordinator Lambda, a Redshift high-water checkpoint, physical Gold dimensions/facts, AWS provider 5.x plus Archive 2.x, and the existing imported workflow. The earlier lab below uses a different isolated acceptance ledger/view and direct Data API workflow. Keep it as a teaching alternative; do not use its apply steps to recreate his deployment. Exact source is needed before converting it into a matching Richard project. The instructor's thirty-minute schedule was independently confirmed ENABLED; unattended execution and checkpoint advancement remain unverified.

## Three stages of Glue work

| Stage | Why it exists | Input/output behavior | Run pattern |
| --- | --- | --- | --- |
| Initial | Learn flattening JSON, joining station metadata, and loading a warehouse | Richard's existing full-history Silver overwrite and repeat-safe warehouse loader; instructor initial loader sampled 100 rows | Existing baseline; retain for comparison |
| Backfill | Establish a corrected historical baseline before cutover | Historical Bronze before a cutoff → separate date-partitioned Silver history → prepared empty lab detail table | One-time, manually validated; warehouse append is not retry-safe |
| Incremental | Keep the baseline current without rebuilding all history | Selected Bronze interval → isolated Silver batch → landing → merge/acceptance → reporting | One closed batch at a time; controlled replay |

“We updated Glue twice” means the lesson evolved through these stages. It does not mean updating the Glue runtime twice. These files retain the stages separately so the historical overwrite job is not accidentally scheduled as the ongoing incremental job.

## Directory and reading order

```text
3.1-wed-citibike-step-functions-lab/
├── initial/                 Copies of Richard's existing Lambda and two Glue scripts
├── backfill/                Parameterized historical Silver and warehouse jobs
├── incremental/             Parameterized bounded Silver and landing jobs
├── reference/
│   ├── instructor/          Six instructor source snapshots; compare, do not deploy
│   └── provenance.json      Original S3 locations, hashes, missing sources, adaptations
├── sql/                     New lab tables, acceptance procedure, read-only checks
├── workflows/               Backfill and incremental Standard ASL definitions
├── inputs/                  Example execution inputs; replace stale example intervals
├── terraform/               Upload scripts; define four jobs and two workflows
├── iam/                     Required role/actions, trust boundaries, SQL grants
├── dashboard/               Streamlit sample/live reader and sample CSV
├── prepare-input.py         Generate aligned batch arguments and acceptance SQL offline
└── verify-local.py          Offline checks; no AWS jobs or SQL execution
```

Read one row below when the walkthrough reaches it. A Python filename is not a Glue job name: Terraform connects the local source file, uploaded S3 script, and named job.

| File | What to look for | Why it matters |
| --- | --- | --- |
| [initial/ingestion-lambda.py](initial/ingestion-lambda.py) | `CITIBIKE_BUCKET`, capture timestamp, uploaded keys | Raw snapshots remain the replay source |
| [initial/bronze-to-silver.py](initial/bronze-to-silver.py) | `explode`, filename timestamp, metadata join, `overwrite`, read-back | Your original transformation and its whole-history behavior |
| [initial/silver-to-redshift.py](initial/silver-to-redshift.py) | Validation, shared staging, `MERGE` | Your original warehouse loader differs from the instructor's initial sampled append |
| [reference/provenance.json](reference/provenance.json) | Source names and the adaptation list | Separates inspected instructor code from reconstructed lab code |
| [backfill/bronze-to-silver.py](backfill/bronze-to-silver.py) | `BUCKET`, optional `CUTOFF_UTC`, latest metadata, date partition, separate overwrite path | Historical rebuild has an explicit cutover boundary |
| [backfill/silver-to-redshift.py](backfill/silver-to-redshift.py) | Eleven columns, isolated lab destination, append connector, explicit COPY role | Requires an empty destination before its first load |
| [incremental/bronze-to-silver.py](incremental/bronze-to-silver.py) | Required batch/interval args, explicit URI list, immutable output, read-back | Process selected files; do not overwrite accepted history |
| [incremental/silver-to-redshift.py](incremental/silver-to-redshift.py) | Batch path, `batch_id`, landing append | Landing is intermediate and may contain replayed rows |
| [sql/01-setup.sql](sql/01-setup.sql) | New `citibike_v2_lab` schema, table column order, ordinary reporting view | Does not replace your original public detail or Gold star schema |
| [sql/02-accept-batch.sql](sql/02-accept-batch.sql) | Atomic procedure, batch conflict checks, merge, accepted marker | Detail mutation and accepted progress commit together |
| [sql/03-validate.sql](sql/03-validate.sql) | Snapshot range, duplicate keys, landing rows, accepted batches, Gold totals | A successful job still needs data checks |
| [workflows/backfill.asl.json](workflows/backfill.asl.json) | Two Glue `.sync` tasks; no retries | Historical workflow remains separate from ongoing processing |
| [workflows/incremental.asl.json](workflows/incremental.asl.json) | Build/reuse batch → landing → SQL submission → polling | SQL submission success is not SQL completion |
| [prepare-input.py](prepare-input.py) | UTC validation, closed interval, safe batch ID, matching SQL call | Keep source selection and accepted interval aligned |
| [terraform/main.tf](terraform/main.tf) | Script objects, job map, workflow JSON field overrides | Terraform provisions configuration; it does not perform the backfill |
| [terraform/variables.tf](terraform/variables.tf) | Explicit existing resources and required workflow role ARN | Reuse your infrastructure without taking ownership of its lifecycle |
| [iam/README.md](iam/README.md) | Operator versus workflow versus Glue versus database identity | One role's permission does not fix another stage's denial |
| [dashboard/app.py](dashboard/app.py) | Default sample mode; explicit live-load button; charts | The dashboard reads accepted reporting data |
| [dashboard/redshift-reader.py](dashboard/redshift-reader.py) | Fixed SELECT, bounded polling, result pagination | No ETL or table mutations on page refresh |

## Richard-specific adaptations

- Bucket and connection/warehouse S3 role are Glue arguments instead of instructor constants. Terraform supplies `--BUCKET`, and on loader jobs `--CONNECTION` and `--REDSHIFT_ROLE`.
- The lab uses `silver/citibike/v2-lab/history/`, `silver/citibike/v2-lab/batches/batch_id=.../`, and schema `citibike_v2_lab`. Your original destinations remain separate.
- The incremental interval is **inclusive start, exclusive end**, `[start, end)`, using `--START_AT_UTC` and `--END_BEFORE_UTC`. The current instructor reference also implements inclusive start with `start <= ts < end`, despite its stale exclusive-start header and the argument name `START_AFTER_UTC`. Our argument rename makes the existing comparison clearer; it is not a different boundary policy. The earlier description based on the header was incorrect.
- The input generator rejects future end boundaries. S3 listing cannot select objects that will appear later. A closed interval can still receive late files afterward; use a separate catch-up batch and reconcile retained Bronze against accepted keys.
- Both adapted Silver jobs read published Parquet back and check nonempty output plus valid/unique keys before permitting downstream work. These checks do not prove historical completeness, correct metadata semantics, or zero rejected source rows.
- Metadata remains latest-state enrichment, not point-in-time history. The incremental code uses the latest metadata file before its end, so it can enrich an earlier status snapshot with later station attributes. Record this assumption.
- `accepted_batch` records accepted batch identities/intervals, not a universal high-water mark or an immutable source manifest. Retain the input and published batch; independent source mutation/listing changes remain a replay limitation.
- Gold here is a minimal ordinary view over accepted snapshots. It changes when base data commits; it needs no `REFRESH`. The instructor's unrecovered physical Gold model may require a separate refresh. Your star-schema transformations remain separate.

## Terraform preparation

Terraform was not installed on the user's shell PATH during initial inspection. Use the [official installation instructions](https://developer.hashicorp.com/terraform/install). This lab requires Terraform 1.5 or newer, below 2.0, and the HashiCorp AWS provider 6.x. Keep the generated `.terraform.lock.hcl` once initialized. The provider is downloaded by `terraform init`; the AWS CLI and boto3 are separate tools.

From the repository root, enter this project's Terraform directory:

```bash
cd /Users/richardwilkerson/VSCodeProjects/BigDataExample/docs/Training/Week6/3.1-wed-citibike-step-functions-lab/terraform
```

```bash
cp terraform.example.tfvars terraform.tfvars
```

Replace the placeholder `workflow_role_arn` in `terraform.tfvars` with the actual reviewed role. Resolve [IAM and database prerequisites](iam/README.md). Defaults reuse the named Richard bucket, connection, Glue role, Redshift S3 role and workgroup. The configuration does not silently create those prerequisites or import teacher resources.

```bash
terraform init
terraform fmt -check
terraform validate
terraform plan -out=lab.tfplan
```

Read the plan: expect **four new script objects, four new Glue jobs, and two new state machines** for an empty Terraform state. Expect no changes to your original bucket, Lambda, connection, workgroup or original jobs. If those lab names already exist outside this state, decide ownership/import first; a matching name does not make Terraform recognize them as managed.

After reviewing the plan and permissions, applying it provisions the lab configuration:

```bash
terraform apply lab.tfplan
terraform output workflow_arns
terraform output job_names
```

No data load starts merely because Terraform applies. SQL setup, manual checkpoints, and `StartExecution` are separate operations. Keep state and plans local and out of Git; they describe real infrastructure. Do not run `destroy` as routine cleanup: it would remove the lab jobs/workflows/scripts, while warehouse objects and derived datasets would still remain.

Provider references: [Glue jobs](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/glue_job), [S3 script objects](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/s3_object), and [state machines](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/sfn_state_machine).

## Backfill run contract

Run [01-setup.sql](sql/01-setup.sql) and [02-accept-batch.sql](sql/02-accept-batch.sql) in Richard's `dev` database after understanding their objects/grants. The backfill loader must see an empty `citibike_v2_lab.station_snapshot` table. A second append is not safe merely because the state-machine name is unchanged.

Choose a fixed **exclusive** UTC cutoff and edit [backfill.example.json](inputs/backfill.example.json). Its date is illustrative; it is not an instructor-approved processing range. Retain a frozen input or record the exact relevant object set. Start the backfill state machine from the console with this JSON, then run [03-validate.sql](sql/03-validate.sql) and compare actual Silver counts/keys. Do not start incremental processing until the historical baseline is accepted.

The historical Silver overwrite is isolated to the lab history prefix but still has partial-publication hazards. On failure, preserve the previous accepted version and inspect files before redoing it. The SQL acceptance procedure is for incremental landing batches, not the direct historical append.

## Incremental run contract

Capture a new source snapshot with your existing ingestion Lambda if needed, and verify its returned object keys. Set the incremental start to the accepted backfill cutoff or a deliberate catch-up start. Choose an already elapsed end after the selected capture; the guide does not invent source snapshots missing from your personal bucket.

From the lab directory, this example only generates local input:

```bash
python3 prepare-input.py --batch-id richard_example_20261014 --start 2026-10-14T00:00:00Z --end 2026-10-14T01:00:00Z --output inputs/incremental.local.json
```

Replace the dates and batch identity with your actual accepted range. Start the incremental state machine using the generated JSON. Both workflows use Standard `.sync` for Glue. Incremental SQL uses Data API temporary IAM authentication to Richard's workgroup and waits for `DescribeStatement.Status=FINISHED`. No automatic mutating retries are configured.

`accept_sql` is trusted operator input, and must be the matching `sp_accept_batch` call generated by the helper. The workflow's successful SQL completion means the procedure's implemented checks passed, not that source-to-target completeness was automatically proven. Run the read-only SQL and source reconciliation afterward.

### Failure and replay

| Failure boundary | What to preserve/check | Replay action |
| --- | --- | --- |
| Silver write fails | Selected Bronze interval, logs, partial batch prefix | Inspect and repair partial output before reuse; the writer refuses existing output |
| Silver succeeds; loader fails | Accepted published Silver batch | After validating it, generate input with `--reuse-silver` to skip the immutable Silver writer |
| Landing append succeeds; acceptance fails | Batch ID, landing rows, SQL statement/error | Repair SQL/grants and replay from accepted Silver; exact duplicate landing rows are collapsed by the procedure |
| Acceptance commits; reply/history is uncertain | `accepted_batch` row and final detail keys | Same ID/interval acceptance is a no-op except landing cleanup; different interval for that ID is rejected |
| Two executions overlap | Shared S3 destinations, Glue runs, SQL writers | Keep one active pipeline writer; per-job concurrency does not serialize whole executions |
| Window produces zero files | Exact filenames, UTC interval, late arrival expectations | Empty batch fails visibly; choose a genuine populated interval or implement an explicit no-data policy later |

The procedure collapses exact duplicates and rejects conflicting values for a station/snapshot within a batch. SQL locks protect its acceptance transaction; they do not make concurrent S3 writes safe. Source/target reconciliation and a real admission lock remain required before enabling a recurring schedule. No schedule is provisioned here.

## Streamlit: learn the visual first

From the repository root:

```bash
.venv/bin/python -m streamlit run docs/Training/Week6/3.1-wed-citibike-step-functions-lab/dashboard/app.py
```

Open the displayed local URL. Sample mode shows three synthetic snapshots and makes no AWS calls. Select **Richard Redshift**, then **Load accepted snapshots** only after the view exists and your local credential identity has SELECT/Data API access. The fixed query returns the latest 1,000 operational-station summary timestamps; this is not every station row or the entire history. Missing operational-station snapshots may yield no summary rows. The displayed latest capture is a freshness clue, not proof the schedule is healthy.

If dependencies are missing, install the [dashboard requirements](dashboard/requirements.txt) into the repo environment:

```bash
.venv/bin/python -m pip install -r docs/Training/Week6/3.1-wed-citibike-step-functions-lab/dashboard/requirements.txt
```

The dashboard uses local AWS SDK credentials, not the AWS MCP session. A working MCP resource inspection does not prove your shell is authenticated. Query failures show the statement/error; a polling timeout does not prove SQL stopped. Refresh is explicit, so page reruns do not launch new queries or ETL work automatically. No credentials are embedded in these files.

Streamlit references: [Running an app](https://docs.streamlit.io/develop/concepts/architecture/run-your-app) and [AppTest](https://docs.streamlit.io/develop/api-reference/app-testing/st.testing.v1.apptest).

## Verification and remaining work

From the repository root, run the offline verifier:

```bash
.venv/bin/python docs/Training/Week6/3.1-wed-citibike-step-functions-lab/verify-local.py
```

The verifier checks source hashes, Python/JSON structure, ASL reachability, batch-input validation, and local links. It also exercises the dashboard in sample mode and the Data API decoder/pagination with an SDK stub. These checks make no AWS calls and do not prove Spark, Redshift SQL, IAM, networking, publication completeness, billing, or cloud replay correctness. Exact authoring results and versions are recorded in [verification.md](verification.md).

All cloud deployment/execution, Redshift procedure/grants, historical reconciliation, incremental replay, and live dashboard reads remain pending. The instructor's reported completion is not independently certified because the finished workflow and SQL were inaccessible. Bring his Terraform/project path when shared; compare and integrate it rather than treating this reconstruction as an exact copy.
