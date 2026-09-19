# Local PostgreSQL

This Compose project runs PostgreSQL 18.6 for local SQL and data-engineering exercises. It is a single-node development database, not a production deployment.

## Configuration

Compose reads connection settings from the ignored `infra/postgres/.env` file. The tracked `.env.example` documents the required variables without committing a password.

| Setting | Local value | Purpose |
| --- | --- | --- |
| Host | `127.0.0.1` | Prevents PostgreSQL from being published on every host interface. |
| Port | `5432` | Standard PostgreSQL client port. |
| Database | `bigdata` | Default learning database. |
| User | `bigdata` | Local learning superuser created during initialization. |
| Storage | `big-data-example-postgres-data` | Named Docker volume that survives container recreation. |
| Shared memory | 128 MiB | Explicit local starting allocation for PostgreSQL container operations. |

## Start and verify

Run these commands from the repository root:

```bash
docker compose --env-file infra/postgres/.env -f infra/postgres/compose.yml up -d
docker compose --env-file infra/postgres/.env -f infra/postgres/compose.yml ps
```

The service is ready when its status is `healthy`. Inspect initialization or startup failures with:

```bash
docker compose --env-file infra/postgres/.env -f infra/postgres/compose.yml logs postgres
```

## Connect

Open `psql` inside the running container:

```bash
docker exec -it big-data-example-postgres psql -U bigdata -d bigdata
```

Useful first commands inside `psql`:

```text
SELECT version();
\conninfo
\l
\dt
\q
```

A host application or database client can use:

```text
Host: 127.0.0.1
Port: 5432
Database: bigdata
User: bigdata
Password: the POSTGRES_PASSWORD value in infra/postgres/.env
```

## Stop, restart, and remove

Stop and remove the container and network while retaining the named database volume:

```bash
docker compose --env-file infra/postgres/.env -f infra/postgres/compose.yml down
```

Start it again with `up -d`; existing database state will be reused.

To permanently delete the local database, add `--volumes` to `down`. This erases all PostgreSQL data stored by this Compose project:

```bash
docker compose --env-file infra/postgres/.env -f infra/postgres/compose.yml down --volumes
```

`POSTGRES_USER`, `POSTGRES_PASSWORD`, and `POSTGRES_DB` initialize only an empty data directory. Changing them later does not modify roles, passwords, or databases already stored in the named volume.
