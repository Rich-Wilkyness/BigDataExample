# Completed captures → EventBridge → Step Functions

> Status, 2026-10-19: Implemented locally and validated, not deployed. Richard's login was denied events:DescribeRule and events:TestEventPattern. The live pipeline still uses the deployed 22-state preparation workflow and two manual commands. The staged source adds one lock-wait state for a proposed 23-state workflow.

## Intended behavior

```text
Manual invocation of richard-citibike-ingestion
  → download all API feeds
  → write four Bronze JSON objects
  → write one capture-complete marker last
  → S3 Object Created event on the default EventBridge bus
  → rule matches only Richard's completion prefix
  → start the existing Step Functions workflow with completion_key
  → prepare/freeze batch, run Glue, accept Redshift, release lock
```

This is an event rule, not EventBridge Scheduler. After deployment and verification, invoking ingestion will be the only manual data-capture trigger. It will not collect new captures on a timer. The rule defaults to DISABLED until the code and workflow are ready.

## Why publish one completion marker?

[The new ingestion source](lambda/ingestion.py) downloads all required feeds before publishing objects. Each S3 write uses IfNoneMatch so it does not overwrite an earlier capture at the same filename timestamp. After all four uploads succeed, it writes:

```text
bronze/citibike/completed/capture_YYYYMMDDTHHMMSSZ.json
```

The marker lists version, bucket, capture_id, snapshot_time, and the four exact object keys. A failed feed download or upload does not publish a marker. A partially uploaded failed capture remains a recovery responsibility.

The ingestion response will contain data_files_uploaded = 4, files_uploaded = 5, capture_id and completion_key. The five objects are the four data/discovery JSON files plus the completion marker. The existing Week 5 source remains a historical copy; the new ZIP contains lambda_function.py so it preserves the deployed function's handler name.

The existing ingestion role already permits PutObject on Richard's Bronze prefix. Its observed configuration was Python 3.14, x86_64, 256 MiB, 120 seconds, with only CITIBIKE_BUCKET as a user environment variable. The proposed code update changes the ZIP only. Terraform continues to manage the existing preparation function; ingestion remains externally managed to preserve its current ownership/configuration.

## Terraform inventory

[terraform/eventbridge.tf](terraform/eventbridge.tf) declares seven additions:

| Resource | Purpose |
| --- | --- |
| aws_s3_bucket_notification.capture_events | Enable the existing bucket's delivery of S3 events to EventBridge |
| aws_cloudwatch_event_rule.capture_complete | Match Object Created for the account, Ohio region, Richard bucket and completion prefix |
| aws_cloudwatch_event_target.capture_complete | Start the existing workflow after transforming the event to completion_key |
| aws_iam_role.capture_events | EventBridge target role, restricted to this account and rule ARN |
| aws_iam_role_policy.capture_events | Allow that role to start only Richard's workflow |
| aws_sqs_queue.capture_delivery_dlq | Retain undeliverable target events for 14 days, using managed encryption |
| aws_sqs_queue_policy.capture_delivery_dlq | Allow this rule's EventBridge deliveries to the queue |

Three existing resources change: the preparation policy gains completion/feed object reads, the preparation Lambda receives updated code, and the state machine receives the original-input reference and BUSY/wait branch. The reviewed plan was **7 additions, 3 updates, 0 deletions**. Updating the externally managed ingestion ZIP is a separate code deployment and is not counted in that plan.

S3 has one bucket-wide notification configuration. Preflight found all notification fields unset; no Lambda, SQS, SNS or EventBridge destination was configured. Recheck before applying, and preserve any destinations introduced since that inspection. This Terraform resource would replace that bucket-level configuration, not merge it automatically with external changes.

## Event input, serialization and duplicates

The target's input transformer produces this shape:

```json
{
  "completion_key": "bronze/citibike/completed/capture_20261019T180000Z.json"
}
```

This timestamp is illustrative, not a new capture to replay. Preparation reads the marker from the configured bucket, checks its identity/path and four object keys, verifies those objects exist, and chooses the marker's capture timestamp plus one second as the exclusive upper bound. It also requires completion markers for every selected capture in event-triggered catch-up. Existing unaccepted captures without markers must be reconciled through the manual path before enabling the rule; do not invent markers for failed uploads.

The event path retains source counting, frozen inputs and atomic warehouse acceptance. Manual `{}` and preview inputs remain supported by the staged handler.

