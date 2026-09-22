#!/usr/bin/env bash

set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
container_name="big-data-example-postgres"
database_name="week3_hive_migration"
database_user="bigdata"
maintenance_database="bigdata"
source_dir="$repo_root/docs/Training/Week3/2.1_hive_migration/tmp/data"
container_data_dir="/tmp/week3_hive_migration_data"
sql_dir="$repo_root/sql/hive-migration"

if [[ ! -d "$source_dir" ]]; then
    echo "Missing source directory: $source_dir" >&2
    exit 1
fi

csv_count="$(find "$source_dir" -type f -name '*.csv' | wc -l | tr -d ' ')"
if [[ "$csv_count" != "10" ]]; then
    echo "Expected 10 CSV files under $source_dir, found $csv_count" >&2
    exit 1
fi

if [[ "$(docker inspect --format '{{.State.Running}}' "$container_name" 2>/dev/null || true)" != "true" ]]; then
    echo "Container $container_name is not running." >&2
    echo "Start it with: docker compose --env-file infra/postgres/.env -f infra/postgres/compose.yml up -d" >&2
    exit 1
fi

docker exec "$container_name" mkdir -p \
    "$container_data_dir/bronze" \
    "$container_data_dir/silver" \
    "$container_data_dir/gold"
docker cp "$source_dir/." "$container_name:$container_data_dir"

docker exec -i "$container_name" \
    psql -X -v ON_ERROR_STOP=1 -U "$database_user" -d "$maintenance_database" \
    < "$sql_dir/create-database.sql"
docker exec -i "$container_name" \
    psql -X -v ON_ERROR_STOP=1 -U "$database_user" -d "$database_name" \
    < "$sql_dir/setup.sql"
docker exec -i "$container_name" \
    psql -X -v ON_ERROR_STOP=1 -U "$database_user" -d "$database_name" \
    < "$sql_dir/verify.sql"
