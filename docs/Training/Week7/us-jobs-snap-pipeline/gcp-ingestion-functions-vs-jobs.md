# GCP ingestion: source-deployed functions versus container jobs

> Purpose: presentation reference and architecture decision aid.
> Historical decision record: the discussion below preserves the October 25–26 evaluation. The project subsequently adopted Cloud Run Jobs, and the learner reported completed ingestion and workflow executions. For the current presentation rationale and alternatives, use [presentation-script.md](presentation-script.md#32-ingestion-with-cloud-run-jobs--draft-for-review). The runtime-check evidence below describes that early experiment only.
> Decision status: open; the learner has not selected the final ingestion deployment approach.
> Evidence: a container image was built/pushed and a Cloud Run runtime-check Job succeeded. Live BLS/SNAP cloud ingestion and monthly orchestration remain pending.
> Reviewed: October 25, 2026 local / October 26, 2026 UTC.

## Presentation summary — about 30 seconds

“I evaluated two ways to deploy the ingestion code: a source-deployed Python function and a container-based batch job. A function offers a workflow similar to our AWS Lambda lab, while a job lets us package a Python program and execute it to completion. Both can participate in an automated monthly pipeline. The tradeoff is deployment simplicity versus explicit runtime control and batch execution behavior. Docker is a packaging choice, not a requirement for all Python ingestion in GCP. We verified the container runtime, but the final ingestion choice is still open.”

## What problem are we solving?

Run bounded Python ingestion without depending on a laptop: fetch BLS responses and USDA SNAP downloads, preserve original bytes and manifests in Bronze, and tell the orchestrator whether capture succeeded. Processing must respect each source's latest six reporting months, retain source exceptions, and support safe reruns. These correctness requirements apply to either deployment approach.

The ingestion runtime is separate from managed Spark transformations, BigQuery modeling, and history publication. Neither a function nor a basic ingestion Job is a Spark cluster.

## Separate storage, packaging, execution, and orchestration

| Responsibility | Meaning in this project |
|---|---|
| Source/data storage | Cloud Storage holds original captures, manifests, and processing artifacts. |
| Deployment packaging | Source and dependencies are prepared for execution; an explicit container image also specifies its runtime environment. |
| Execution | A function handler or batch Job runs the ingestion logic. |
| Orchestration | Workflows coordinates dependent stages, waits for results, and handles workflow-level failures. |
| Scheduling | Cloud Scheduler starts the workflow monthly. |

Uploading a Python file to object storage does not by itself make it execute. In the learner's AWS lab, S3 held scripts/artifacts and Lambda supplied execution. GCP similarly separates storage from compute. AWS Lambda itself supports both ZIP and container-image deployment packages; packaging and the choice of execution service are distinct decisions. [AWS deployment packages](https://docs.aws.amazon.com/lambda/latest/dg/configuration-function-zip.html)

## Compare the two GCP choices

| Consideration | Source-deployed Cloud Run function | Container-based Cloud Run Job |
|---|---|---|
| Application entry point | Python handler invoked by HTTP or an event | Program starts, completes its task, and exits |
| Developer supplies | Function source, dependencies, and runtime configuration | Image built from code, dependencies, and a runtime definition |
| Packaging work | Platform manages image construction from source | Developer explicitly controls image construction and versioning |
| Useful fit here | Small, bounded ingestion handlers; familiar Lambda-style authoring | Script-oriented batch capture with explicit task completion |
| Main tradeoff | Less explicit container maintenance; conform to the function execution contract | More build/repository setup; direct control of the packaged environment |
| Workflow integration | Workflows invokes the function using its supported interface | Workflows starts the Job and waits for its execution result |
| Data correctness | Application must enforce keys, windows, retries, and acceptance rules | Application must enforce the same rules |

These are capability descriptions, not benchmark results. Google documents [source-deployed functions](https://docs.cloud.google.com/run/docs/deploy-functions), [Jobs that run to completion](https://docs.cloud.google.com/run/docs/create-jobs), and [Workflows service orchestration](https://docs.cloud.google.com/workflows/docs/overview).

### Source deployment still involves an image

Cloud Run function deployment uses buildpacks and Cloud Build to create an image, then Artifact Registry to store it. The platform automates that packaging; the learner does not have to maintain a Dockerfile or manually push the image. Source deployment still requires appropriate APIs, build permissions, and runtime identity configuration. [Function build process](https://docs.cloud.google.com/run/docs/deploy-functions)

For our explicit Job image, the Dockerfile selected Python 3.12 and dependencies, Cloud Build built/pushed the image, and Cloud Run executed it. This exposes more of the deployment machinery, which can be educational but adds setup effort.

## Build time and monthly execution are different

| When | What happens |
|---|---|
| Code or dependencies change | Build and deploy a new application version. |
| Monthly schedule fires | Execute an already-deployed version with the relevant run parameters. |

The intended monthly workflow does not require opening Cloud Shell, rebuilding the image, or uploading local files each month. Both approaches can run automatically with cloud identities and cloud storage paths.

## Why Jobs were proposed, and why functions remain reasonable

The ingestion already exists as a Python program that fetches batches, preserves attempt artifacts, writes a summary, and exits. That makes Jobs a natural candidate. Explicit packaging also lets us select the interpreter and dependencies and identify the deployed image by digest.

Our ingestion workload is small enough that a source-deployed function is also a reasonable candidate. It would more closely match the learner's Lambda experience and reduce explicit Docker authoring. It would need a handler around the shared ingestion logic and appropriate timeout, retry, and authentication settings.

Neither choice is inherently faster, cheaper, or more reliable for this workload. We have not measured a function-versus-Job comparison. Build/image storage, execution, logging, and related services belong in the cost comparison; a managed source build does not make deployment artifacts disappear.

Existing setup is useful evidence, but it does not require choosing Jobs. The final choice should follow the desired learning experience and workload needs, not merely the effort already spent.

## What our experiment actually proved

| Observed evidence | What it establishes |
|---|---|
| Cloud Shell built the runtime-check image | The supplied package can build in that environment. |
| Direct Docker push repeatedly received TCP connection refusal | That push path failed; the precise underlying network cause was not established. |
| Cloud Build initially lacked source-object read access | Build identity permissions needed correction. |
| Managed build/push subsequently succeeded | A runnable image was published to Artifact Registry. |
| Cloud Run logged an object write, exited with code 0, and completed | The runtime-check Job received a nonempty secret and could create an object in Bronze. |

This experiment does not establish real BLS API authentication from Cloud Run, completed cloud ingestion, production reliability, or a cost advantage over functions. Those remain separate acceptance checkpoints.

## Ownership, failures, and production considerations

The build identity packages code; the runtime identity reads its authorized secret and writes captures; the orchestrator starts and coordinates work. These are separate permissions even when the application code is small.

In either approach, preserve failed attempts, limit retries, keep credentials out of artifacts/logs, and publish completion only after required captures exist. Workflow retries and task/event retries must not multiply source calls unexpectedly. A successful execution alone does not prove complete source coverage or correct warehouse publication.

The final monthly pipeline also needs fresh cutoff discovery, six-month filtering, a single-writer guard, idempotent fact/history publication, and operational logs. Choosing a function or Job does not supply these data guarantees automatically.

## Questions to answer before deciding

- Do I prefer handler-based authoring or a program that runs and exits?
- Do my dependencies need explicit operating-system/runtime packaging?
- Is matching the AWS Lambda learning pattern more valuable than practicing container deployment?
- Can the chosen runtime meet the measured ingestion duration, memory, and retry needs?
- Can I explain deployment, execution, and data correctness as separate concerns?

## Presentation wording and next decision

Use: “We tested a container-based Job and are comparing it with source-deployed functions. Both can support the planned monthly orchestration.”

Avoid: “GCP requires Docker,” “Docker makes ingestion faster,” or “the monthly cloud pipeline is complete.”

The next decision is the ingestion execution interface. The accepted Bronze layout, shared Python logic, six-month policy, revision-history requirements, and monthly Workflows/Scheduler target remain applicable to either option. See the [GCP learning plan](gcp-learning-plan.md) and [execution record](steps.md) for implementation status.