If another execution holds the run lock, preparation returns BUSY rather than starting Glue. PreparedStatus routes to WaitForBatchLock, waits 30 seconds, and returns to PrepareBatch. The Task reads the original request from `$$.Execution.Input` so repeated preparation does not accidentally treat the BUSY result as a new request. Preparation-only waiting does not retry Glue or warehouse writes.

Duplicate notifications can create multiple Step Functions executions. They do not share a deterministic execution name. The S3 lock serializes participating processing; once a capture has been accepted, the checkpoint causes a repeated or older completion event to return NO_DATA without publishing another batch or starting Glue. Offline tests exercise this behavior; it is not a claim of exactly-once event delivery.

A failed owning execution retains its lock. Waiting executions have the same 3,000-second overall workflow limit and can time out while that lock is retained. WaitForBatchLock is not a durable queue and cannot repair a failed run. This is appropriate for the bounded, manually captured lab; sustained ingestion would need a stronger queue/recovery policy.

## What the delivery DLQ covers

The target retries failed delivery for up to one hour and at most 12 retry attempts, then retains undeliverable events in the standard SQS queue. The queue has a 14-day retention period.

This covers failure to deliver StartExecution. Once Step Functions accepts the event, subsequent Lambda, Glue, SQL or lock-release failures belong to workflow monitoring and recovery. They are not automatically placed in this delivery DLQ. Inspect execution failures and retained locks separately.

## Permission handoff

The confirmed caller was `arn:aws:iam::866934333672:user/richard.wilkerson@techconsulting.tech`. Read-only preflight was denied:

- events:DescribeRule on `arn:aws:events:us-east-2:866934333672:rule/richard-citibike-capture-complete`.
- events:TestEventPattern on resource `*`.

The [scoped EventBridge deployment gap policy](iam/capture-events-deployer-gap.json) is for an administrator to review. It permits lifecycle operations on only this rule, pattern testing, and passing only RichardCitiBikeCaptureEventRole to EventBridge. It is an addition to existing deployment permissions, not an account-wide administrator policy or a complete replacement for existing Terraform access. The deployment identity also needs its normal S3/IAM/Lambda/Step Functions permissions plus lifecycle access to the one SQS delivery queue declared in the plan; only the EventBridge denials above were confirmed in this preparation.

No user permissions were changed, no deployment role was assumed, and no Terraform apply was attempted while rule ownership/state could not be read. A successful plan does not establish authorization to create the rule or set its target.

The local environment did not have uvx available. The gap policy's rule-action names/resource support were checked against AWS's public programmatic EventBridge service-authorization metadata. To generate a broader deployment baseline from the saved plan on an administrator's tooling environment:

```bash
uvx iam-policy-autopilot@latest generate-policies \
  /tmp/richard-capture-events-plan.json \
  --region us-east-2 \
  --account 866934333672 \
  --pretty
```

The plan JSON is local to this session, is owner-readable only, and should not be committed or pasted into messages. Recreate a fresh plan JSON with Terraform show -json if it no longer exists. Review generated permissions; do not automatically upload or attach them.

## Deployment sequence after access is available

Run from the repository root:

```bash
cd /Users/richardwilkerson/VSCodeProjects/BigDataExample
CITIBIKE_LAB='docs/Training/Week6/3.4-wed-incremental-pipeline'

.venv/bin/python -m unittest discover -s "$CITIBIKE_LAB/lambda" -p 'test_*.py'
.venv/bin/python "$CITIBIKE_LAB/lambda/package.py"

terraform -chdir="$CITIBIKE_LAB/terraform" fmt -check
terraform -chdir="$CITIBIKE_LAB/terraform" validate
terraform -chdir="$CITIBIKE_LAB/terraform" plan \
  -out=/tmp/richard-capture-events-disabled.tfplan
```

First recheck the caller, current rule, bucket notifications, running executions and lock ownership. Reconcile any unaccepted source captures that predate marker publication. Review the fresh disabled-rule plan, then apply that saved plan. Do not apply the old plan after additional source, configuration or infrastructure changes.

```bash
terraform -chdir="$CITIBIKE_LAB/terraform" apply \
  /tmp/richard-capture-events-disabled.tfplan
```

Save a recovery copy of the deployed ingestion ZIP before updating it. Inspect the current ingestion configuration and retrieve its revision immediately before the code update:

