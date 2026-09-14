# Interactive Data Engineering Lab Template

> Status: Draft contract; implementation and automated execution validated with one Easy lab, learner-usability review pending
> First template-validation lab: `DV-E23` High-Engagement Video Filtering

## Purpose

An interactive lab teaches one or more durable data-engineering techniques through job-shaped artifacts and executable evidence. The notebook is the guide, runner, and feedback surface; learner work belongs in pre-created Python, SQL, shell, configuration, data-contract, infrastructure, or other files appropriate to the task. A lab must run independently from a clean notebook kernel and clean generated-output location.

## Classification

Difficulty and delivery scope are independent. Do not label a lab Hard merely because it contains many steps, and do not label a one-line transformation Easy when its correctness contract is subtle.

### Technique difficulty

| Level | Learner responsibility | Guidance contract |
| --- | --- | --- |
| Easy | Apply a named technique against a precise contract | Provide ordered checkpoints, target files and function signatures, focused hints, visible tests, and explicit completion criteria. |
| Medium | Select and combine techniques while resolving ordinary edge cases | Provide business and data contracts, artifact boundaries, and acceptance tests; omit most algorithmic steps. |
| Hard | Design a robust solution under ambiguity, scale, failure, and operational constraints | Provide requirements, evidence expectations, non-goals, and failure scenarios; do not prescribe the architecture or implementation sequence. |

### Delivery scope

| Scope | Typical work | Indicative effort |
| --- | --- | --- |
| Technique drill | One focused SQL, DataFrame, schema, shell, or scheduling technique | 15–45 minutes |
| Component exercise | One reusable transform, ingestion script, data-quality gate, CLI, or cron definition | 45–90 minutes |
| Pipeline slice | Multiple artifacts crossing one meaningful boundary such as source → bronze or silver → gold | 1.5–3 hours |
| System flow | Several cooperating components such as producer → broker → consumer → sink with recovery and observability | Multi-session |

Effort is a planning estimate, not a correctness claim. Record actual learner time after running the lab and adjust future estimates from evidence.

## Lab identity

Every lab declares:

```markdown
Lab ID: DV-E23
Title: High-Engagement Video Filtering
Scenario: Content platform
Difficulty: Easy
Delivery scope: Technique drill
Expected effort: 30–45 minutes
Primary interface: PySpark DataFrame API
Optional comparison: Spark SQL
Tooling: python, pyspark, spark
Techniques: explicit-schema, filter, projection, deterministic-order
Prerequisites: DataFrame filtering, projection, ordering, explicit schemas
Source context: User-provided Data Vidhya question
```

Stable IDs do not change when titles, paths, difficulty, or source wording changes.

Tooling tags identify technologies the learner is practicing, not universal delivery software. Do not tag every lab with `jupyter` or `vscode` merely because notebooks are opened in VS Code. Include `linux`, `cron`, `kafka`, `spark`, `python`, `sql`, or another tool only when using that tool is part of the learning objective.

## Artifact map

Include only artifacts the lab actually needs, but always include a notebook, one or more pre-created learner work files, learner-facing verification, and a separate solution explanation. A technique drill may have one small Python or SQL file; broader labs may have several source, query, script, configuration, or infrastructure files. Files may begin mostly empty, but their path, intended responsibility, and loading or execution mechanism must already exist and be linked from the notebook.

```text
notebooks/interactive-data-engineering-labs/<scenario>/<lab-id>-<slug>.ipynb
src/big_data_example/labs/<scenario_module>/<lab_id>_<slug>.py
sql/interactive-data-engineering-labs/<scenario>/<lab-id>-<slug>.sql
scripts/interactive-data-engineering-labs/<scenario>/<lab-id>-<slug>.sh
data/samples/interactive-data-engineering-labs/<scenario>/source/<batch>/...
tests/labs/<scenario_module>/test_<lab_id>_<slug>.py
tests/fixtures/interactive-data-engineering-labs/<scenario>/<lab-id>/expected/...
docs/interactive-data-engineering-labs/solutions/<scenario>/<lab-id>-<slug>.md
```

