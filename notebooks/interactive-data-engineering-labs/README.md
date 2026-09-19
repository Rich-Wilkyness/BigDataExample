# Interactive Data Engineering Labs

This directory is the learner entry point for executable, job-shaped data-engineering practice. Each notebook presents the problem, schema or data contract, checkpoints, immediate validation, and a separate solution.

## Available labs

| Lab | Difficulty | Scope | Effort | Tooling | Status |
| --- | --- | --- | --- | --- | --- |
| [DV-E23 High-Engagement Video Filtering](content-platform/dv-e23-high-engagement-video-filtering.ipynb) | Easy | Technique drill | 30-45 minutes | Python, PySpark, Spark | Ready to attempt |
| [WH-M01 Medallion Sales Pipeline](retail-sales/wh-m01-medallion-sales-pipeline.ipynb) | Medium | System flow | Multiple sessions | Python, pandas, SQL, PostgreSQL | Stage 1 ready through Bronze; stop before Silver |

## How a lab is organized

The notebook is the guide, runner, and feedback surface. Each lab links to pre-created learner files that hold the actual work. A short drill may use one Python or SQL file; a pipeline lab may provide several Python, SQL, shell, configuration, or infrastructure files. A file may begin mostly empty because deciding and implementing its behavior is the exercise.

This structure separates orchestration from deliverables: notebooks make exploration and feedback convenient, while `src/`, `sql/`, `scripts/`, and `infra/` resemble the versioned artifacts that jobs, schedulers, deployments, and other engineers can invoke without manually running a notebook. Every checkpoint must say exactly which linked file to modify and how the notebook loads it.

## One-time environment setup

Create `.venv` once for this repository, not every time you open VS Code. Repeat installation only if you delete `.venv` or the project dependencies change.

On Windows, run from the repository root in PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[spark-notebook]"
```

Open a lab notebook, choose **Select Kernel**, and select `.venv\Scripts\python.exe`. VS Code also needs the Microsoft Python and Jupyter extensions, and local PySpark needs Java available through `JAVA_HOME` or `PATH`.

On macOS or Linux, the environment directory is the same but its Python executable is in `bin`:

```bash
python3 -m venv .venv
./.venv/bin/python -m pip install -e '.[spark-notebook]'
```

Then select `.venv/bin/python` as the notebook kernel. The dependency result is the same on all three platforms; only the Python launcher and virtual-environment executable path differ.

## Run DV-E23 in VS Code

1. Open the [DV-E23 notebook](content-platform/dv-e23-high-engagement-video-filtering.ipynb).
2. Select the repository's `.venv` kernel.
3. Read the visible problem and schema, then follow the checkpoints.
4. Open the learner file linked from Checkpoint 2 and complete `build_high_engagement_videos` there.
5. Save the learner file, return to the notebook, and run Checkpoint 2. Its explicit reload line imports your newest saved implementation; no notebook magic is involved.
6. Run the Checkpoint 3 **Check my work** cell. It checks the result produced by your learner file and reports a focused contract error or `PASS`.
7. Continue through the plan and reflection sections, then stop Spark with the cleanup cell.

The setup cell confirms that Python and Spark start successfully. That is an environment check. The **Check my work** cell validates your transformation. Author-side unit tests exist for maintaining the curriculum's reference implementation, but the learner workflow does not link to or require those tests.

## Restart, clear, and reset

- **Restart execution state:** choose **Restart** in the VS Code notebook toolbar, then **Run All**. This creates a fresh Python kernel and Spark session.
- **Clear displayed output:** choose **Clear All Outputs** in the notebook toolbar or Command Palette. This changes notebook presentation, not the implementation or data.
- **Stop Spark only:** run the notebook's cleanup cell.
- **Reset the learner implementation:** after the baseline files are committed, close the learner file and inspect `git diff -- src/big_data_example/labs/content_platform/dv_e23_high_engagement_video_filtering.py`. Then run the command below from the repository root. It deliberately discards changes to only that pre-created learner file.

```powershell
git restore -- src/big_data_example/labs/content_platform/dv_e23_high_engagement_video_filtering.py
```

DV-E23 reads immutable fixtures and does not write generated data, so it has no generated-output cleanup step. A stateful ingestion or bronze/silver/gold lab must supply its own bounded reset command and identify exactly which generated directory it removes or recreates.

## How this maps to job work

DV-E23 represents the smallest unit of real pipeline work rather than an entire job assignment: interpret a consumer requirement, understand the input contract, implement testable transformation logic, inspect representative data, verify edge cases, and reason about the Spark plan. A production ticket could contain exactly this transformation, but it would usually live inside a larger ingestion or publication flow.

The lab sequence should expand independently along difficulty and delivery scope:

| Scope | Job-shaped responsibility introduced |
| --- | --- |
| Technique drill | Implement and test one schema, transformation, query, shell operation, or scheduling technique. |
| Component exercise | Build one reusable reader, transform, quality gate, command-line job, cron definition, producer, or consumer. |
| Pipeline slice | Cross a real boundary such as source to bronze, bronze to silver, or silver to gold with contracts, reconciliation, idempotent reruns, and failure handling. |
| System flow | Operate cooperating components such as producer to Kafka to consumer to storage, including observability, recovery, schema evolution, security, performance, and cost tradeoffs. |

This progression is intended to teach both tool mechanics and the engineering flow around them. Later labs should not merely make the datasets larger; they should add ownership boundaries, operational state, failure modes, deployment-style entry points, and evidence that mirrors production responsibilities.

The maintained [lab coverage inventory](../../docs/interactive-data-engineering-labs/coverage.md) records what has actually been introduced, practiced, verified, or operated and identifies the important gaps for subsequent labs.

## Authoring and solutions

The [lab design documents](../../docs/interactive-data-engineering-labs/README.md) own source intake, cataloging, reusable scenario planning, and the authoring template. Explanatory solutions stay under `docs/interactive-data-engineering-labs/solutions/` because they are durable documentation rather than executable notebooks. If a future solution is itself an executable comparison notebook, that notebook will live under `notebooks/` and the explanation will link to it.
