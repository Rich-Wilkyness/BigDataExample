# Infrastructure

Local service definitions and later deployment examples belong here. Initial
work should stay vendor-neutral. PostgreSQL, object storage, Spark, Kafka, and
orchestration services will be added only when their owning curriculum topics
require executable evidence.

Infrastructure examples must state resource assumptions, persistence behavior,
health checks, shutdown behavior, and cleanup procedures.

## Local services

- [PostgreSQL](postgres/README.md) — PostgreSQL 18.6 on `127.0.0.1:5432` with ignored local credentials, a health check, and named-volume persistence for SQL exercises.
