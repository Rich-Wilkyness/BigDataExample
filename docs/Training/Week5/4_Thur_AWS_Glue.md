# AWS Glue and Redshift: Citi Bike Bronze → Silver → Gold

> Level: Beginner to intermediate  
> Applies to: AWS Glue, Spark, IAM, VPC networking, S3, Redshift Serverless  
> Example status: Saved scripts and policies; manual results recorded in the original notes  
> Evidence status: Local artifact review; recorded cloud results are distinguished below from fresh verification  
> Last reviewed: 2026-10-09

## Overview

The goal is to turn raw Citi Bike API snapshots into structured station data, load that data into a warehouse, and expose a reporting summary. The main engineering concerns are preserving each station/snapshot identity, giving each service the correct permissions, establishing the network path, and making repeated loads safe.

```text
Citi Bike API → Lambda → S3 Bronze JSON
                             ↓ Glue / Spark
                        S3 Silver Parquet
                             ↓ Glue → temporary S3 files → Redshift COPY
                        Redshift station snapshots
                             ↓ SQL aggregation
                        Gold reporting view
```

The Redshift detail table retains the station-snapshot grain. The Gold view changes the grain to one row per snapshot across operational stations. Gold describes the purpose of the model; it could also be stored as Parquet in S3.

## Learning objectives

- Explain the difference between service trust, AWS resource permissions, network access, and database permissions.
- Trace the Bronze-to-Silver script and the Silver-to-Redshift load.
- Explain why a VPC-attached Glue job needs a working route to S3.
- Verify rows and keys in Redshift rather than relying only on a successful job status.
- Explain how staging and `MERGE` protect repeated station-snapshot loads.

## Prerequisites and working directory

- AWS CLI v2 with an authenticated profile authorized to use the relevant resources.
- Bronze JSON already captured in the learner bucket; see the [Wednesday console walkthrough](3.3-wed-citibike-console-steps.md).
- The [Thursday practice guide](4.2_Thur_Glue_Redshift_HW.md) provides the original staged checkpoints. These notes organize the implementation and results recorded while completing them.
- Commands below assume macOS/zsh and the artifact directory as the current directory:

```bash
cd /Users/richardwilkerson/VSCodeProjects/BigDataExample/docs/Training/Week5/4.1_EMR_citibike
export AWS_DEFAULT_REGION=us-east-2
export AWS_PAGER=""
export BUCKET=richard-wilkerson-citibike-pipeline-866934333672-us-east-2-an
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
```

Use your configured `AWS_PROFILE`; the instructor examples mixed `default` and `company`, so do not copy a profile name without checking it. Inspect the caller identity before issuing resource-changing commands. Commands in this guide document the setup; they were not executed against AWS during this editing pass.

## Resource map and saved files

### Learner resources used in the notes

| Resource | Recorded value | Purpose |
| --- | --- | --- |
| Region | `us-east-2` | Location of the bucket, jobs, and warehouse |
| Bucket | `richard-wilkerson-citibike-pipeline-866934333672-us-east-2-an` | Bronze, Silver, scripts, and temporary files |
| Glue execution role | `AWSGlueServiceRole-RichardCitiBike` | Permissions used by Glue |
| Redshift S3 role | `RichardCitiBikeRedshiftRole` | Permissions used by Redshift to access staging files |
| Redshift workgroup | `richard-citibike-wg` | Compute and network endpoint |
| Database | `dev` | Container for schemas and tables |
| Database administrator | `richard_admin` | Initial database login; keep the password private |
| Glue JDBC connection | `richard-citibike-redshift-connection` | Saved database and network settings |
| Warehouse load job | `richard-citibike-silver-to-redshift` | Silver-to-Redshift Spark job |
| VPC | `vpc-0df4612f429f52b16` | Network used in the recorded setup |
| Glue subnet | `subnet-0b0981def77506f0f` | Subnet for Glue network interfaces |
| Availability Zone | `us-east-2b` | Recorded subnet AZ |
| Security group | `sg-0f7b3d5165f21f99c` | Recorded network rules; inspect before reuse |
| Route table | `rtb-0b50cc16c48fedd8a` | Recorded table associated with the S3 endpoint |
| S3 gateway endpoint | `richard-citibike-s3-endpoint` | Private route to regional S3 |

The learner namespace name was not captured. Inspect the workgroup's namespace association rather than substituting the instructor namespace. Network IDs describe the recorded environment and must be checked before reuse.

