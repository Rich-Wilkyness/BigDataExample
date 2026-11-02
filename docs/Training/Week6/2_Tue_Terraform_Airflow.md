# Infrastructure as Code and Workflow Orchestration

> Week 6 Tuesday lecture notes. Level: foundational, with production context. Examples are for reading; no AWS deployment or Airflow installation is required. Primary documentation reviewed: 2026-10-14. Runtime behavior remains unverified.

## Overview and study route

A data pipeline needs infrastructure to exist, a trigger to start work, and coordination to move through its tasks safely. These are three different responsibilities, even when one tool supports more than one of them.

- **Provisioning:** create and configure resources, such as an S3 bucket or Glue job definition.
- **Scheduling:** decide when to request a run, such as every morning.
- **Orchestration:** coordinate tasks, dependencies, completion, retries, and failure paths within a run.

Read these notes in order, then use the checkpoints to explain the ideas in your own words. The companion [homework](2.1_Tue_HW.md) contains the questions and submission requirements; this lecture provides background rather than a completed submission.

| Homework material | Lecture section |
| --- | --- |
| Part 1: IaC | Infrastructure as Code |
| Part 2: Terraform | Terraform fundamentals and Terraform state |
| Part 3: orchestration | Workflow orchestration and dependencies |
| Part 4: Step Functions | AWS Step Functions |
| Part 5: Airflow | Apache Airflow |
| Part 6: Cron | Cron and EventBridge Scheduler |
| Part 7 and final exercise | Comparing the technologies, Operations and recovery, and Design practice |

## Learning objectives

After studying these notes, you should be able to:

- Explain why organizations use Infrastructure as Code and Git.
- Read a Terraform configuration and distinguish a provider, resource, and data source.
- Explain `init`, `plan`, `apply`, `destroy`, and Terraform state.
- Separate provisioning, scheduling, and orchestration.
- Explain state machines, dependencies, completion checks, retries, and failure handling.
- Read an Airflow DAG and explain its direction, dependencies, and schedule.
- Interpret Linux Cron and recognize that EventBridge Scheduler uses different syntax.
- Describe how to verify a pipeline's execution and its output data.

### Prerequisites and scope

You need a conceptual understanding of S3, Lambda, Glue, and Redshift from the previous AWS lessons. An **API** lets software request actions from another system. An **IAM role** supplies permissions for an AWS identity or service to act.

You do not need credentials or installed tools to read this lesson. The snippets teach configuration and workflow structure; they are not a deployable production project.

## Mental model: resources, triggers, and runs

Consider the existing Citi Bike work: collect a snapshot, store raw JSON in Bronze, transform it into Silver Parquet, and load it into Redshift for analysis.

```text
Before recurring processing:
  Infrastructure configuration → create/configure resources

For each run:
  Time or event trigger → workflow → coordinated tasks → verified output

Data movement:
  Citi Bike API → Lambda → S3 Bronze → Glue → S3 Silver → load → Redshift
```

- Terraform can manage the definitions of the resources used by this pipeline.
- A scheduler can request a new execution at a chosen time.
- An orchestrator can ensure a load waits for complete transformation output.
- Lambda, Glue, and Redshift perform the collection, transformation, and loading work.

Creating a Glue job definition differs from starting a Glue job run. Creating a workflow definition differs from executing it for a particular date or snapshot.

## Infrastructure as Code

### Why manual setup becomes difficult

In a demonstration, you can create a bucket, IAM role, and Glue job through the Console. With more resources and environments, remembering every setting becomes difficult.

- Development and production may have different settings by accident.
- Another engineer may be unable to reproduce the setup.
- Console changes may lack the review history needed to explain them.
- Rebuilding an environment may depend on someone's memory.

**Infrastructure as Code (IaC)** records desired infrastructure in files that tools use to create and manage resources.

| Benefit | Practical meaning |
| --- | --- |
| Repeatability | Reuse configuration to build similar environments with different parameter values |
| Version control | Track configuration changes and their recorded reasons |
| Consistency | Share resource patterns across development, testing, and production |
| Automation | Replace repeated Console steps with a repeatable provisioning workflow |
| Reviewability | Review configuration and proposed infrastructure changes before applying them |

Git records configuration history. It does not automatically record every Console change or undo deployed changes. Restoring an older configuration requires another plan and review, especially if replacement or deletion affects stored data.

