#!/usr/bin/env bash

# START HERE: this is the host-side coordinator for the pipeline.
# It does not clean data or connect to PostgreSQL itself. Its responsibilities are:
# 1. Find and validate files on the user's computer (the host).
# 2. Create the local output directory and runtime .env file when needed.
# 3. Give Docker Compose the host CSV path that it must mount into the pipeline container.
# 4. Start PostgreSQL, build the Python image, and run the Python container.
#
# Compose automatically creates a private network for the two services. On that network, the
# Python container reaches PostgreSQL with the service name "postgres", so this script does not
# need to create a Docker network or manually manage container names.


# -e: stop when a command fails.
# -u: stop when an undefined variable is used.
# -o pipefail: consider a pipeline failed if any command within it fails.
set -euo pipefail

# Anchor every relative path to this script's directory. This makes ./run_pipeline.sh behave the
# same way even if the user invokes it while their terminal is in a different directory.
PROJECT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_DIR"

# These are host paths. The containers cannot see them until docker-compose.yml bind-mounts them.
INPUT_FILE="$PROJECT_DIR/data/sales.csv"
OUTPUT_DIR="$PROJECT_DIR/output"

# Docker can mount an existing host directory, so make sure the report destination exists first.
mkdir -p "$OUTPUT_DIR"

# Export makes this shell variable visible to Docker Compose. Compose uses it as the bind mount's
# source, while /app/input/sales.csv is the corresponding path inside the pipeline container.
export SALES_CSV_PATH="$INPUT_FILE"

echo "Running Sales Report .csv to SQL pipeline"

if [[ ! -f "$INPUT_FILE" ]]; then
    echo "Error: expected input file at: $INPUT_FILE"
    exit 1
fi

if [[ ! -f ".env" ]]; then
    echo "Creating local .env from .env.example"
    # .env contains local PostgreSQL settings. Compose reads it automatically from this directory.
    cp .env.example .env
fi

echo "Starting PostgreSQL"
# --detach leaves PostgreSQL running; --wait waits for the Compose healthcheck to report healthy.
docker compose up --detach --wait postgres

echo "Building and running the pipeline"
# --build creates/updates the pipeline image from Dockerfile.
# --rm removes the one-run pipeline container afterward; it does not remove the reusable image.
docker compose run --rm --build pipeline

echo "Pipeline completed successfully"
echo "data available in persistent volume."
echo "Run 'docker compose down' when you want to stop PostgreSQL."
echo "Report available at: $OUTPUT_DIR/sales_report.csv"