### Artifact inventory

All seven files below are present in [4.1_EMR_citibike](4.1_EMR_citibike/).

| File | Responsibility |
| --- | --- |
| [glue_trust_policy.json](4.1_EMR_citibike/glue_trust_policy.json) | Allows `glue.amazonaws.com` to assume the execution role |
| [glue_s3_policy.json](4.1_EMR_citibike/glue_s3_policy.json) | Grants Glue access to the learner bucket's input, scripts, output, and temporary prefixes |
| [citibike_glue_etl.py](4.1_EMR_citibike/citibike_glue_etl.py) | Reads Bronze JSON, builds Silver station snapshots, writes Parquet, and checks the published output |
| [redshift-trust-policy.json](4.1_EMR_citibike/redshift-trust-policy.json) | Allows the Redshift and Redshift Serverless service principals to assume the S3 role |
| [redshift-s3-policy.json](4.1_EMR_citibike/redshift-s3-policy.json) | Grants Redshift bucket listing, input/staging reads, and temporary export writes |
| [richard-citibike-silver-to-redshift.py](4.1_EMR_citibike/richard-citibike-silver-to-redshift.py) | Validates incoming keys, loads staging, and merges into the detail table |
| [gold-station-availability-summary.sql](4.1_EMR_citibike/gold-station-availability-summary.sql) | Creates or replaces the Gold reporting view |

**Missing setup record:** the final loader requires `public.citibike_station_snapshot` to exist before it creates staging with `LIKE`. Its original `CREATE TABLE` statement or first-load creation record was not found in the artifact directory. The practice guide contains illustrative DDL for a differently named test table; that does not establish the actual destination definition. Find the original DDL or export the existing table definition to complete the setup record.

The temporary `/tmp/citibike-connection.json` from the instructor demonstration was deliberately deleted after connection creation. It contained credentials and is not a missing artifact to recover. Cloud job definitions, connection settings, and SQL result exports are also not saved in these seven files.

### Instructor examples

The lecture used bucket `citi-bike-nyc-pipeline`, Glue role `AWSGlueServiceRole-CitiBike`, Glue job `CitiBikeBronzeToSilverGlue`, Redshift workgroup `citibike-wg`, namespace `citibike-ns`, and connection `citibike-redshift-connection`. Keep these names separate from the learner resources above.