IaC does not design the architecture for you. Engineers still decide which services, connections, permissions, and recovery behavior are required. Configuration can reproduce a mistake as consistently as a good design.

Reference: [HashiCorp: What is Terraform?](https://developer.hashicorp.com/terraform/intro).

**Checkpoint:** Describe a manual-setup problem and how a reviewed configuration would help prevent it.

## Terraform fundamentals

### Declarative configuration and providers

Terraform uses **HCL**, HashiCorp Configuration Language. **Declarative** means you describe the desired result; Terraform determines the resource operations needed to move toward it.

A **provider** is a plugin that implements interaction with a platform's APIs. The AWS provider understands AWS resource types and uses AWS credentials to request permitted operations. Naming a provider does not grant permissions.

Reference: [HashiCorp: Providers](https://developer.hashicorp.com/terraform/language/providers).

### Read a small configuration

This illustrative `main.tf` fragment needs an available bucket name before deployment. A complete project would also select provider versions and configure authentication and state storage.

```hcl
# Provider configuration: where AWS operations will be directed.
provider "aws" {
  region = "us-east-2"
}

# Resource declaration: a bucket Terraform would manage.
resource "aws_s3_bucket" "raw_data" {
  bucket = "replace-with-an-available-training-bucket-name"
}
```

| Element | Meaning |
| --- | --- |
| `provider`, `resource` | Terraform block types |
| `aws` | Local name conventionally used for the AWS provider |
| `aws_s3_bucket` | Resource type implemented by that provider |
| `raw_data` | Author-chosen local resource name |
| `bucket` | Argument specifying the actual S3 bucket name |
| `aws_s3_bucket.raw_data` | Terraform resource address; it is not the bucket's AWS name |

HCL comments use `#`, `//`, or `/* ... */`. HTML comments such as `<!-- main.tf -->` do not belong inside Terraform configuration.

### Resource versus data source

- A `resource` block declares something Terraform should manage, such as an EC2 instance.
- A `data` block reads information, such as finding an existing Amazon Machine Image (AMI) using filters.
- An **AMI** is a template used to launch EC2 instances. Looking one up does not launch an instance.

The class demo used `data "aws_ami" "amazon_linux"` and an `aws_instance` resource. The connection would be an expression such as `ami = data.aws_ami.amazon_linux.id`. This reference also establishes an infrastructure dependency. Terraform resource dependencies do not define the order of daily ETL tasks.

Reference: [HashiCorp: Data sources](https://developer.hashicorp.com/terraform/language/data-sources).

### Terraform workflow

Run commands in the directory containing the project's `.tf` files. `main.tf` is a common filename; Terraform reads configuration files in that directory together.

| Command | Purpose | Important limit |
| --- | --- | --- |
| `terraform init` | Initialize the working directory, providers, and configured backend | Prepares the project for later commands |
| `terraform fmt -check` | Check standard formatting | Formatting does not establish correctness |
| `terraform validate` | Check syntax and internal consistency after initialization | Does not prove AWS permissions or successful deployment |
| `terraform plan` | Preview proposed additions, changes, and removals | Does not apply those proposed resource changes |
| `terraform apply` | Carry out a plan | Ordinary interactive apply without a saved plan generates a plan and requests confirmation |
| `terraform destroy` | Remove managed resources in the selected configuration/state | Review the environment, affected resources, and data before confirming |

The learning sequence is `init` → formatting/validation → `plan` → reviewed `apply`. There is no `terraform commit` command in this workflow. `git commit` records files; `terraform apply` changes infrastructure.

Illustrative plan output: `Plan: 1 to add, 0 to change, 0 to destroy.` One addition is proposed; it has not happened yet. Review individual changes because a plan may also propose replacement or deletion.

Reference: [HashiCorp: Terraform CLI commands](https://developer.hashicorp.com/terraform/cli/commands).

### Installation and EC2 demo context

- The class installation commands used `apt` for Debian/Ubuntu. Do not paste those into macOS Terminal; follow instructions for the operating system where Terraform will run.
- Keep AWS access keys and passwords out of examples and committed configuration.
- Amazon Linux 2023 on the demo EC2 instance uses `dnf`; the remote instance and your laptop are separate environments.
- The usual Amazon Linux SSH username is `ec2-user`, with a hyphen. A public IP alone is insufficient: authentication and network access must also be configured. EC2 Instance Connect has its own prerequisites.

Optional references: [Install Terraform](https://developer.hashicorp.com/terraform/tutorials/aws-get-started/install-cli), [Amazon Linux package management](https://docs.aws.amazon.com/linux/al2023/ug/package-management.html), and [EC2 connection prerequisites](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/connection-prereqs.html). Installation and SSH are outside this theoretical homework.

**Checkpoint:** Explain what plan does, what apply can change, and why validation cannot establish that AWS will accept a deployment.

## Terraform state

State connects configuration addresses to real managed objects. For example, it records which existing bucket corresponds to `aws_s3_bucket.raw_data`.

| Piece | Role |
| --- | --- |
| Configuration | Desired resource definitions |
| State | Mapping and tracked attributes for managed objects |
| Actual AWS resources | Objects that currently exist, which may have changed outside Terraform |

During planning, Terraform normally refreshes information about tracked resources and compares it with the desired configuration. A manual change outside Terraform is **drift**. Review drift rather than assuming the files and live environment match.

- Local state is commonly stored in `terraform.tfstate`.
- Teams commonly use a remote backend to share the appropriate state instead of competing laptop copies.
- State locking, where supported and enabled, helps prevent concurrent writers interfering.
- Losing state can break the mapping to existing resources. Deleting the state file does not delete the resources themselves.

References: [Terraform state](https://developer.hashicorp.com/terraform/language/state) and [State locking](https://developer.hashicorp.com/terraform/language/state/locking).

State and saved plans can contain sensitive values. Protect access, encryption, and backups, and do not commit them to Git. Marking a value `sensitive` controls its display but does not by itself keep it out of state. See [HashiCorp: Sensitive data](https://developer.hashicorp.com/terraform/language/manage-sensitive-data).

Terraform state tracks infrastructure. It does not tell you whether yesterday's pipeline completed or whether warehouse rows are correct.

**Checkpoint:** If a bucket exists but its Terraform state is lost, why might the configuration alone be insufficient to manage it safely?

## Workflow orchestration and dependencies

An orchestrator coordinates tasks toward a workflow outcome. It tracks eligibility, completion, and the next action after success or failure.

For the Citi Bike example, assume one run owns a specific snapshot and corresponding output paths:

```text
Collect snapshot → store Bronze JSON → transform to Silver Parquet
                                         ↓ after success
                                  load into Redshift
                                         ↓ after success
                                  update analytical output
```

Carry the snapshot identifier or exact input paths through the run. “Load the latest file” is ambiguous: a retry might consume a different snapshot.

### Why dependencies matter

- A transformation needs its expected raw input.
- A load needs complete, validated transformation output.
- Analytical updates need the intended load to finish successfully.
- Independent tasks can run in parallel; dependent tasks must respect prerequisites.

**Starting a job is not completing it.** A successful API response can mean only that a service accepted a request and returned a job-run ID. The job might fail later. A dependent task must wait for the completion condition it actually needs.

If a transformation fails, block its dependent load from consuming incomplete or stale output. Retry appropriate transient errors or stop that path and report failure. A notification task may still run on an explicit failure path.

### Scheduling versus orchestration

| Question | Responsibility |
| --- | --- |
| Should a run start every morning? | Scheduling |
| Has transformation finished successfully? | Orchestration/completion tracking |
| May loading begin now? | Orchestration/dependency management |
| What happens after failure? | Orchestration/failure policy |
| Do the bucket and job definitions exist? | Provisioning |

An 8 AM trigger does not establish that source data is ready. Add readiness checks when arrival time varies.

**Checkpoint:** Why does scheduling transformation at 8 AM and loading at 8:10 AM fail to guarantee correct ordering?

## AWS Step Functions

Step Functions is an AWS managed workflow orchestration service. A **state machine** defines states, transitions, and outcomes. An **execution** is one run of that definition with particular input.

Workflow Studio provides visual authoring. **Amazon States Language (ASL)** provides a structured definition. Terraform can provision a state machine containing that definition; the invoked services still perform the processing.

Reference: [AWS: Step Functions overview](https://docs.aws.amazon.com/step-functions/latest/dg/welcome.html).

### Common states

| State | Purpose | Example |
| --- | --- | --- |
| `Task` | Invoke an action or integrated service | Invoke Lambda or start Glue |
| `Choice` | Select a path based on a condition | Branch on an input-readiness result |
| `Wait` | Pause before continuing | Delay before a status check |
| `Parallel` | Run multiple branches | Perform independent checks |
| `Map` | Process a collection | Process a list of objects |
| `Pass` | Pass or shape workflow data | Prepare values for another state |
| `Succeed` / `Fail` | End with an explicit outcome | Mark completion or unrecoverable failure |

The class demonstrated Distributed Map, a Map capability using child workflow executions for larger collections. It is not required for this homework. Step Functions can coordinate services beyond Lambda.

Reference: [AWS: Workflow states](https://docs.aws.amazon.com/step-functions/latest/dg/workflow-states.html).

### Wait for Glue completion

This Task-state fragment uses ASL's JSONPath form. It is incomplete: the next state, existing Glue job, and execution permissions are not supplied.

```json
{
  "TransformSnapshot": {
    "Type": "Task",
    "Resource": "arn:aws:states:::glue:startJobRun.sync",
    "Parameters": {
      "JobName": "example-bronze-to-silver"
    },
    "Next": "ValidateSilverOutput"
  }
}
```

- `TransformSnapshot` is an author-chosen state name.
- `Type`, `Resource`, `Parameters`, and `Next` are ASL fields.
- `JobName` identifies an existing Glue job definition.
- `.sync` starts the job and waits for completion before a successful transition.
- A job failure needs error handling; it is not a successful transition to validation.

Use a **Standard** workflow for this `.sync` example. Express workflows do not support the job-run `.sync` pattern. Express synchronous invocation and a Task's `.sync` service integration are different concepts.

References: [AWS: Glue integration](https://docs.aws.amazon.com/step-functions/latest/dg/connect-glue.html) and [Choosing workflow type](https://docs.aws.amazon.com/step-functions/latest/dg/choosing-workflow-type.html).

### Choice, Retry, and Catch

- **Choice:** branch based on workflow data, such as a readiness flag.
- **Retry:** attempt a failed state again when its error matches the retry policy.
- **Catch:** transition to a recovery or reporting path after a matching error is not recovered by retries.
- **Fail:** end with a failure outcome when recovery is inappropriate or exhausted.

A failed Glue Task does not automatically produce a normal `succeeded = false` value for Choice to inspect. Handle task errors through the relevant error-handling configuration.

```text
Transform → temporary service error → bounded retry → succeeds → validate
Transform → persistent invalid input → stop dependent work → report → fail
```

Retrying a task gives it another chance; failing the workflow records that this execution did not complete its required work. Neither automatically undoes earlier writes. Repeated attempts will not repair the same invalid schema.

Reference: [AWS: Error handling](https://docs.aws.amazon.com/step-functions/latest/dg/concepts-error-handling.html).

**Checkpoint:** Explain why Choice and Retry are not interchangeable, and why a Glue job-run ID is insufficient evidence to start a load.

## Apache Airflow

Airflow is an open-source platform for developing, scheduling, and monitoring workflows. Workflows are defined in Python as **DAGs: Directed Acyclic Graphs**.

- **Graph:** tasks are nodes; dependencies are edges.
- **Directed:** dependencies have a direction, such as extract → transform.
- **Acyclic:** dependencies cannot form a circular path.

If extract waits for load, load waits for transform, and transform waits for extract, no task can satisfy its prerequisites. Daily recurrence creates another DAG run, not a cycle. A retry repeats an attempt without creating a circular dependency.

Reference: [Apache Airflow: DAGs](https://airflow.apache.org/docs/apache-airflow/stable/core-concepts/dags.html).

### Tasks and runs

| Term | Meaning |
| --- | --- |
| DAG definition | Reusable workflow structure |
| DAG run | One execution of that workflow |
| Task | One unit of work |
| Task instance | A particular task in a particular DAG run |
| Upstream / downstream | A prerequisite task / a task depending on it |
| Operator | Implementation for a kind of task |
| Sensor | A task waiting for a condition, such as an expected file |

The scheduler identifies runnable work; execution components arrange for tasks to run. Work may happen in an Airflow worker or be submitted to an external service. Task states and logs expose progress and failures.

Reference: [Apache Airflow: Tasks](https://airflow.apache.org/docs/apache-airflow/stable/core-concepts/tasks.html).

### Read an Airflow 3 DAG

This print-only example uses Airflow 3-style imports. It demonstrates dependencies, not real extraction or loading. Python syntax checks do not establish compatibility with an installed Airflow environment.

```python
from datetime import datetime, timedelta, timezone

from airflow.sdk import dag, task


@dag(
    dag_id="snapshot_pipeline_demo",
    start_date=datetime(2026, 10, 1, tzinfo=timezone.utc),
    schedule="@daily",
    catchup=False,
)
def snapshot_pipeline_demo():
    @task(retries=2, retry_delay=timedelta(minutes=1))
    def extract():
        print("Extracting a snapshot: demonstration only")

    @task
    def transform():
        print("Transforming a snapshot: demonstration only")

    @task
    def load():
        print("Loading a snapshot: demonstration only")

    # Build task nodes and declare dependency direction.
    extract_task = extract()
    transform_task = transform()
    load_task = load()
    extract_task >> transform_task >> load_task


snapshot_pipeline_demo()
```

- `dag` and `task` are imported decorators. Function and variable names are author-chosen.
- `@dag` defines the workflow; `@task` makes a function an Airflow task definition.
- Calls inside the DAG function build task nodes. They do not immediately execute the print statements during parsing.
- `>>` declares dependencies. Under the default success-based trigger rule here, transform requires extract to succeed, and load requires transform to succeed.
- `retries=2` allows two retries after the initial extract attempt; `retry_delay` sets their delay.
- The final call creates the DAG for discovery. Running the file as an ordinary Python script does not run the ETL workflow end to end.

Reference: [Apache Airflow: TaskFlow tutorial](https://airflow.apache.org/docs/apache-airflow/stable/tutorial/taskflow.html).

### Scheduling and historical runs

- `schedule="@daily"` declares a daily schedule.
- `start_date` anchors the scheduling timeline; it does not request immediate task execution at that timestamp.
- For this interval-based daily schedule, scheduled runs are normally created after the data interval ends.
- `catchup=False` prevents automatic creation of every missed historical interval. Historical processing can still be requested separately.
- A **backfill** deliberately processes historical intervals. Tasks must select those intervals' inputs rather than blindly read today's data.

Reference: [Apache Airflow: DAG runs](https://airflow.apache.org/docs/apache-airflow/stable/core-concepts/dag-run.html).

### Airflow versus Step Functions

Airflow suits teams wanting Python-defined workflows, scheduling/backfills, and integrations across cloud and non-cloud systems. It needs an operational environment, self-managed or provided by a service. AWS offers **Amazon Managed Workflows for Apache Airflow (MWAA)**; the abbreviation is MWAA, not MAA.

Step Functions supplies managed state-machine execution and AWS service integrations without operating an Airflow environment. Both can coordinate AWS tasks. Choose based on workflow needs, integration support, team experience, and operational responsibilities.

References: [AWS: What is MWAA?](https://docs.aws.amazon.com/mwaa/latest/userguide/what-is-mwaa.html) and [Step Functions overview](https://docs.aws.amazon.com/step-functions/latest/dg/welcome.html).

**Checkpoint:** Trace extract failing once and then succeeding. When may transform run? What happens if extract exhausts its retries?

## Cron and EventBridge Scheduler

### Traditional Linux Cron

Cron schedules commands on Unix/Linux hosts. A user crontab entry commonly has five time fields followed by a command:

```text
minute  hour  day-of-month  month  day-of-week  command
0       8     *             *      1-5          /absolute/path/to/script
```

This requests the command at 8 AM Monday through Friday in Cron's configured timezone.

| Field | Common values |
| --- | --- |
| Minute | `0-59` |
| Hour | `0-23` |
| Day of month | `1-31` |
| Month | `1-12` |
| Day of week | `0-7`; `0` and `7` mean Sunday in the referenced Linux implementation |

- `*` means every valid value in that field.
- `1-5` is a range; in the weekday field, Monday through Friday.
- `*/15` in the minute field means minute 0, 15, 30, and 45 each hour, not 15 minutes after the previous command finishes.

```text
# Expressions only; a real crontab entry also needs a command.
0 0 * * *       every day at midnight
*/15 * * * *    every 15 minutes
0 2 * * 0       every Sunday at 2 AM
```

Cron does not supply a complete task graph, dependency tracking, and pipeline retry policy. A launched script can implement these, but then the script owns them. Separate time-based entries do not guarantee success-based ordering.

Reference: [Linux crontab manual](https://man7.org/linux/man-pages/man5/crontab.5.html).

### Host-based scheduling limits

- The host and Cron service must be running; a sleeping laptop is unsuitable for dependable production scheduling.
- Commands need appropriate paths, environment settings, credentials, and logs. Interactive terminal settings may be absent.
- Runs may overlap if a command exceeds the schedule interval and coordination is absent.
- Choose the timezone and consider daylight-saving transitions.

A cloud scheduler moves scheduling off someone's laptop. Permissions, delivery monitoring, and downstream completion checks still need configuration.

### EventBridge Scheduler

EventBridge Scheduler requests AWS target operations on recurring or one-time schedules. It can request a Step Functions execution or invoke Lambda, using an execution role with relevant permissions.

Its cron expressions include a year field and AWS-specific rules. `?` leaves a day field unspecified. Do not copy Linux Cron directly into Scheduler.

| Intent | Linux expression | EventBridge Scheduler expression |
| --- | --- | --- |
| 8 AM Monday–Friday | `0 8 * * 1-5` | `cron(0 8 ? * MON-FRI *)` |
| Midnight daily | `0 0 * * *` | `cron(0 0 * * ? *)` |
| Every 15 minutes | `*/15 * * * *` | `rate(15 minutes)` for interval-based scheduling |

The rate expression requests recurring intervals, not alignment to specific wall-clock minutes. Configure Scheduler's timezone for cron-based schedules; do not assume the classroom example uses your local timezone.

References: [AWS: Scheduler schedule types](https://docs.aws.amazon.com/scheduler/latest/UserGuide/schedule-types.html) and [Scheduler setup and execution roles](https://docs.aws.amazon.com/scheduler/latest/UserGuide/setting-up.html).

**Checkpoint:** What does Cron provide, and what must a script add to coordinate a multi-step pipeline?

## Comparing the technologies

| Technology | Responsibility here | Definition style | What it does not establish by itself |
| --- | --- | --- | --- |
| Terraform | Provision and manage infrastructure | HCL | Successful daily processing or correct data |
| Step Functions | Orchestrate workflow executions | ASL and visual tooling | A recurring calendar schedule or correct transformations |
| Airflow | Schedule and orchestrate workflows | Python DAGs | Automatically provisioned AWS infrastructure or correct task code |
| Cron | Schedule host commands | Crontab expressions and commands | Managed dependency tracking and recovery |
| EventBridge Scheduler | Trigger AWS operations on a schedule | Expression, target, permissions | Downstream workflow completion |

These tools can work together. Terraform can provision a workflow and schedule. Scheduler can request executions. The workflow coordinates processing services. Airflow combines scheduling and orchestration, so a migration should revisit both responsibilities and avoid accidental duplicate triggers.

Kubernetes appeared in class as another kind of orchestration. It coordinates container workloads and desired runtime state; this differs from explicitly managing ETL dependencies and data intervals.

## Operations and recovery

### Requirements and data ownership

Before choosing a design, identify expected input, processing interval, completion deadline, and success criteria. Assume a modest batch for one identified Citi Bike snapshot here; no throughput or latency has been measured.

- Bronze preserves the captured input for the run.
- Silver and warehouse output are derived data traceable to that input.
- The workflow owns coordination and run status; each job owns its processing and publication behavior.
- Required invariant: dependent loads consume complete output for the intended run.
- Required invariant: repeating a run does not silently duplicate intended business records.

### Failures and safe retries

| Failure | Detection | Response to design |
| --- | --- | --- |
| Source object absent | Readiness check | Wait within a limit or report missing input |
| Temporary service outage | Task error/status | Bounded retry with delay |
| Invalid schema | Validation and job logs | Stop dependent work; fix or quarantine before rerun |
| Partial transformation output | Output checks and publication records | Keep partial output away from readers; publish validated output |
| Load commits but reply is lost | Target data and load/run records | Reconcile before repeating writes |

**Idempotency** means repeating an operation for the same logical input has the same intended final effect. Plain append may duplicate rows on retry. A designed merge, deduplication key, or controlled replacement of an owned partition can make reruns safe within its scope. The orchestrator does not automatically provide this data behavior.

### Verify a particular day's outcome

Check multiple layers:

- **Trigger:** was the expected run requested?
- **Workflow:** did that execution or DAG run reach its required successful outcome?
- **Tasks:** did required Glue runs and warehouse operations complete? Inspect failures, retries, durations, and logs.
- **Data:** does output cover the intended interval and pass schema, completeness, and duplicate checks?
- **Freshness:** was validated output available by the deadline?

Record run ID, snapshot or processing date, S3 paths, Glue job-run IDs, output identity, and validation results. For Step Functions Standard, inspect execution history and service logs. For Airflow, inspect DAG runs, task-instance states, and logs. Configure failure and missing-run reporting: a workflow that never started cannot report its own failure.

### Production considerations

- Separate deployment permissions from runtime permissions. Creating a job does not establish that it can read input or that a workflow can invoke it.
- Protect state, secrets, and logs. Pass data identifiers and locations rather than credentials in workflow input.
- Define timeout, retry, overlap, and backfill policies. Decide what happens if yesterday's run remains active at today's trigger.
- Include processing services, orchestration/scheduling, storage, logs, and any Airflow environment in cost analysis. No billing was measured here.
- Assign cleanup ownership; deleting a workflow differs from deciding whether retained data may be deleted.

## Common pitfalls

| Misunderstanding | Correction |
| --- | --- |
| Plan creates resources | Plan previews; apply performs resource changes |
| Terraform commit deploys | Git commits files; Terraform apply changes infrastructure |
| State is pipeline execution history | State tracks managed infrastructure objects |
| Successful Glue request means output is ready | Request acceptance differs from job completion |
| Choice automatically catches task errors | Choice evaluates data; errors need error handling |
| A DAG cannot run daily | Recurrence creates separate runs of an acyclic graph |
| A dependency passes the full dataset | Dependencies establish ordering; data needs explicit handoff |
| A successful trigger proves pipeline success | Verify downstream tasks and published data |
| Retrying is always safe | Repeated writes require idempotency and outcome reconciliation |

## Design practice

Rehearse using the Citi Bike example, then apply the reasoning independently to the homework's daily sales scenario. No deployment is required.

Write assumptions about arrival time, input completeness, processing date, and acceptable delay before drawing a diagram. A daily clock does not establish that all of yesterday's data has arrived.

- List resources needed before a run; distinguish new resources from shared ones.
- Identify the morning trigger and timezone.
- Name tasks, draw dependency arrows, and state each required completion condition.
- Add a transformation failure path; distinguish retryable errors from those requiring investigation.
- Identify run records and data checks needed to assess a particular day's outcome.
- For an Airflow alternative, identify where dependencies, scheduling, retries, and monitoring would move, and which processing/storage services could remain.

Make the resource choices and final diagram in your own submission. Consult the [homework](2.1_Tue_HW.md) for exact questions and answer length.

## Knowledge check and completion checklist

You are ready when you can explain these without copying the lecture:

- [ ] Give a concrete reason for IaC and explain why architecture knowledge remains necessary.
- [ ] Explain providers, resource declarations, declarative configuration, and state.
- [ ] Distinguish plan/apply and explain the consequences of destroy.
- [ ] Separate provisioning, scheduling, and orchestration using one pipeline.
- [ ] Explain state machines, Choice, completion waiting, task retry, and workflow failure.
- [ ] Expand DAG, explain why cycles are invalid, and trace `extract >> transform >> load`.
- [ ] Interpret `*/15 * * * *` and explain host availability requirements.
- [ ] Distinguish Linux Cron and EventBridge Scheduler syntax.
- [ ] Give a reason to choose Airflow and identify responsibilities affected by a migration.
- [ ] Explain why both execution evidence and data checks matter.

## Verification status

These are lecture examples and design explanations. Local documentation and syntax checks are recorded in the [coverage inventory](../../AI-Generated-Training/COVERAGE.md). Terraform provider initialization, validation through Terraform itself, Airflow import/scheduling, and AWS execution have not been performed. Syntax checks do not establish permissions, service integration, runtime recovery, or data correctness.