```bash
CITIBIKE_INGESTION_REVISION=$(aws lambda get-function-configuration \
  --function-name richard-citibike-ingestion \
  --query RevisionId --output text --region us-east-2 --no-cli-pager)

aws lambda update-function-code \
  --function-name richard-citibike-ingestion \
  --zip-file "fileb://$CITIBIKE_LAB/terraform/.build/ingestion.zip" \
  --revision-id "$CITIBIKE_INGESTION_REVISION" \
  --region us-east-2 \
  --no-cli-pager

aws lambda wait function-updated-v2 \
  --function-name richard-citibike-ingestion \
  --region us-east-2
```

The ZIP builder preserves lambda_function.lambda_handler. Do not change runtime, architecture, role or other configuration as part of this code-only step. Lambda's revision check prevents overwriting a concurrent update, but you still need to review ownership/configuration before submitting it.

With the rule disabled, invoke ingestion once and verify that it writes five objects with the marker last. Start one manual workflow using that actual completion_key and verify the event-shaped input through acceptance. This staged test prevents enabling an unverified code/input combination.

After the manual event-shaped execution succeeds and releases its lock, enable the rule with a reviewed Terraform plan:

```bash
terraform -chdir="$CITIBIKE_LAB/terraform" plan \
  -var='capture_events_enabled=true' \
  -out=/tmp/richard-capture-events-enabled.tfplan

terraform -chdir="$CITIBIKE_LAB/terraform" apply \
  /tmp/richard-capture-events-enabled.tfplan
```

Keep that variable setting consistent in later Terraform plans; the source default is false. A later plan without the override will propose disabling the rule. For persistent local use, a reviewed ignored `.auto.tfvars` file can hold the same setting.

S3 documentation notes that enabling bucket delivery to EventBridge can take around five minutes. After propagation, invoke ingestion again and verify that the matching completion event starts the workflow automatically. Do not start it manually during this automatic-path test. Find the execution by its completion_key and require acceptance, correct warehouse counts, and released ownership before declaring success.

Then replay the same event-shaped workflow input without collecting new data and verify NO_DATA/no extra facts. Observe delivery-queue message counts. Offline duplicate checks are not a replacement for this runtime verification.

## Pause automatic processing

Once deployed, disable the rule through Terraform by planning/applying capture_events_enabled=false. This stops new matching events from starting workflows; it does not cancel executions already started, stop a running Glue job, or prevent someone manually invoking ingestion. There is no Scheduler in this extension.

For an immediate operator pause when Terraform is not practical:

```bash
aws events disable-rule \
  --name richard-citibike-capture-complete \
  --region us-east-2 \
  --no-cli-pager
```

Reflect the pause in Terraform's variable setting before the next apply to avoid unintentionally re-enabling the rule. Inspect active work separately and follow the existing lock/warehouse recovery procedure before stopping or retrying it.

## Verification and remaining work

Local checks: the preparation/ingestion suite passed; Python parsing, ZIP packaging, Terraform formatting/provider validation and a disabled-rule plan passed. AWS validated the 23-state workflow definition with no diagnostics. Event-pattern API testing was denied. No rule, target, queue, bucket notification, code update, enabled-rule plan apply, source capture or warehouse execution was deployed/run for this extension.

[Staged evidence](evidence/2026-10-19-capture-events-staged.json) records exact boundaries. Pending: administrator authorization, fresh resource ownership checks, disabled deployment, ingestion code update, manual event-shaped acceptance, rule enablement and propagation, automatic end-to-end execution, live duplicate/out-of-order verification, and delivery-failure exercise.

## References

- [S3 events starting Step Functions through EventBridge](https://docs.aws.amazon.com/step-functions/latest/dg/tutorial-cloudwatch-events-s3.html)
- [S3 duplicate and ordering behavior](https://docs.aws.amazon.com/AmazonS3/latest/userguide/notification-how-to-event-types-and-destinations.html)
- [EventBridge input transformers](https://docs.aws.amazon.com/eventbridge/latest/userguide/eb-input-transformer-tutorial.html)
- [EventBridge delivery dead-letter queues](https://docs.aws.amazon.com/eventbridge/latest/userguide/eb-rule-dlq.html)
- [Lambda code update and revision checking](https://docs.aws.amazon.com/lambda/latest/api/API_UpdateFunctionCode.html)
