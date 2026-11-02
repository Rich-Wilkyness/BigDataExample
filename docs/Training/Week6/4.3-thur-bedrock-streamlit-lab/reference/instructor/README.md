# Citi Bike Step Functions classroom demo

## Preconditions
- AWS profile `company` authenticates to account 866934333672, region us-east-2.
- Existing Lambda: `citibike-ingestion`.
- Existing Glue jobs: `CitiBikeBronzeToSilverGlue`, `CitiBikeSilverToRedshiftTest`.
- Caller has permissions to create IAM roles/policies, Step Functions state machines, CloudWatch log groups and to pass the state machine role.
- Existing Lambda, Glue, and Redshift jobs work independently; this project does not repair their execution roles, networking, or data schemas.

## Deploy
```bash
unset AWS_ACCESS_KEY_ID AWS_SECRET_ACCESS_KEY AWS_SESSION_TOKEN AWS_SECURITY_TOKEN
export AWS_PROFILE=company AWS_REGION=us-east-2 AWS_DEFAULT_REGION=us-east-2
aws sts get-caller-identity --profile company
terraform init
terraform fmt -check
terraform validate
terraform plan
terraform apply
```

## Execute once
```bash
aws stepfunctions start-execution \
  --state-machine-arn "$(terraform output -raw state_machine_arn)" \
  --input '{}' --profile company --region us-east-2
```
Use the AWS Step Functions console to inspect execution graph and task history.

## Clean up
```bash
terraform destroy
```
Destroy removes ONLY the state machine, its role/policy, and its log group, not the existing pipeline. Do not delete the Terraform state file before destroy.

## Important cautions
- The existing `Citi-bike-ingestion-5-min` schedule is ENABLED. This project creates no schedule. A manually invoked Lambda may overlap with its scheduled execution.
- The Lambda integration checks a FunctionError field but cannot validate arbitrary business-level success in a custom Lambda payload; inspect Lambda return behavior before relying on it.
- The two Glue jobs may have bookmarks or other stateful behavior. A successful Step Functions run does not guarantee new records if the source data or job configuration is unchanged.
- Retrying a Glue Task after a task failure can cause duplicate side effects if the Glue job is not idempotent. For teaching, consider temporarily limiting retries and ensure the jobs tolerate repeat runs.
- The Step Functions `.sync` integration requires appropriate Glue polling permissions; those are included. Existing Glue roles remain untouched.
- AWS account SCPs, permission boundaries, or explicit denies can still block Terraform. This configuration cannot override them.
