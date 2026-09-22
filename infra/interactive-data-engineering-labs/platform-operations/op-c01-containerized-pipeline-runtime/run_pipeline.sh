#!/usr/bin/env bash

# Learner file for OP-C01. Replace each __PLACEHOLDER__ while completing Checkpoint 4.
set -euo pipefail

PROJECT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
REPOSITORY_ROOT="$(cd -- "$PROJECT_DIR/../../../.." && pwd)"
cd "$PROJECT_DIR"

INPUT_FILE="$REPOSITORY_ROOT/__SOURCE_CSV_PATH__"
OUTPUT_DIR="$PROJECT_DIR/output"

__CHECK_INPUT_FILE__
__CREATE_OUTPUT_DIRECTORY__
__CREATE_LOCAL_ENV_IF_MISSING__
__EXPORT_COMPOSE_INPUT_PATH__

echo "Starting PostgreSQL"
__START_POSTGRES_AND_WAIT__

echo "Building and running the supplied pipeline"
__BUILD_AND_RUN_PIPELINE__

echo "Pipeline complete: $OUTPUT_DIR/sales_report.csv"
