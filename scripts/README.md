# Scripts

Repeatable bootstrap, ingestion, backfill, validation, and evidence-collection
commands may be added here. Scripts must fail safely, validate destructive
targets, avoid embedded credentials, and document whether rerunning them is
idempotent.

## Interactive lab support

- [`OP-C01` verification](interactive-data-engineering-labs/platform-operations/op-c01-containerized-pipeline-runtime/verify-lab.py) checks the completed setup contract and, after execution, verifies PostgreSQL state and source-to-report reconciliation.
- [`OP-C02` verification](interactive-data-engineering-labs/platform-operations/op-c02-sqlalchemy-pipeline-setup/verify-lab.py) checks the learner's Python and SQLAlchemy setup contract and, after execution, verifies PostgreSQL state and source-to-report reconciliation.

## Training data loaders

- [`load-hive-migration-postgres.sh`](load-hive-migration-postgres.sh) copies the Week 3 migration CSV fixtures into the PostgreSQL container and recreates only the isolated `week3_hive_migration` schemas.