Repository directories use kebab case. Importable Python modules use snake case because Python identifiers cannot contain hyphens.

## Notebook contract

### 1. Lab header

State the identity fields, what the learner will build, and why the technique matters in a real pipeline. Distinguish the source-inspired concept from the derivative exercise. Keep difficulty, delivery scope, expected effort, deliverable, prerequisites, tooling tags, and technique tags visible at the top so the learner can judge the commitment before starting.

Immediately below the metadata, include a compact **Start here** block that links every learner work file needed for the first action, points to the lab README or run instructions, and links the separate solution as a spoiler. Do not link learner-facing prompts directly to author-side unit-test source or hidden expected fixtures.

### 2. Business request

Describe the consumer, decision, requested output, freshness or schedule, and important non-goals. Keep Easy requests narrow enough that infrastructure does not obscure the primary technique.

### 3. Data contract

For every input and output, state:

- Grain: what one row represents.
- Business and technical keys.
- Ordered field names and types.
- Nullability and invalid-record behavior.
- Time zone and interval-boundary rules when relevant.
- Decimal precision and rounding rules when relevant.
- Duplicate and tie-breaking rules.
- Sensitive fields and allowed exposure.

### 4. Supplied artifacts

Link only the source fixtures, starter files, shared helpers, and solution that the learner is expected to navigate. State which files or cells the learner may edit and which inputs must remain immutable. Keep author-side tests and hidden expected fixtures out of the learner navigation even though a determined repository reader can still find them.

### 5. Environment check

Use the shared notebook helper to acquire the local Spark session and resolve repository paths. Do not duplicate environment installation logic or depend on another notebook having run.

### 6. Guided checkpoints

Each checkpoint contains:

```markdown
#### Checkpoint N: Concise objective

Target artifact: `relative/path/to/file.py`

Task: State the observable behavior to implement.

Acceptance evidence: State the command or notebook validation cell that must pass.

Hint: Include for Easy, include selectively for Medium, and normally omit for Hard.

Job connection: Explain briefly how the checkpoint's technique appears in production work and where the simplified exercise stops matching production.
```

The notebook may contain scratch cells for inspection or experiments, but accepted work lives in the linked pre-created files. The checkpoint's execution cell must explicitly reload, run, or otherwise consume the learner's latest saved artifact so the relationship is visible rather than relying on unexplained notebook magic.

Keep the problem, schema or data contract, and target artifact visible without expansion. For each checkpoint, keep its heading visible and place all checkpoint prose inside one HTML `<details>` block. Keep the executable code in the immediately following code cell, which remains independently collapsible because standard notebook HTML cannot enclose or control another cell. A learner should be able to collapse the instructions and code separately, then scan the checkpoint titles without repeatedly scrolling through prose.

### 7. Validation cells

Validation must invoke the learner's notebook result or external artifact. Present it as **Check my work** and report focused contract failures without linking to the checker implementation, author unit tests, or hidden expected fixture. Checks should compare schema and rows, avoid accidental reliance on unordered DataFrame output, and include meaningful boundary cases. A displayed `show()` result is diagnostic output, not proof.

### 8. Operational extension

Include only when appropriate to the delivery scope. Examples are rerun behavior, an ingestion shell script, a cron expression, a command-line entry point, a producer/broker/consumer flow, checkpoint recovery, or publication semantics.

### 9. Reflection

Ask focused questions about correctness, alternatives, performance, and production behavior. Easy labs should normally ask two to four questions rather than turning a technique drill into a system-design essay.

### 10. Definition of done

- The notebook runs from a clean kernel.
- Required implementation files are complete.
- Automated checks pass.
- Output schema, order where contractual, and boundary cases match.
- Generated artifacts stay in their declared ignored locations.
- The learner can explain the technique without relying on the solution document.

### 11. Restart and reset

