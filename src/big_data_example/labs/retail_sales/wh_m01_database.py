"""Safe PostgreSQL setup and reset helpers for the WH-M01 medallion lab."""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path

from sqlalchemy import URL, Engine, create_engine, text


LAB_DATABASE = "week3_medallion_lab"
LAB_SCHEMAS = ("gold", "silver", "bronze")
LAB_LAYER_RESET_ORDER = {
    "gold": ("gold",),
    "silver": ("gold", "silver"),
    "schemas": LAB_SCHEMAS,
}
REQUIRED_ENV_KEYS = (
    "POSTGRES_USER",
    "POSTGRES_PASSWORD",
    "POSTGRES_DB",
    "POSTGRES_PORT",
)
POSTGRES_CONTAINER = "big-data-example-postgres"


@dataclass(frozen=True)
class PostgresConfig:
    """Connection values loaded from the repository-managed PostgreSQL file."""

    user: str
    password: str
    maintenance_database: str
    port: int
    host: str = "127.0.0.1"


def repository_root(start: Path | None = None) -> Path:
    """Find the repository root without depending on the caller's directory."""

    current = (start or Path.cwd()).resolve()
    for candidate in (current, *current.parents):
        if (candidate / "pyproject.toml").is_file() and (candidate / "AGENTS.md").is_file():
            return candidate
    raise RuntimeError("Could not locate the BigDataExample repository root.")


def load_postgres_config(root: Path | None = None) -> PostgresConfig:
    """Read PostgreSQL settings without printing or returning a connection string."""

    env_path = (root or repository_root()) / "infra" / "postgres" / ".env"
    if not env_path.is_file():
        raise FileNotFoundError(
            "Missing infra/postgres/.env. Copy infra/postgres/.env.example and set a local password."
        )

    values: dict[str, str] = {}
    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip().strip('"').strip("'")

    missing = [key for key in REQUIRED_ENV_KEYS if not values.get(key)]
    if missing:
        raise RuntimeError(f"Missing required PostgreSQL settings: {', '.join(missing)}")

    return PostgresConfig(
        user=values["POSTGRES_USER"],
        password=values["POSTGRES_PASSWORD"],
        maintenance_database=values["POSTGRES_DB"],
        port=int(values["POSTGRES_PORT"]),
    )


def make_engine(database: str, root: Path | None = None) -> Engine:
    """Create an engine for only the configured maintenance DB or WH-M01 DB."""

    config = load_postgres_config(root)
    allowed_databases = {config.maintenance_database, LAB_DATABASE}
    if database not in allowed_databases:
        raise ValueError(
            f"Refusing connection to {database!r}; allowed databases are {sorted(allowed_databases)}."
        )

    url = URL.create(
        drivername="postgresql+psycopg2",
        username=config.user,
        password=config.password,
        host=config.host,
        port=config.port,
        database=database,
    )
    return create_engine(url, pool_pre_ping=True)


def verify_container_health() -> str:
    """Return the Docker health status for the repository PostgreSQL container."""

    result = subprocess.run(
        [
            "docker",
            "inspect",
            "--format",
            "{{if .State.Health}}{{.State.Health.Status}}{{else}}{{.State.Status}}{{end}}",
            POSTGRES_CONTAINER,
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    status = result.stdout.strip()
    if status != "healthy":
        raise RuntimeError(f"{POSTGRES_CONTAINER} is {status!r}, not 'healthy'.")
    return status


def create_lab_database(root: Path | None = None) -> bool:
    """Create only week3_medallion_lab; return True when creation occurred."""

    config = load_postgres_config(root)
    engine = make_engine(config.maintenance_database, root)
    try:
        with engine.connect().execution_options(isolation_level="AUTOCOMMIT") as connection:
            exists = connection.execute(
                text("SELECT 1 FROM pg_database WHERE datname = :database_name"),
                {"database_name": LAB_DATABASE},
            ).scalar_one_or_none()
            if exists:
                return False
            connection.execute(text(f'CREATE DATABASE "{LAB_DATABASE}"'))
            return True
    finally:
        engine.dispose()


def verify_lab_connection(root: Path | None = None) -> dict[str, str]:
    """Return non-secret evidence from a SQLAlchemy connection to the lab DB."""

    engine = make_engine(LAB_DATABASE, root)
    try:
        with engine.connect() as connection:
            row = connection.execute(
                text(
                    "SELECT current_database() AS database_name, "
                    "current_user AS database_user, "
                    "current_setting('server_version') AS server_version"
                )
            ).mappings().one()
            return dict(row)
    finally:
        engine.dispose()


def reset_lab_layers(reset_point: str, root: Path | None = None) -> tuple[str, ...]:
    """Drop a requested lab layer and every derived downstream layer."""

    if reset_point not in LAB_LAYER_RESET_ORDER:
        raise ValueError(
            f"Unknown reset point {reset_point!r}; choose from {sorted(LAB_LAYER_RESET_ORDER)}."
        )

    engine = make_engine(LAB_DATABASE, root)
    schemas = LAB_LAYER_RESET_ORDER[reset_point]
    try:
        with engine.begin() as connection:
            for schema in schemas:
                connection.execute(text(f'DROP SCHEMA IF EXISTS "{schema}" CASCADE'))
    finally:
        engine.dispose()
    return schemas


def reset_lab_schemas(root: Path | None = None) -> None:
    """Backward-compatible all-layer reset for WH-M01."""

    reset_lab_layers("schemas", root)


def drop_lab_database(confirmation: str, root: Path | None = None) -> None:
    """Drop only week3_medallion_lab after exact-name confirmation."""

    if confirmation != LAB_DATABASE:
        raise ValueError(
            f"Destructive reset requires --confirm {LAB_DATABASE}; no database was removed."
        )

    config = load_postgres_config(root)
    engine = make_engine(config.maintenance_database, root)
    try:
        with engine.connect().execution_options(isolation_level="AUTOCOMMIT") as connection:
            connection.execute(
                text(
                    "SELECT pg_terminate_backend(pid) FROM pg_stat_activity "
                    "WHERE datname = :database_name AND pid <> pg_backend_pid()"
                ),
                {"database_name": LAB_DATABASE},
            )
            connection.execute(text(f'DROP DATABASE IF EXISTS "{LAB_DATABASE}"'))
    finally:
        engine.dispose()
