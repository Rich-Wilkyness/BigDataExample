# Verified Citi Bike pipeline and role setup

> Executed on 2026-10-08 evening in America/Boise; AWS timestamps are 2026-10-09 UTC. These files record actual account changes and executions.

## Resources and responsibilities

| Resource | Role | Access |
| --- | --- | --- |
| `richard-citibike-ingestion` | `RichardCitiBikeLambdaRole` | Write own Bronze prefix and own function logs |
| Scheduler target configuration | `RichardCitiBikeSchedulerRole` | Invoke only Richard's ingestion Lambda |
| EMR application `00g9cdv89blube0d` | `RichardCitiBikeEMRRole` | Read own Bronze/scripts; write own Silver/logs |
| Glue job `richard-citibike-bronze-to-silver` | `AWSGlueServiceRole-RichardCitiBike` | Read own Bronze/scripts; write own Glue Silver/temp prefixes |

Bucket: `richard-wilkerson-citibike-pipeline-866934333672-us-east-2-an`, Region `us-east-2`, account `866934333672`.

## Actual results

- Lambda's existing deployed code was inspected. It matches the local ingestion code; no code replacement was necessary.
- Lambda now uses the dedicated role, a 120-second timeout and 256 MB memory; configuration reached Active/Successful.
- Manual Lambda invocation wrote four JSON objects at snapshot `2026-10-09T02:41:15.304322+00:00`.
- Status and metadata Bronze feeds each contain 2,519 stations.
- EMR run `00g9com5g7safg0f` reached SUCCESS and wrote `silver/citibike/station_status/`.
- Glue run `jr_70db287aa6199146b043df237873d3a25f3cdde8490a142c7c9a56e1e97980ef` reached SUCCEEDED and wrote `silver/citibike/glue_station_status/`.
- Both Parquet outputs were downloaded and read back using the existing project environment. Each contains 2,519 rows, with zero missing station IDs/timestamps, duplicate station/snapshot pairs, unmatched station metadata, or negative availability/capacity counts.
- A sorted all-column comparison confirms the Glue and EMR outputs agree for this snapshot.
- EMR's driver log reports `SILVER RECORD COUNT: 2519`; the log is saved here.
- EMR was stopped after completion; GetApplication confirmed STOPPED. Automatic start and 15-minute automatic stop remain configured.
- Instructor-owned roles/resources were not changed. Redshift loading was not executed in this repair.

## Scheduler dependency

The dedicated Scheduler role and its exact Lambda permission were created and verified. Its trust restricts Scheduler to this account's `default` schedule group. Scheduler itself does not write S3: it invokes Lambda, which writes Bronze.

The login cannot perform `scheduler:ListSchedules`, `scheduler:GetSchedule`, or `scheduler:CreateSchedule`. A one-time verification schedule creation attempt was denied. No schedule was created or enabled, and existing schedules could not be inspected.

Give the administrator these details yourself:

- User: `arn:aws:iam::866934333672:user/richard.wilkerson@techconsulting.tech`.
- Region: `us-east-2`; desired schedule: `richard-citibike-every-five-minutes`, group `default`.
- Execution role: `arn:aws:iam::866934333672:role/RichardCitiBikeSchedulerRole`.
- Target: `arn:aws:lambda:us-east-2:866934333672:function:richard-citibike-ingestion`.
- Either have the administrator create/configure the schedule, or grant scoped Scheduler create/read/update/delete actions, required list access, and `iam:PassRole` on this exact role for `scheduler.amazonaws.com`.
- If this schedule already exists, inspect it and update it deliberately rather than creating a duplicate.
- [scheduler-input.json](scheduler-input.json) is a prepared five-minute schedule, saved DISABLED. It was not deployed. Enable it only when the owner can monitor and pause it.

A recurring ingestion schedule does not automatically submit EMR or Glue transformations. This verified pipeline was invoked in separate manual stages.

## Files and replay limits

- [pipeline-config.json](pipeline-config.json): names and run IDs.
- [execution-evidence.json](execution-evidence.json): invocation result, observed source schema/counts, verified roles and policies, terminal statuses.
- [emr-silver-validation.json](emr-silver-validation.json) and [glue-silver-validation.json](glue-silver-validation.json): read-back quality evidence.
- [emr-driver-stdout.txt](emr-driver-stdout.txt): actual EMR schema/sample/count output.
- Trust/access JSON files: exact role policy examples matching the account setup.
- [glue-bronze-to-silver.py](glue-bronze-to-silver.py): adapts the existing Spark transformation to Glue's named `--BUCKET` argument, a separate output prefix, and published-data checks.

Both transforms rebuild/overwrite their own dedicated output prefix. They are not incremental or atomic publication pipelines. Multiple metadata snapshots still require an explicit selection rule; this run used one captured snapshot. A successful bounded run does not verify long-term scheduling, historical modeling, or production recovery.

## Next homework checkpoint

Continue at Step 6 in [the Thursday homework guide](../../4.2_Thur_Glue_Redshift_HW.md): your own Redshift Serverless setup or the instructor-approved fallback. The Bronze → Silver requirement now has your own successful Glue execution evidence.

References: [Lambda execution roles](https://docs.aws.amazon.com/lambda/latest/dg/lambda-intro-execution-role.html), [EMR runtime roles](https://docs.aws.amazon.com/emr/latest/EMR-Serverless-UserGuide/security-iam-runtime-role.html), [Scheduler trust restrictions](https://docs.aws.amazon.com/scheduler/latest/UserGuide/cross-service-confused-deputy-prevention.html).

