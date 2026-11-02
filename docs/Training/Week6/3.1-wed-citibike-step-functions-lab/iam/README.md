# IAM and database prerequisites

The Terraform project requires an explicit `workflow_role_arn`. Creating this local project does not establish that the role exists or can call the new jobs. Give the administrator [the action checklist](required-actions.json), your Terraform plan, and the resource names below. No policy changes are applied by this lab.

## Workflow execution role

- Trust principal: `states.amazonaws.com`, with `aws:SourceAccount=866934333672` and `aws:SourceArn` limited to the two workflow ARNs: `arn:aws:states:us-east-2:866934333672:stateMachine:richard-citibike-v2-lab-backfill` and `arn:aws:states:us-east-2:866934333672:stateMachine:richard-citibike-v2-lab-incremental`.
- Glue start/monitor/stop actions apply to the four exact job ARNs produced by Terraform: `arn:aws:glue:us-east-2:866934333672:job/richard-citibike-v2-lab-backfill-silver`, `...-backfill-redshift`, `...-incremental-silver`, and `...-incremental-redshift`. Expand each full ARN in the policy; ellipses here are prose, not policy syntax.
- Data API submission applies to Richard's Redshift workgroup. `DescribeStatement` has different supported resource scoping; follow the service authorization reference instead of putting every action under a workgroup ARN.
- Serverless temporary IAM authentication requires `redshift-serverless:GetCredentials` on `arn:aws:redshift-serverless:us-east-2:866934333672:workgroup/6de8611e-e342-4b21-ac2d-cb2a8ac3e59c`. Confirm the workgroup ID if recreated.
- Data API IAM authentication maps to a database identity. Grant that identity schema usage, procedure execution, table SELECT/INSERT/UPDATE/DELETE, and temporary-table creation required by the `SECURITY INVOKER` procedure. The Glue JDBC connection's database login may be a different identity.
- The workflow accepts a reviewed `accept_sql` string from its operator. It is a classroom input contract, not a public API. Restrict SQL grants to this lab and use [prepare-input.py](../prepare-input.py) to keep the procedure call aligned with the selected batch.

## Existing Glue and Redshift roles

The Terraform defaults explicitly name `AWSGlueServiceRole-RichardCitiBike` and `RichardCitiBikeRedshiftRole`. Inspect their current trust/access policies before applying. Glue needs the new script prefix, retained Bronze, `silver/citibike/v2-lab/*`, and its temporary prefixes; Spark overwrite requires delete as well as write permissions. Redshift needs the loader's `redshift-temp/citibike/*` files and any applicable KMS access. Existing connection/network attachment is reused. IAM grants do not supply VPC routes or database grants.

## Your operator identity

The live inspection was denied `states:ListStateMachines`. Resolve that with your teacher. Terraform also needs S3 object, Glue job, and state-machine read/write operations plus scoped `iam:PassRole` for the explicitly configured Glue and Step Functions roles. Review the actual plan rather than assigning administrator access. Neither the dashboard nor creating these local files proves effective permission.

For reproducible deployment-policy generation after producing a plan JSON, the AWS IAM skill recommends IAM Policy Autopilot. From the Terraform directory, these are preparation commands, not a deployment:

```bash
terraform plan -out=lab.tfplan
terraform show -json lab.tfplan > plan.local.json
uvx iam-policy-autopilot@latest generate-policies /Users/richardwilkerson/VSCodeProjects/BigDataExample/docs/Training/Week6/3.1-wed-citibike-step-functions-lab/terraform/plan.local.json --region us-east-2 --account 866934333672 --pretty > deployment-policy.local.json
```

The CLI accepts the plan JSON as a positional input, per its official documentation reviewed on 2026-10-14. Autopilot is not installed or executed by this lab. Keep the plan JSON and generated policies local; they may contain sensitive planned values. This deployment policy is distinct from the workflow runtime role's permissions.

References: [Step Functions trust roles](https://docs.aws.amazon.com/step-functions/latest/dg/procedure-create-iam-role.html), [Glue integration actions](https://docs.aws.amazon.com/step-functions/latest/dg/connect-glue.html), [Redshift Data API IAM](https://docs.aws.amazon.com/redshift/latest/mgmt/data-api-iam.html), [Data API action scopes](https://docs.aws.amazon.com/service-authorization/latest/reference/list_redshift-data.html), and [IAM Policy Autopilot](https://github.com/awslabs/iam-policy-autopilot).
