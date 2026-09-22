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

echo "Starting the isolated OP-C02 PostgreSQL service"
docker compose up --detach --wait postgres

echo "Building and running the learner's Python setup"
docker compose run --rm --build pipeline

echo "OP-C02 complete: $OUTPUT_DIR/sales_report.csv"
