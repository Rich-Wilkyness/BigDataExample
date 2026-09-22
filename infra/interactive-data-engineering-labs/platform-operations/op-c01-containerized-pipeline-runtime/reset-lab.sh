#!/usr/bin/env bash

set -euo pipefail

PROJECT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
REPOSITORY_ROOT="$(cd -- "$PROJECT_DIR/../../../.." && pwd)"
cd "$PROJECT_DIR"

if [[ "${1:-}" != "--force" ]]; then
    echo "This removes only OP-C01 containers, its network, its named volume, .env, and generated report."
    echo "Run: ./reset-lab.sh --force"
    exit 1
fi

export SALES_CSV_PATH="$REPOSITORY_ROOT/data/samples/interactive-data-engineering-labs/platform-operations/op-c01-containerized-pipeline-runtime/sales.csv"

docker compose --env-file .env.example down --volumes --remove-orphans
rm -f "$PROJECT_DIR/output/sales_report.csv"
rm -f "$PROJECT_DIR/.env"

echo "OP-C01 generated state removed. Learner files were preserved."