Every lab explains the difference between restarting the notebook kernel, clearing displayed cell outputs, stopping a local service or Spark session, resetting learner files, and clearing generated state. Provide a narrowly scoped `git restore` command for the lab's pre-created learner files and instruct the learner to close any affected editor buffers first. Stateful labs must additionally provide a bounded, lab-specific reset operation for generated data, broker offsets, checkpoints, tables, or files; clearing notebook outputs never resets external state.

## Dataset contract

Use synthetic structured records only unless a lab explicitly teaches media or binary processing. A `videos` dataset contains metadata and events, not actual video files.

Each reusable scenario delivery should document:

| Field | Required content |
| --- | --- |
| Delivery ID | Stable batch identity |
| Source system | Producer or source boundary |
| Format | CSV, JSON Lines, Parquet, Avro, or another justified format |
| Record grain | One sentence defining a record |
| Schema version | Contract version used to parse the delivery |
| Expected counts | Received, accepted, rejected, deduplicated, and published where applicable |
| Intentional edge cases | Exact list of nulls, duplicates, missing references, late records, corrections, and boundary values |
| Mutability | Source fixtures are immutable; generated outputs are replaceable or versioned as declared |

Do not share a fixture merely because two tables have similar columns. Reuse is appropriate when the questions share the same business grain and source contract.

## Verification contract

Select evidence in proportion to the lab scope:

| Evidence | Technique drill | Component | Pipeline slice | System flow |
| --- | --- | --- | --- | --- |
| Schema and row assertions | Required | Required | Required | Required |
| Boundary and null cases | Required | Required | Required | Required |
| Unit tests | When reusable code exists | Required | Required | Required |
| Idempotent rerun | Optional | When stateful | Required | Required |
| Source-to-target reconciliation | Optional | When ingesting | Required | Required |
| Failure injection and recovery | No | Optional | At important boundaries | Required |
| Plan or performance evidence | When technique-sensitive | When relevant | Required for material operations | Required |
| Operational command verification | No | When applicable | Required | Required |

The learner-facing checker owns feedback on the learner's attempt. Separate author-side tests own correctness evidence for maintained reference implementations and lab infrastructure. Do not present author maintenance tests as environment checks or require students to inspect them. Once a lab introduces reusable artifacts, tests should exercise those artifacts outside the notebook as well.

## Solution and explanation contract

The solution document is separate from the learner notebook so it does not reveal the answer during the initial attempt. Use this structure:

```markdown
# <Lab ID>: <Title> — Solution and Explanation

## Outcome
State what was built and the verified result.

## Reference implementation
Link the completed Python, SQL, script, configuration, and test artifacts.

## Why it is correct
Explain grain, keys, predicates, joins, null behavior, time boundaries, decimals, duplicates, tie handling, and ordering that materially affect correctness.

## Walkthrough
Explain the important transformations in execution order without restating every line.

## Alternatives and tradeoffs
Compare reasonable alternatives and state when each becomes preferable.

## Pitfalls
Describe plausible incorrect implementations and the failures the tests expose.

## Distributed and performance behavior
Identify actions, exchanges, partition implications, driver boundaries, and scale limits appropriate to the lab.

## Verification evidence
List exact commands and results that actually ran. Separate local evidence from claims that remain unverified.

## Production extension
Describe what would change for larger scale, orchestration, security, observability, recovery, or a real platform.
```

## First-example constraint

`DV-E23` remains an Easy technique drill. The notebook links a pre-created Python learner module, explicitly reloads its saved function, and uses a **Check my work** cell for feedback. A separate spoiler-marked executable reference implementation and author tests verify the maintained lab materials without appearing in learner navigation. The lab uses a small synthetic video-metadata fixture to teach explicit schema use, filtering, projection, deterministic ordering, functions, and DataFrame verification. It does not add bronze, silver, gold, cron, or broker infrastructure merely to appear job-like. Those concerns enter later component, pipeline-slice, and system-flow labs where they are the techniques being taught.

After completing `DV-E23`, review the template for learner friction, duplicated setup, test readability, solution usefulness, actual completion time, and whether the boundary between notebook guidance and implementation files feels natural. Revise this template before generating the remaining catalog.
