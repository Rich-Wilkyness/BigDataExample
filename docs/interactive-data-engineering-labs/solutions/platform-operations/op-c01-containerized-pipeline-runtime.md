# OP-C01: Containerized Pipeline Runtime — Solution and Explanation

## Outcome

The completed runtime builds one reusable Python pipeline image, starts PostgreSQL as a separate healthy service, mounts an immutable host CSV into a one-shot pipeline container, persists database files in a named volume, and writes the final report through a host bind mount. The learner runs the complete flow with `./run_pipeline.sh`.

## Reference implementation

The original completed [Week 2 weekend project](../../../Training/Week2/weekend_project/README.md) is the source experience from which this lab was derived. The OP-C01 solution below uses isolated names and paths so it cannot modify that project.

### Dockerfile

```dockerfile
FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .

RUN python -m pip install --no-cache-dir -r requirements.txt

COPY pipeline.py .

CMD ["python", "pipeline.py"]
```

### docker-compose.yml

```yaml
name: op-c01-container-runtime

services:
  postgres:
    image: postgres:18
    environment:
      POSTGRES_USER: ${POSTGRES_USER}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
      POSTGRES_DB: ${POSTGRES_DB}
    ports:
      - "${POSTGRES_PORT:-55432}:5432"
    volumes:
      - postgres-data:/var/lib/postgresql
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U $${POSTGRES_USER} -d $${POSTGRES_DB}"]
      interval: 2s
      timeout: 5s
      retries: 15
      start_period: 5s

  pipeline:
    build: .
    depends_on:
      postgres:
        condition: service_healthy
    environment:
      DATABASE_URL: postgresql+psycopg://${POSTGRES_USER}:${POSTGRES_PASSWORD}@postgres:5432/${POSTGRES_DB}
      INPUT_FILE: /app/input/sales.csv
      OUTPUT_FILE: /app/output/sales_report.csv
    volumes:
      - type: bind
        source: ${SALES_CSV_PATH}
        target: /app/input/sales.csv
        read_only: true
      - type: bind
        source: ./output
        target: /app/output

volumes:
  postgres-data:
```

### run_pipeline.sh

```bash
#!/usr/bin/env bash

set -euo pipefail

PROJECT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
REPOSITORY_ROOT="$(cd -- "$PROJECT_DIR/../../../.." && pwd)"
cd "$PROJECT_DIR"

INPUT_FILE="$REPOSITORY_ROOT/data/samples/interactive-data-engineering-labs/platform-operations/op-c01-containerized-pipeline-runtime/sales.csv"
OUTPUT_DIR="$PROJECT_DIR/output"

if [[ ! -f "$INPUT_FILE" ]]; then
    echo "Error: expected input file at $INPUT_FILE"
    exit 1
fi

mkdir -p "$OUTPUT_DIR"

if [[ ! -f ".env" ]]; then
    cp .env.example .env
fi

export SALES_CSV_PATH="$INPUT_FILE"

echo "Starting PostgreSQL"
docker compose up --detach --wait postgres

echo "Building and running the supplied pipeline"
docker compose run --rm --build pipeline

echo "Pipeline complete: $OUTPUT_DIR/sales_report.csv"
```

## Why it is correct

The Dockerfile owns build-time contents only: Python, declared dependencies, and the supplied application code. The source CSV remains outside the image so a new delivery does not require rebuilding an otherwise identical runtime. Credentials remain outside the image so image layers do not preserve them.

Compose creates one private network. The pipeline uses `postgres:5432` because `postgres` is service discovery inside that network. `${POSTGRES_PORT}:5432` is a different boundary: it maps a port on the host to the PostgreSQL container for host-side clients.

The CSV bind mount crosses a host-to-container file boundary and is read-only. The output bind mount crosses the boundary in the writable direction. The named volume is managed by Docker and preserves PostgreSQL's internal files independently of both host directories.

The healthcheck establishes readiness rather than mere process creation. `depends_on` with `condition: service_healthy` prevents the pipeline from racing PostgreSQL initialization.

`create_engine(DATABASE_URL)` creates a SQLAlchemy connection manager. It does not create the PostgreSQL process, network, database, schema, or table. Compose creates the process and initial database; the supplied Python process opens a connection and creates application-owned schema/table objects inside that database.

## Walkthrough

`run_pipeline.sh` resolves stable absolute host paths, validates the input, creates replaceable host state, and exports the CSV path for Compose interpolation. Compose starts the long-running PostgreSQL service, builds the pipeline image, and creates a one-shot pipeline container. The supplied Python program cleans the CSV, replaces the table rows transactionally, executes the SQL aggregation, and writes the report through the output bind mount. `--rm` removes the completed pipeline container while leaving the image and PostgreSQL service available.

## Alternatives and tradeoffs

A host-installed Python process could connect through `localhost:${POSTGRES_PORT}`, but that would require every learner machine to reproduce Python and dependency installation outside Docker. A single container could run Python and PostgreSQL together, but lifecycle, readiness, logs, upgrades, and persistence become coupled. A separate migration tool becomes preferable when schema evolution exceeds a small idempotent setup block.

Docker secrets or an external secret manager should replace `.env` credentials in a production environment. The lab uses an ignored development `.env` because the goal is local runtime wiring.

## Pitfalls

- `localhost` inside the pipeline container refers to that pipeline container, not PostgreSQL.
- A host path is meaningless inside a container unless it is mounted.
- `docker compose run --rm` removes a container, not its image.
- `docker compose down` removes containers and the network but retains named volumes; `down --volumes` deletes this lab's database state.
- Changing `POSTGRES_DB`, user, or password does not reinitialize an already populated PostgreSQL volume.
- `docker exec` requires both a container and a command; `docker compose exec postgres psql ...` avoids unstable container IDs.

## Verification evidence

The maintained lab checks shell and Python syntax, notebook structure, unresolved setup placeholders, Compose configuration, script executability, PostgreSQL health, persisted row count, and source-to-report reconciliation. Coverage records runtime behavior only after those runtime checks have executed against a completed learner setup.

## Production extension

A production version would pin or attest image dependencies, publish the pipeline image through a registry, inject secrets outside Compose files, run database migrations separately, emit structured run metadata and metrics, enforce resource limits, and execute the one-shot job through a scheduler or orchestrator. The storage and retry policy would distinguish full refreshes from incremental ingestion rather than truncating on every run.
