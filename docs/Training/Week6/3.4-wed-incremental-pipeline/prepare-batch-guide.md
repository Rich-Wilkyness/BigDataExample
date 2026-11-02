# PrepareBatch: the coordinator before Glue

> EventBridge source update staged, not deployed: the local handler also accepts completion_key and returns BUSY for a held lock; the proposed workflow waits before retrying preparation. The deployed 22-state baseline and its runtime evidence below remain unchanged. See the [capture-event guide](capture-events-guide.md) for the permission block and deployment sequence.

The preparation Lambda turns a request to process new captures into a fixed batch. It reads progress and source data, reserves the pipeline, freezes the selected JSON inputs, and returns the arguments consumed by the existing Glue and Redshift stages. It never advances the warehouse checkpoint.

## Workflow

```text
Manual ingestion Lambda invocation → API feeds saved in Bronze

Manual Step Functions execution with {}
  → PrepareBatch Lambda
  → PreparedStatus
      → NO_DATA: finish without Glue
      → PREVIEW: display proposed batch without writes or Glue
      → READY: validate generated arguments
          → BronzeToSilver reads frozen manifest
          → SilverToLanding
          → SubmitAcceptance and poll SQL status
          → ReleaseBatchLock
          → PipelineSucceeded
```

EventBridge and an ingestion completion marker are a later checkpoint. The preparation manifest described here records the selected processing batch; it is not an ingestion completion event. Invoke ingestion successfully before manually starting the workflow.

## Responsibilities

| Component | Responsibility |
| --- | --- |
| Existing ingestion Lambda | Download the API feeds and write the Bronze JSON objects. |
| [PrepareBatch Lambda](lambda/prepare_batch.py) | Read checkpoint, reserve pipeline, select captures, count distinct station/capture observations, and freeze inputs. |
| [Bronze-to-Silver Glue](glue/bronze-to-silver.py) | Read the frozen manifest, transform data with Spark, and verify published Silver against the prepared count. |
| Existing Silver-to-landing Glue | Append the batch's Silver observations to Redshift landing. |
| Existing warehouse acceptance procedure | Validate and accept warehouse changes, then atomically record the ledger and advance the checkpoint. |

## Start a run

From the repository root, after ingestion has completed:

```bash
aws stepfunctions start-execution \
  --state-machine-arn arn:aws:states:us-east-2:866934333672:stateMachine:richard-citibike-incremental-workflow \
  --input '{}' \
  --region us-east-2 \
  --no-cli-pager
```

To inspect preparation without taking the run lock, writing frozen objects, or running Glue:

```bash
aws stepfunctions start-execution \
  --state-machine-arn arn:aws:states:us-east-2:866934333672:stateMachine:richard-citibike-incremental-workflow \
  --input '{"preview":true}' \
  --region us-east-2 \
  --no-cli-pager
```

A preview reads S3 and Redshift. It is an estimate at that moment and does not reserve the proposed batch. If there are no eligible captures, it returns `NO_DATA`.

The only optional processing parameter is an exclusive UTC `window_end`, for example `{"window_end":"2026-10-19T18:00:00Z"}`. This lets an operator bound catch-up work. It must not be in the future. Legacy fixed-input fields such as `batch_id` and `expected_rows` are rejected; preparation now owns them. Archived October 16 input files remain historical evidence.

## How preparation chooses the batch

- Read exactly one checkpoint row for `richard-citibike` in database `dev` through the Redshift Data API.
- Start at that accepted boundary. List status captures by UTC day prefix and select filenames within the half-open requested window.
- Require corresponding station metadata for every selected status capture. Missing metadata fails preparation rather than silently skipping that capture and moving progress past it.
- Read each status object using its listed ETag as a condition. Reject missing station IDs and conflicting observations for the same station within a capture. Exact duplicate rows count once.
- Freeze the source JSON under `control/citibike/incremental/batches/<batch_id>/`. Freeze the latest selected capture's metadata too, preserving the existing lab's latest-metadata-for-the-batch behavior.
- Publish `manifest.json` last. It contains frozen object URIs, original object keys/ETags, row counts, execution ownership, and the generated workflow fields.
- Set the proposed exclusive end to one second after the latest selected capture. Unobserved time after that capture is not marked complete.

