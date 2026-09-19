#!/usr/bin/env python3
"""Verify WH-M01 packages and its SQLAlchemy database connection."""

from importlib.metadata import version

from big_data_example.labs.retail_sales.wh_m01_database import (
    POSTGRES_CONTAINER,
    verify_container_health,
    verify_lab_connection,
)


PACKAGES = (
    "ipykernel",
    "matplotlib",
    "pandas",
    "psycopg2-binary",
    "seaborn",
    "SQLAlchemy",
)

print("Required package versions:")
for package in PACKAGES:
    print(f"- {package} {version(package)}")

health = verify_container_health()
print(f"PASS: {POSTGRES_CONTAINER} is {health}.")

evidence = verify_lab_connection()
print(
    "PASS: SQLAlchemy connected without exposing the password: "
    f"database={evidence['database_name']}, "
    f"user={evidence['database_user']}, "
    f"PostgreSQL={evidence['server_version']}"
)