The [shared instructor conversation](https://chatgpt.com/share/6ac80534-c88c-83ea-a447-b6ee19c098ff) is retained as a reference from the original notes; its contents were not used to fill gaps in this revision.

## Requirements, identity, and data ownership

| Dataset | Grain and ownership | Important invariant |
| --- | --- | --- |
| Bronze JSON | API responses captured by ingestion into learner-owned S3 | Preserve raw input for replay |
| Silver Parquet | One station at one captured snapshot | `(station_id, snapshot_timestamp)` must be populated and unique |
| Redshift detail table | One station at one snapshot | Replaying the same snapshot must not add another copy |
| Gold view | One snapshot summarizing operational stations | Aggregate from validated detail rows |

The recorded example contains 2,519 station rows for one snapshot. That is an example count, not a fixed property of future Citi Bike feeds. No recurring freshness target or automatic end-to-end orchestration was established here.

## IAM: who runs the code, and what can it access?

### Trust policy versus permissions policy

- **Trust policy:** who may assume a role. The Glue trust file names `glue.amazonaws.com` and allows `sts:AssumeRole`.
- **Permissions policy:** what the assumed role may do. The Glue S3 file grants operations on specific bucket and object ARNs.
- **Your deployment identity:** needs permission to configure jobs and pass their execution roles with `iam:PassRole`. An execution role's permissions do not automatically grant those permissions to you.
- **Database login:** controls SQL privileges. An S3 role does not automatically grant table access.

`create-role` creates the identity and its trust relationship. `attach-role-policy` associates an existing managed policy with that role. `put-role-policy` stores an inline policy directly on the role. A role can have both managed and inline policies.

### Create or inspect the Glue execution role

Inspect an existing role first. If it already exists, reuse it after checking its trust and permissions; an `EntityAlreadyExists` response does not require deleting it.

```bash
aws iam get-role \
  --role-name AWSGlueServiceRole-RichardCitiBike \
  --query 'Role.{Arn:Arn,Trust:AssumeRolePolicyDocument}'
```

If the role has not been created, the saved files support this setup:

```bash
aws iam create-role \
  --role-name AWSGlueServiceRole-RichardCitiBike \
  --assume-role-policy-document file://glue_trust_policy.json

aws iam attach-role-policy \
  --role-name AWSGlueServiceRole-RichardCitiBike \
  --policy-arn arn:aws:iam::aws:policy/service-role/AWSGlueServiceRole

aws iam put-role-policy \
  --role-name AWSGlueServiceRole-RichardCitiBike \
  --policy-name RichardCitiBikeGlueS3Access \
  --policy-document file://glue_s3_policy.json
```

`RichardCitiBikeGlueS3Access` is a descriptive inline-policy name used in these examples; the original notes did not establish its saved name. The managed-policy ARN above identifies AWS's Glue service policy. Find managed-policy ARNs in IAM → Policies or the relevant AWS documentation; inline policies are addressed by role and policy name instead.

Verify trust, managed attachments, and inline permissions separately. `get-role` alone does not display all access policies.

```bash
aws iam list-attached-role-policies \
  --role-name AWSGlueServiceRole-RichardCitiBike

aws iam list-role-policies \
  --role-name AWSGlueServiceRole-RichardCitiBike

aws iam get-role-policy \
  --role-name AWSGlueServiceRole-RichardCitiBike \
  --policy-name RichardCitiBikeGlueS3Access
```

### Reading a permissions policy

| Element | Meaning | How to choose it |
| --- | --- | --- |
| `Version` | IAM policy-language version | Use `2012-10-17`; it is not the file's creation date |
| `Statement` | List of permission statements | Separate permissions with different actions or resource scopes |
| `Sid` | Optional statement label | Choose a readable description, such as `WriteOwnBronze` |
| `Effect` | `Allow` or `Deny` | Grant intended access; explicit denies override allows |
| `Action` | Service operation, such as `s3:PutObject` | Use the service's documented IAM action names |
| `Resource` | Resources the action applies to | Use bucket ARNs for bucket actions and object ARNs for object actions |
| `Principal` | Caller allowed by a trust/resource policy | In these trust files, the AWS service assuming the role |

JSON policy files cannot contain `//` comments. Keep explanations in the notes. See the [IAM policy element reference](https://docs.aws.amazon.com/IAM/latest/UserGuide/reference_policies_elements.html).

| Common action | Purpose | Typical scope |
| --- | --- | --- |
| `s3:ListBucket` | List object keys | `arn:aws:s3:::bucket-name` |
| `s3:GetBucketLocation` | Read bucket Region | Bucket ARN |
| `s3:GetObject` | Read a script or dataset object | `arn:aws:s3:::bucket-name/prefix/*` |
| `s3:PutObject` | Create or replace an object | Object-prefix ARN |
| `s3:DeleteObject` | Remove objects, including during some overwrite operations | Intended output/temp prefix |
| `logs:CreateLogGroup` | Create the service's log group | Appropriate log-group scope |
| `logs:CreateLogStream`, `logs:PutLogEvents` | Write diagnostic events | Appropriate log-stream scope |
| `iam:PassRole` | Pass an execution role to a service | Approved role ARN |
| `secretsmanager:GetSecretValue` | Retrieve database credentials when using a secret | Selected secret ARN |
| `kms:Decrypt` | Decrypt data protected by a customer-managed key when required | Selected KMS key ARN |

The Lambda example in the original notes grants `s3:PutObject` beneath `bronze/citibike/*`, plus logging. It does not grant Silver read/write access. Inspect it through Lambda → `richard-citibike-ingestion` → Configuration → Permissions → execution role. The Glue policy separately grants Bronze/script reads and read/write/delete access to its Silver and temporary prefixes. Policies allow operations; bucket, endpoint, key, or organization policies can still restrict effective access.

## Bronze → Silver with Glue

### What the saved script does

Read [citibike_glue_etl.py](4.1_EMR_citibike/citibike_glue_etl.py) in this order:

1. Resolves the required `--BUCKET` argument and sets the Spark session time zone to UTC.
2. Reads multiline station-status JSON and captures each input filename.
3. Explodes `data.stations` into individual station rows.
4. Extracts `snapshot_timestamp` from the `station_status_YYYYMMDDTHHMMSSZ` filename. This is the captured snapshot identity; `last_reported_timestamp` comes from the station's source epoch value.
5. Reads station information, selects metadata, and deduplicates by `station_id`.
6. Left-joins metadata to status and derives utilization, empty/full flags, and operational status.
7. Overwrites `silver/citibike/glue_station_status/` with Parquet.
8. Reads the published Parquet back and reports row count, invalid keys, duplicate keys, unmatched metadata, and negative counts.

`utilization_pct` is available bikes divided by station capacity, multiplied by 100 when capacity is positive. `is_operational` requires installed, renting, and returning flags to all be true. The write is followed by validation; a failing validation can therefore leave a published output that needs investigation.

Important limitations:

- Metadata deduplication prevents join multiplication, but does not choose the latest metadata or the metadata valid at each historical snapshot.
- The job rereads its input and overwrites its Silver output. It does not implement incremental or atomic publication.
- It uses ordinary Spark reads, with no Glue bookmark lifecycle. Enabling the job's bookmark option alone would not make these reads incremental. See [Glue bookmark behavior](https://docs.aws.amazon.com/glue/latest/dg/monitor-continuations.html).
- Unmatched metadata is reported, but is not itself a failing condition in the saved script.

### Script upload and job configuration

```bash
aws s3 cp citibike_glue_etl.py \
  "s3://${BUCKET}/scripts/glue/citibike_glue_etl.py"
```

In Glue → ETL jobs, inspect the existing Bronze-to-Silver job before creating another. The lecture job name was `CitiBikeBronzeToSilverGlue`; the learner job's exact name was not preserved in these notes. Configure the learner job with:

| Setting | Value or check |
| --- | --- |
| Job type | Spark/Python (`glueetl`) |
| Execution role | `AWSGlueServiceRole-RichardCitiBike` |
| Script location | Learner bucket → `scripts/glue/citibike_glue_etl.py` |
| Glue version | Record the version actually selected; it was not captured here |
| Worker type/count | Lecture example: two `G.1X` workers |
| Timeout | Lecture example: 10 minutes |
| Maximum concurrency | 1; concurrent overwrites of the same Silver prefix are unsafe |
| Job parameter | `--BUCKET` = the learner bucket name |
| Temporary directory | `s3://<learner-bucket>/glue-temp/` |
| Bookmarks | Disable for this full-read/full-overwrite implementation |

After selecting the actual job name, inspect and start it as follows. Replace the placeholder first.

```bash
BRONZE_JOB_NAME='REPLACE_WITH_YOUR_EXISTING_JOB_NAME'
aws glue get-job --job-name "$BRONZE_JOB_NAME"
aws glue start-job-run \
  --job-name "$BRONZE_JOB_NAME" \
  --arguments "{\"--BUCKET\":\"${BUCKET}\"}"
```

Record the returned `JobRunId`, inspect terminal status, and open run details → CloudWatch output logs. Verify the schema and the `SILVER READBACK` quality counts; a script upload alone does not demonstrate a successful transformation.

### DPUs and worker types

A standard Data Processing Unit represents 4 vCPUs and 16 GB of memory. These are allocated resources, not a throughput guarantee. Two `G.1X` workers allocate 2 DPUs: 8 vCPUs and 32 GB in total, including resources used to run Spark itself.

| Worker type | DPUs per worker | vCPUs | Memory |
| --- | --- | --- | --- |
| `G.1X` | 1 | 4 | 16 GB |
| `G.2X` | 2 | 8 | 32 GB |
| `G.4X` | 4 | 16 | 64 GB |
| `G.8X` | 8 | 32 | 128 GB |

A `G.1X` worker has 94 GB of local disk, approximately 44 GB free. More workers do not necessarily reduce runtime proportionally; startup, I/O, and data distribution matter. See the [AWS worker specifications](https://docs.aws.amazon.com/glue/latest/dg/worker-types.html).

## Redshift Serverless setup

### Namespace, workgroup, and credentials

- **Namespace:** contains database objects and related users, storage, security, and role settings.
- **Workgroup:** provides compute capacity and the network endpoint used to query the namespace.
- **Database:** `dev` in this example; it contains schemas such as `public` and `gold`.
- **Schema:** named container for tables/views inside a database.

The notes record creating learner resources in Redshift → Serverless dashboard in `us-east-2`, with `richard_admin` as the database administrator. The database username/password are separate from the AWS console login. Keep the password out of documentation and scripts. Credential options determine whether you choose the password or use an AWS-managed secret.

Inspect the actual VPC, subnets, security groups, endpoint, and capacity settings rather than treating console defaults as universal. Enhanced VPC routing directs Redshift COPY/UNLOAD traffic through VPC routes; the recorded setup left it off while checking routing.

### Create and associate the Redshift S3 role

If the role already exists, inspect it before changing it. For initial creation:

```bash
aws iam create-role \
  --role-name RichardCitiBikeRedshiftRole \
  --assume-role-policy-document file://redshift-trust-policy.json

aws iam put-role-policy \
  --role-name RichardCitiBikeRedshiftRole \
  --policy-name RichardCitiBikeRedshiftS3Access \
  --policy-document file://redshift-s3-policy.json
```

In the namespace's permissions settings, associate `RichardCitiBikeRedshiftRole` and set it as default if using `IAM_ROLE default` in SQL. The saved Glue writer explicitly names this role's ARN. Creating the role alone does not associate it with Redshift. The saved trust file includes both required service principals; see [Serverless role association and trust](https://docs.aws.amazon.com/redshift/latest/mgmt/serverless-security-other-services.html).

## Networking: Glue must reach both Redshift and S3

The recorded subnet initially had an internet-gateway route but no S3 gateway-endpoint route. Glue's VPC network interfaces have private addresses without public IPs, so the internet gateway alone did not provide the needed path. An S3 gateway endpoint was added for regional S3 access. See [Glue JDBC networking requirements](https://docs.aws.amazon.com/glue/latest/dg/connection-JDBC-VPC.html).

In VPC → Subnets → the selected subnet → Route table, inspect the effective routes. Then inspect VPC → Endpoints:

| Recorded endpoint setting | Value |
| --- | --- |
| Name | `richard-citibike-s3-endpoint` |
| Service | `com.amazonaws.us-east-2.s3` |
| Type | Gateway |
| VPC | `vpc-0df4612f429f52b16` |
| Route-table association | `rtb-0b50cc16c48fedd8a` |
| Endpoint policy | Full access in this learning setup; IAM and bucket permissions still apply |

The notes record that this route table served all three relevant subnets. Verify the associations in the current environment. An S3 endpoint supplies the S3 route; other destinations can require their own endpoints or NAT access.

Also check:

- **Ingress** means inbound traffic; **egress** means outbound traffic.
- Redshift must accept TCP traffic on its configured port, here `5439`, from the Glue security group.
- At least one Glue security group must allow self-referencing inbound TCP traffic for communication among Glue components.
- Outbound rules, network ACLs, available subnet IPs, and VPC DNS settings must support the connection.

Creating a connection object does not verify these network requirements.

## Create and test the Glue JDBC connection

In Glue → Data Catalog → Connections, create a JDBC connection. A connector supplies integration software; a connection stores settings for a specific destination. Glue includes Redshift support.

| Setting | Recorded value or instruction |
| --- | --- |
| Name | `richard-citibike-redshift-connection` |
| JDBC URL | Copy from the actual `richard-citibike-wg` endpoint; recorded form: `jdbc:redshift://richard-citibike-wg.866934333672.us-east-2.redshift-serverless.amazonaws.com:5439/dev` |
| Driver class / driver S3 path | Leave blank for built-in Redshift support |
| Credentials | Database username and password from the namespace setup |
| SSL | Require SSL for the database connection |
| VPC / subnet / security group | Recorded learner network values in the resource map |

Attach this connection under the load job's **Additional network connections**. To test it, select the connection → Actions → Test connection, using `AWSGlueServiceRole-RichardCitiBike`.

The instructor initially struggled with the console and eventually created the connection with `aws glue create-connection` using a temporary JDBC configuration JSON. That command used the instructor endpoint and connection name. It is historical context; use the learner connection above for the saved loader. Connection creation, connection-test success, and successful data loading are separate milestones.

## Silver → Redshift: validate, stage, and merge

### Configure the job

In Glue → ETL jobs → Script editor, inspect or create the Spark job `richard-citibike-silver-to-redshift` using the [saved complete script](4.1_EMR_citibike/richard-citibike-silver-to-redshift.py).

| Setting | Value |
| --- | --- |
| Execution role | `AWSGlueServiceRole-RichardCitiBike` |
| Script directory | Learner bucket → `scripts/glue/` |
| Script filename | `richard-citibike-silver-to-redshift.py` |
| Temporary path | Learner bucket → `redshift-temp/citibike/` |
| Additional network connection | `richard-citibike-redshift-connection` |
| Maximum concurrency | 1, because the script uses one shared staging table |

The temporary path stages data for transfer and COPY; it is not the CloudWatch log destination. Both Glue and Redshift need the relevant permissions on this staging prefix. A successful Silver read proves neither Glue staging writes nor Redshift staging reads. See [Glue's Redshift integration](https://docs.aws.amazon.com/glue/latest/dg/aws-glue-programming-etl-connect-redshift-home.html).

### Understand the final script

The original learning sequence first printed the Silver schema, five rows, and row count, then selected the warehouse columns and performed an append load. The saved script now includes the later repeat-load repair:

1. Reads `silver/citibike/glue_station_status/`.
2. Selects eleven columns: station ID, snapshot timestamp, station name, available bikes/e-bikes/docks, capacity, utilization, and empty/full/operational flags.
3. Rejects null station IDs/timestamps and duplicate `(station_id, snapshot_timestamp)` pairs. The Silver script additionally checks empty station IDs; the loader's own key check only checks nulls.
4. Converts the selected DataFrame into a Glue `DynamicFrame` for the writer.
5. Uses `preactions` to create `public.citibike_station_snapshot_stage` with the destination's structure and clear leftover staging rows.
6. Writes the incoming data to staging through temporary S3 files and Redshift COPY.
7. Uses `postactions` to merge staging into `public.citibike_station_snapshot`, then clear staging inside a transaction.
8. Calls `job.commit()` after the write.

| Writer option | Meaning |
| --- | --- |
| `catalog_connection` | Saved JDBC destination and credentials |
| `database` | `dev` |
| `dbtable` | Staging table receiving this load |
| `redshift_tmp_dir` | S3 staging prefix |
| `aws_iam_role` | Redshift-associated role used to access S3 staging files |
| `preactions` / `postactions` | SQL executed before/after COPY |

The merge matches both key columns. Matching pairs are updated and new pairs are inserted. `REMOVE DUPLICATES` requires compatible types and the same column count/order in source and target, which is why staging uses `LIKE` the destination. It does not clean unrelated pre-existing duplicate keys that are absent from the incoming data. See [Redshift MERGE semantics](https://docs.aws.amazon.com/redshift/latest/dg/r_MERGE.html).

**Setup dependency:** restore or verify the actual destination DDL before running this final script in a new environment. The destination must already exist, and the selected column order/types must match its structure. `CREATE TABLE IF NOT EXISTS` does not repair an incompatible existing staging table. The database user also needs the required table/schema privileges.

### Upload and inspect before rerunning

```bash
aws s3 cp richard-citibike-silver-to-redshift.py \
  "s3://${BUCKET}/scripts/glue/richard-citibike-silver-to-redshift.py"
```

Reload the Glue job. Confirm the Script tab contains `MERGE INTO`, the connection is attached, and maximum concurrency is 1. Confirm the job's script location matches the uploaded object. Run it and inspect terminal status and output logs.

## Verify SQL through the Redshift Data API

Query Editor v2 required account-level setup in the original notes, so the CLI was used. The Data API uses the caller's AWS authorization and configured database authentication; it does not test the Glue JDBC network path. Check the connected database user because it can differ from `richard_admin`.

Use this asynchronous pattern for each query. A returned statement ID means submission succeeded; it does not mean SQL execution finished. See [calling the Redshift Data API](https://docs.aws.amazon.com/redshift/latest/mgmt/data-api-calling.html).

```bash
STATEMENT_ID=$(aws redshift-data execute-statement \
  --workgroup-name richard-citibike-wg \
  --database dev \
  --sql 'SELECT current_database(), current_user, current_schema();' \
  --query Id --output text)

aws redshift-data describe-statement --id "$STATEMENT_ID"
```

If status is still `SUBMITTED`, `PICKED`, or `STARTED`, inspect it again. On `FAILED`, read `Error`; on `ABORTED`, investigate the cancellation. Once a SELECT reaches `FINISHED`, retrieve its rows:

```bash
aws redshift-data get-statement-result --id "$STATEMENT_ID"
```

For the SQL checks below, execute each in Query Editor or replace the `--sql` text in this pattern. Each submission produces a new ID. The fixed UUIDs from the rough notes were historical query IDs and should not be reused.

### Count, uniqueness, and staging checks

```sql
SELECT
    (SELECT COUNT(*) FROM public.citibike_station_snapshot) AS destination_rows,
    (SELECT COUNT(*) FROM (
        SELECT station_id, snapshot_timestamp
        FROM public.citibike_station_snapshot
        GROUP BY station_id, snapshot_timestamp
        HAVING COUNT(*) > 1
    ) AS duplicates) AS duplicate_key_groups,
    (SELECT COUNT(*) FROM public.citibike_station_snapshot_stage) AS staging_rows;

SELECT station_id, snapshot_timestamp, COUNT(*) AS copies
FROM public.citibike_station_snapshot
GROUP BY station_id, snapshot_timestamp
HAVING COUNT(*) > 1;
```

For a repeat of the same recorded snapshot, the expected result is 2,519 destination rows, zero duplicate key groups, and zero staging rows. With new snapshots, destination count should grow. Compare per-snapshot counts and keys with Silver; a total count alone does not establish value agreement.

The original notes say to validate that the repeat still has 2,519 rows, but do not include the returned final verification payload. Treat this as the recorded rerun expectation until the query output is saved.

## Gold: station availability by snapshot

The Gold model counts and sums only operational stations:

```sql
SELECT
    snapshot_timestamp,
    COUNT(*) AS operational_stations,
    SUM(bikes_available) AS bikes_available,
    SUM(docks_available) AS docks_available,
    SUM(CASE WHEN is_empty THEN 1 ELSE 0 END) AS empty_stations,
    SUM(CASE WHEN is_full THEN 1 ELSE 0 END) AS full_stations
FROM public.citibike_station_snapshot
WHERE is_operational = TRUE
GROUP BY snapshot_timestamp;
```

`WHERE` selects operational stations. `GROUP BY` produces one row per snapshot. Each `SUM(CASE...)` counts stations satisfying a flag.

### Results recorded in the original notes

| Metric | Recorded value |
| --- | ---: |
| Operational stations | 2,435 |
| Bikes available | 35,568 |
| Docks available | 30,430 |
| Empty operational stations | 122 |
| Full operational stations | 274 |

These are the learner's recorded results for the example snapshot, not values queried again during this revision. The notes did not preserve the corresponding snapshot timestamp or raw result export.

### Save and query the view

First create the schema, using the Data API pattern or Query Editor:

```sql
CREATE SCHEMA IF NOT EXISTS gold;
```

After that statement reaches `FINISHED`, submit the saved SQL file:

```bash
STATEMENT_ID=$(aws redshift-data execute-statement \
  --workgroup-name richard-citibike-wg \
  --database dev \
  --sql file://gold-station-availability-summary.sql \
  --query Id --output text)

aws redshift-data describe-statement --id "$STATEMENT_ID"
```

The SQL file creates the view; it does not create the `gold` schema despite its trailing comment. Once view creation succeeds, query:

```sql
SELECT *
FROM gold.station_availability_summary
ORDER BY snapshot_timestamp;
```

A regular view stores a query definition and evaluates it against the detail table when queried. It does not publish another set of Parquet files or persist an aggregate table.

## EMR Serverless versus Glue

| Question | EMR Serverless | Glue Spark jobs |
| --- | --- | --- |
| Main fit | Serverless execution of supported open-source analytics engines such as Spark and Hive | Managed data integration with Spark and AWS-specific ETL facilities |
| Code model here | Spark DataFrames | Spark DataFrames, plus DynamicFrames where useful |
| Capacity terminology | Application/job worker CPU and memory | Worker types and DPUs |
| What remains your responsibility? | Transformations, permissions, data quality, replay behavior | Transformations, permissions, data quality, replay behavior |

Both can transform Bronze JSON into Silver Parquet. DynamicFrames are an additional Glue abstraction; they are not required for every transformation. Choose based on engine/runtime needs, integration, operations, and measured cost rather than a rule that one service is always for continuous work and the other for occasional work. See the [EMR Serverless overview](https://docs.aws.amazon.com/emr/latest/EMR-Serverless-UserGuide/) and the [earlier AWS concepts guide](2_Tue_AWS.md).

## Failure model and recovery

| Symptom | Boundary to investigate | Recovery or verification |
| --- | --- | --- |
| IAM role already exists | Identity setup | Inspect and reuse the intended role |
| `iam:PassRole` denied | Deployment identity → Glue role | Request the approved role grant; changing the execution policy does not fix caller permissions |
| Missing `BUCKET` argument | Job configuration → script | Add `--BUCKET` with the exact learner bucket name |
| Missing field / timestamp | Bronze schema or filename → transformation | Inspect source structure, filenames, and printed schema |
| Silver quality failure after write | Published Parquet → consumer | Investigate counts and retain Bronze for replay; a failed job can leave output files |
| S3 endpoint/NAT error | Glue subnet → S3 | Check effective routes and endpoint association |
| JDBC timeout | Glue network → Redshift | Check endpoint, port, security groups, DNS, and ACLs |
| Authentication or SQL permission error | Connection user → database | Check database credentials and SQL privileges separately from IAM |
| COPY access denied | Redshift role → temporary S3 objects | Check namespace role association and exact staging-prefix permissions |
| Destination relation missing | Loader → target DDL | Recover/create the verified destination definition before staging with `LIKE` |
| Duplicate incoming keys | Silver → warehouse load | Repair/rebuild the invalid input before rerunning |
| Partial load or interrupted run | Staging/COPY/MERGE → destination | Inspect destination, staging, and job errors before retry; retain concurrency 1 |

The final loader clears staging on the next run and merges validated keys. That supports repeat loads for this table under serial execution. It is not an end-to-end exactly-once guarantee, an atomic S3 publication mechanism, or a policy for deleting destination history absent from a later input.

## Verification and remaining work

| Item | Evidence available in this revision | Remaining evidence |
| --- | --- | --- |
| Artifact inventory | Seven local files inspected | Original destination DDL/creation record |
| Bronze/Silver execution | Earlier [pipeline evidence](3.4_Wed_citibike/aws-pipeline/README.md) records executed runs and 2,519-row read-back | New snapshots and historical metadata behavior |
| Redshift setup and loading | Setup sequence and reporting values recorded in the learner notes | Saved job/connection settings, destination DDL, run IDs, and raw SQL outputs |
| Repeat-load repair | Validation, staging, and MERGE present in the saved Python script | Final rerun result payload confirming unchanged count and zero duplicates/staging rows |
| Gold view | Saved SQL and recorded aggregate values | Saved view-query result with snapshot timestamp |
| Automation and operations | Manual sequence documented | Scheduled end-to-end orchestration, failure alerts, recovery exercises, measured cost |

### Production considerations

- Retain Bronze and define a replay/backfill policy before changing input history.
- Define schema/type compatibility, timestamp conventions, and historical metadata selection explicitly.
- Replace shared staging with run-specific staging if concurrent writers become necessary.
- Record input scope, script version, job/run ID, SQL statement IDs, validation counts, and reporting timestamp together.
- Monitor freshness, failed runs, invalid keys, duplicate keys, unmatched metadata, and reconciliation differences.
- Review Glue capacity, Redshift capacity, temporary-object retention, and network costs. Serverless resources can still incur charges.

### Knowledge check

- Why can a Silver read succeed while the subsequent Redshift load fails?
- Which identity needs `iam:PassRole`, and which identity reads the COPY staging files?
- Why is the snapshot timestamp part of the key?
- What happens if two runs clear and load the same staging table concurrently?
- Why does `job.commit()` or enabling bookmarks not make this pipeline duplicate-safe by itself?
- What extra evidence would show that Redshift values agree with Silver, beyond matching total counts?

### Completion checklist

- [x] Locate the seven saved scripts and policies.
- [x] Separate instructor names from learner resources.
- [x] Explain trust, permissions, database authentication, and network dependencies.
- [x] Integrate the final staging/MERGE approach into the notes.
- [ ] Recover the original destination DDL or export the current table definition.
- [ ] Record the learner namespace and exact Bronze-to-Silver job/version settings.
- [ ] Save final rerun and Gold query results with timestamps and run/statement IDs.
- [ ] Verify recurring orchestration, recovery behavior, and cost separately.

## References

Official AWS documentation was reviewed on 2026-10-09 for the worker, networking, Redshift integration, bookmark, role-association, MERGE, and Data API explanations linked above. Local parsing and link checks establish document/artifact consistency only; no AWS resources were created or changed, jobs started, or SQL executed during this revision.