Batch IDs are derived from the Step Functions execution ARN. Frozen JSON and the manifest are created with S3 conditional writes and cannot be overwritten by the preparation role. Glue receives read access to that prepared prefix. The original Bronze files remain unchanged.

The lab bounds preparation to 14 days, 128 status captures, 64 MiB of listed status data, 8 MiB per JSON object, and 200,000 distinct observations. Larger work must use smaller catch-up windows or a redesigned preparation/counting strategy. Lambda has 512 MiB memory and a 300-second timeout. The checkpoint read has a 90-second polling budget.

## Lock ownership and recovery

`control/citibike/incremental/active.json` holds the current run owner. Conditional S3 writes ensure only one participating execution can acquire an idle lock. The lock has no automatic expiry. A competing execution fails before preparing data; Lambda concurrency settings alone are not used to serialize the full workflow.

After warehouse acceptance reaches `FINISHED`, `ReleaseBatchLock` changes the lock to idle using its ETag. An empty processing window also releases its lock. Preview does not acquire one. The lock coordinates this updated workflow; someone manually starting Glue or writing warehouse tables can bypass it.

Any failure after lock acquisition leaves it active for inspection, including a workflow timeout or external stop. This intentionally blocks new processing until the owner, source publication, Glue outputs, accepted-batch ledger, and checkpoint are reconciled. Warehouse rollback does not undo S3 or Glue writes.

Do not blindly clear the lock or redrive a failed Glue step. A partially written Silver directory still exists, and the job refuses overwrite. A landing retry may append duplicate rows. Automatic partial-publication repair and end-to-end resume are not implemented.

After verifying the owning execution is terminal and deciding how to handle its outputs and warehouse state, an operator can invoke the preparation Lambda's `release` action with that exact execution ARN. Release checks ownership and does not delete data or move the checkpoint. The normal workflow performs this action only after acceptance finishes.

```json
{
  "action": "release",
  "execution_id": "arn:aws:states:us-east-2:866934333672:execution:richard-citibike-incremental-workflow:RECONCILED_EXECUTION_NAME"
}
```

This JSON is a recovery payload template, not a routine step. A delivery dead-letter queue and durable capture-identity deduplication still need design before an EventBridge trigger is enabled; execution-derived batch IDs alone do not deduplicate repeated capture events.

## Local checks and deployment

From the repository root:

```bash
.venv/bin/python -m unittest discover \
  -s docs/Training/Week6/3.4-wed-incremental-pipeline/lambda \
  -p 'test_*.py' -v

.venv/bin/python docs/Training/Week6/3.4-wed-incremental-pipeline/lambda/package.py
```

The package builder creates a reproducible archive at `terraform/.build/prepare-batch.zip`; the generated archive is ignored by Git. Build it before Terraform validation or planning after changing the handler. The handler uses the AWS SDK included in the Lambda runtime; no package installation or new Terraform provider is needed.

Terraform defines a dedicated Lambda role and log group, checkpoint-read API permissions, Glue access to frozen inputs, and permission for the workflow to invoke the Lambda. [Database setup](sql/17-grant-preparation-checkpoint.sql) grants the password-disabled preparation identity schema usage and checkpoint-table SELECT; it is separate from IAM. Do not rerun CREATE USER after setup has succeeded.

See [verification.md](verification.md) for the actual deployment and runtime evidence. Offline tests and AWS definition validation do not establish a successful live Glue load or warehouse acceptance.

## References

- [Step Functions optimized Lambda integration](https://docs.aws.amazon.com/step-functions/latest/dg/connect-lambda.html)
- [S3 conditional writes](https://docs.aws.amazon.com/AmazonS3/latest/userguide/conditional-writes.html)
- [Lambda execution roles](https://docs.aws.amazon.com/lambda/latest/dg/lambda-intro-execution-role.html)
