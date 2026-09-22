# Infrastructure

Local service definitions and later deployment examples belong here. Initial
work should stay vendor-neutral. PostgreSQL, object storage, Spark, Kafka, and
orchestration services will be added only when their owning curriculum topics
require executable evidence.

Infrastructure examples must state resource assumptions, persistence behavior,
health checks, shutdown behavior, and cleanup procedures.

## Local services

- [PostgreSQL](postgres/README.md) — PostgreSQL 18.6 on `127.0.0.1:5432` with ignored local credentials, a health check, and named-volume persistence for SQL exercises.
- [OP-C01 learner workspace](interactive-data-engineering-labs/platform-operations/op-c01-containerized-pipeline-runtime/README.md) — isolated starter artifacts for practicing a two-container pipeline runtime, host/container mounts, health-gated startup, persistence, and bounded cleanup.
- [OP-C02 supplied runtime](interactive-data-engineering-labs/platform-operations/op-c02-sqlalchemy-pipeline-setup/README.md) — an isolated two-container runtime that lets the learner focus on Python configuration, SQLAlchemy, PostgreSQL DDL and loading, report SQL, and output publication.
