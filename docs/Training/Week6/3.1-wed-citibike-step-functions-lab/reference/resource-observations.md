# Instructor observations — 2026-10-14

These are timestamped read-only observations captured before the later follow-along reconstruction. They do not certify the instructor's finished workflow or current database contents.

Later run-history refresh on October 14 found additional successful incremental runs. The latest Silver batch job completed at **20:29:30 UTC / 2:29 PM Boise** (`jr_7a6934d91f303b8f6a84d70d3a6f34133d1e330a1d267b570f1fc93cb85df983`), and the latest Redshift landing loader completed at **20:32:39 UTC / 2:32 PM Boise** (`jr_fe9b403c70978f11edbc75e584b805a5b8c899106f2c6ae5ab33b43a39286d8a`). Both incremental jobs now have four successful runs in the returned histories. This supports ongoing batch processing beyond the first catch-up demonstration, but does not identify a schedule/Step Functions trigger or verify the separate SQL acceptance/Gold work. The earlier table below remains the original observation snapshot.

### Instructor v2 update — live inspection on 2026-10-14

The screenshot captures an earlier recovery checkpoint. Subsequent read-only inspection of the instructor’s `citi-bike-nyc-pipeline` bucket, four deployed Glue scripts, job configurations, and run histories now gives a more concrete picture. The screenshot’s 55% was the instructor’s estimated completion, not the fraction of the plan available to us.

**He is building two paths: a historical rebuild to establish v2, then bounded incremental batches to keep it current.** The original Bronze input remains the source. New Silver prefixes and Redshift destinations separate the revised data from the original pipeline.

| Instructor Glue job | Purpose confirmed from deployed script | Latest observed run on October 14 |
| --- | --- | --- |
| `CitiBikeBronzeToSilverBackfillV2` | Rebuild historical station snapshots into date-partitioned Silver v2 | `SUCCEEDED`, completed 17:36 UTC / 11:36 AM Boise |
| `CitiBikeSilverToRedshiftBackfillV2` | Append historical Silver v2 into a prepared empty Redshift v2 table | `SUCCEEDED`, completed 17:50 UTC / 11:50 AM Boise |
| `CitiBikeBronzeToSilverIncrementalV2` | Select a timestamp-bounded Bronze batch and publish its isolated Silver output | `SUCCEEDED`, completed 18:28 UTC / 12:28 PM Boise |
| `CitiBikeSilverToRedshiftIncrementalV2` | Load that one Silver batch into a Redshift landing table with its batch ID | `SUCCEEDED`, completed 18:33 UTC / 12:33 PM Boise |

The historical Silver job failed on October 13 with `[TASK_WRITE_FAILED]` during Parquet publication, matching the screenshot. Its next recorded run succeeded today. This confirms recovery at the Glue-job-status level; the run history alone does not establish the underlying fix or data correctness. The incremental Silver job also had a write failure and a missing-arguments failure before its successful run.

#### Historical path: establish the new baseline

```text
Existing Bronze station_status and station_information JSON
  → CitiBikeBronzeToSilverBackfillV2
  → s3://citi-bike-nyc-pipeline/silver/citibike/station_snapshots_v2/
  → CitiBikeSilverToRedshiftBackfillV2
  → public.citibike_station_snapshot_v2
```

- The Silver backfill can accept an optional exclusive `--CUTOFF_UTC`, parsed from snapshot filenames. Its recorded successful run did not report an explicit cutoff argument.
- It casts fields to defined types, deduplicates station/snapshot keys, selects the latest available station metadata per station before the cutoff, and partitions Parquet by `snapshot_date`. That metadata is a latest-state enrichment, not historical metadata matched to each snapshot time.
- It overwrites the entire **v2** Silver prefix, preserving the original Silver path. The listing currently contains 20 objects across October 7, 8, 12, 13, and 14 date partitions; this is object-level evidence, not a row-count or completeness check.
- The Redshift backfill’s connector appends to `public.citibike_station_snapshot_v2`. Its instructions require an existing empty destination. The script does not enforce destination emptiness and does not use your personal loader’s staging/merge pattern. Do not automatically retry or schedule this one-time loader.

#### Incremental path: process a selected batch

```text
Selected Bronze files within a UTC capture-time interval
  → CitiBikeBronzeToSilverIncrementalV2
  → silver/citibike/incremental_batches_v2/batch_id=.../
  → CitiBikeSilverToRedshiftIncrementalV2
  → public.citibike_station_snapshot_landing_v2
  → separate MERGE into accepted detail data
  → separate Gold refresh and validation
```

The observed successful batch was `catchup_20261014_a`, with `--START_AFTER_UTC=2026-10-14T16:00:00Z` and `--END_BEFORE_UTC=2026-10-14T22:00:00Z`. Both boundaries are exclusive. These are the instructor’s observed parameters, not values to copy for your bucket. The upper boundary was later than the run time: the job processes files visible during that listing, not files that will arrive later in the interval.

- The Silver job requires `--BATCH_ID`, `--START_AFTER_UTC`, and `--END_BEFORE_UTC`. It selects status files using timestamps in filenames, rather than S3 modification times, and uses the latest metadata file before the end boundary.
- It refuses to overwrite an existing batch prefix. Four objects were observed in the accepted batch’s October 14 date partition. A rerun of the same Silver batch is therefore not automatically a successful no-op; recovery must decide whether to reuse accepted output or handle partial publication.
- The loader requires `--BATCH_ID`, reads only that batch, adds a `batch_id` column, and appends to the landing table. Its final message explicitly says **“MERGE AND GOLD REFRESH STILL REQUIRED.”** Repeating the loader can append duplicate landing rows; accepted-table deduplication belongs to the later merge.
- All four v2 jobs have Glue bookmarks disabled. The inspected incremental scripts use explicit batch/window selection; they do not themselves persist an end-to-end accepted-progress checkpoint. The bucket’s inspected `checkpoints/` objects belonged to the earlier Kinesis/Aurora demo, so they do not establish checkpointing for this batch pipeline.
- Adjacent exclusive windows need careful boundary handling: a snapshot exactly at a shared boundary could be omitted. Late arrivals and files arriving after a listing also require deliberate catch-up/reconciliation.

**What remains unverified:** the actual Step Functions definition and executions, the separate merge SQL, Gold refresh, accepted checkpoint updates, and final warehouse reconciliation. `states:ListStateMachines` remains denied to your identity, so successful Glue runs cannot be attributed to a particular state-machine execution from this evidence. No instructor jobs or database statements were started during inspection.

**How this affects your walkthrough:** Steps 1–8 teach the smaller workflow using your working Richard resources. They do not reproduce the instructor’s new v2 landing/merge architecture. Use this section to follow his current resource names, and Steps 9–12 to understand the recovery, incremental, and Gold work. Adapting v2 to your bucket requires reviewing its hard-coded bucket, connection, destinations, batch arguments, and merge/checkpoint steps together.

