# WH-M01 Lab Commands

Run every command from the repository root with the repository `.venv` active. These commands read `infra/postgres/.env` but never display its password.

## Install the lab dependencies

```bash
./.venv/bin/python -m pip install -e '.[warehouse-lab]'
```

## Create and verify the isolated database

```bash
./.venv/bin/python scripts/interactive-data-engineering-labs/retail-sales/wh-m01-medallion-sales-pipeline/setup-lab.py
./.venv/bin/python scripts/interactive-data-engineering-labs/retail-sales/wh-m01-medallion-sales-pipeline/verify-lab.py
```

Both commands are safe to rerun. Setup creates `week3_medallion_lab` only when it is missing.

## Generate, load, and verify Stage 1

Generate the source delivery, create Bronze, and run the Stage 1 checker:

```bash
./.venv/bin/python scripts/interactive-data-engineering-labs/retail-sales/wh-m01-medallion-sales-pipeline/generate-source.py
./.venv/bin/python scripts/interactive-data-engineering-labs/retail-sales/wh-m01-medallion-sales-pipeline/load-bronze.py
./.venv/bin/python scripts/interactive-data-engineering-labs/retail-sales/wh-m01-medallion-sales-pipeline/verify-stage1.py
```

The generator verifies an existing delivery and refuses to overwrite changed data. After reviewing an accidental edit, restore the exact deterministic delivery with:

```bash
./.venv/bin/python scripts/interactive-data-engineering-labs/retail-sales/wh-m01-medallion-sales-pipeline/generate-source.py --force
```

## Inspect PostgreSQL directly

Start or confirm the existing repository service:

```bash
docker compose --env-file infra/postgres/.env -f infra/postgres/compose.yml up -d
docker compose --env-file infra/postgres/.env -f infra/postgres/compose.yml ps
```

Enter `psql` through the container:

```bash
docker exec -it big-data-example-postgres psql -U bigdata -d postgres
```

Run these commands after the PostgreSQL prompt appears:

```text
\l
\c week3_medallion_lab
\conninfo
\dn
\dt bronze.*
\dt silver.*
\dt gold.*
\q
```

The backslash commands belong inside `psql`, not in Bash, and do not use semicolons. After Stage 1, `\dt bronze.*` shows `bronze.sales_transactions`; the Silver and Gold commands report no matching relations.

## Reset Gold only

```bash
./.venv/bin/python scripts/interactive-data-engineering-labs/retail-sales/wh-m01-medallion-sales-pipeline/reset-lab.py gold
```

This drops only `gold` inside `week3_medallion_lab`. It preserves the generated source delivery, Bronze, and Silver so you can repeat Stage 3.

## Reset Silver and downstream Gold

```bash
./.venv/bin/python scripts/interactive-data-engineering-labs/retail-sales/wh-m01-medallion-sales-pipeline/reset-lab.py silver
```

This drops `gold` first and then `silver`, because Gold depends on Silver. It preserves the generated source delivery and Bronze so you can repeat Stages 2 and 3.

## Reset every database layer

```bash
./.venv/bin/python scripts/interactive-data-engineering-labs/retail-sales/wh-m01-medallion-sales-pipeline/reset-lab.py schemas
```

This drops `gold`, `silver`, and `bronze` while preserving the generated source delivery. Use it when you want to repeat ingestion beginning with Stage 1.

## Remove the entire lab database

**Destructive for this lab:** the following command removes all objects in `week3_medallion_lab`. The exact confirmation is intentional.

```bash
./.venv/bin/python scripts/interactive-data-engineering-labs/retail-sales/wh-m01-medallion-sales-pipeline/reset-lab.py database --confirm week3_medallion_lab
```

No reset mode targets `week3_hw`, `bigdata`, the PostgreSQL container, or the Docker volume.
