#!/usr/bin/env python3
"""Create the isolated WH-M01 database if it does not already exist."""

from big_data_example.labs.retail_sales.wh_m01_database import (
    LAB_DATABASE,
    create_lab_database,
    verify_lab_connection,
)


created = create_lab_database()
action = "created" if created else "already existed"
evidence = verify_lab_connection()
print(f"PASS: {LAB_DATABASE} {action}.")
print(
    "SQLAlchemy connection: "
    f"database={evidence['database_name']}, "
    f"user={evidence['database_user']}, "
    f"PostgreSQL={evidence['server_version']}"
)
