# BigDataExample

`BigDataExample` is a learning repository for progressing from data-engineering
fundamentals to senior-level big-data system design. Python and SQL are the
primary implementation languages. Tools such as DuckDB, PostgreSQL, Apache
Spark, Kafka, Airflow, and open table formats will be introduced only when their
underlying concepts and tradeoffs are clear.

The curriculum assumes strong Kotlin and Android engineering experience but no
prior data-engineering experience. Comparisons to Kotlin, coroutines, Room/SQLite,
Gradle, and mobile telemetry may be used as bridges; they are not substitutes
for learning data-system semantics.

## Repository layout

```text
BigDataExample/
|-- data/                    Local data policy and future sample datasets
|-- docs/                    Curriculum map, templates, and coverage evidence
|-- infra/                   Future local/distributed service definitions
|-- notebooks/               Disposable exploration and visualization
|-- scripts/                 Repeatable developer and data operations
|-- sql/                     Versioned DDL, transformations, and analysis
|-- src/big_data_example/    Reusable Python application and pipeline code
|-- tests/                   Unit, integration, contract, and data-quality tests
|-- pyproject.toml           Python package metadata and tool configuration
`-- README.md                Project entry point
```

Reusable behavior belongs in `src/` or `sql/`, not only in notebooks. Large,
generated, sensitive, or licensed datasets must not be committed. Small,
documented fixtures may be added later under a dedicated sample-data location.

## Curriculum

Start with the [curriculum map](docs/README.md). The initial 16-area scope and
its implementation/evidence state are maintained in
[curriculum coverage](docs/COVERAGE.md).

Fresh sessions begin with the repository-local [agent guide](AGENTS.md), which
routes each task to the minimum relevant documentation. Prior conversation
context is not required.

Learning guides and interview questions use different authoring contracts:

- [Learning topic template](docs/TOPIC_TEMPLATE.md)
- [Interview preparation workflow](docs/INTERVIEW_PREP_WORKFLOW.md)
- [Interview question template](docs/INTERVIEW_QUESTION_TEMPLATE.md)
- [Python and SQL interview questions](docs/LANGUAGE_INTERVIEW_QUESTIONS.md)
- [Data engineering platform interview questions](docs/PLATFORM_INTERVIEW_QUESTIONS.md)

## Current verification

The bootstrap package uses only the Python standard library. Verify it with:

```powershell
python -m unittest discover -s tests
```

Dependencies and runnable data-platform infrastructure will be selected as the
owning curriculum topics are implemented.

## Optional PySpark notebook practice

VS Code notebook practice uses the optional `spark-notebook` dependency group. On Windows, create the project environment with the selected Python interpreter and install the project plus that group:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[spark-notebook]"
```

Open an `.ipynb` file in VS Code, choose **Select Kernel**, and select `.venv\Scripts\python.exe`. The Microsoft Python and Jupyter extensions are required in VS Code, and local classic PySpark also requires a supported Java runtime through `JAVA_HOME` or `PATH`.

The local Windows setup was smoke-tested on 2026-09-12 with Python 3.14.5, PySpark 4.2.0, and Java 21. The check started a `local[2]` session, ran a two-partition DataFrame filter through Python workers, collected the expected row, and stopped the session. This proves the local environment starts and executes a small job; it does not prove the topic-level correctness, plan, failure, or performance claims tracked in Area 09.

The first complete worked lab is [DV-E23 High-Engagement Video Filtering](notebooks/interactive-data-engineering-labs/content-platform/dv-e23-high-engagement-video-filtering.ipynb), with its [solution and explanation](docs/interactive-data-engineering-labs/solutions/content-platform/dv-e23-high-engagement-video-filtering.md) kept separately. The [interactive lab learner guide](notebooks/interactive-data-engineering-labs/README.md) explains how question-specific implementation files relate to notebooks and tests, how to run the lab in VS Code, and how to restart or reset an attempt. Source intake and lab-authoring plans remain under [`docs/interactive-data-engineering-labs/`](docs/interactive-data-engineering-labs/README.md).
