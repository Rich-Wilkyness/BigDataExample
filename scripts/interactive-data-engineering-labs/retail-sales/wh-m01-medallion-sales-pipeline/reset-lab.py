#!/usr/bin/env python3
"""Reset only the database objects owned by WH-M01."""

from argparse import ArgumentParser

from big_data_example.labs.retail_sales.wh_m01_database import (
    LAB_DATABASE,
    drop_lab_database,
    reset_lab_layers,
)


parser = ArgumentParser(description=__doc__)
parser.add_argument(
    "mode",
    choices=("gold", "silver", "schemas", "database"),
    help=(
        "Drop Gold only; Silver and downstream Gold; all three lab schemas; "
        "or the entire lab database."
    ),
)
parser.add_argument(
    "--confirm",
    default="",
    help=f"Required for database mode; must equal {LAB_DATABASE}.",
)
args = parser.parse_args()

if args.mode != "database":
    dropped_schemas = reset_lab_layers(args.mode)
    dropped_names = ", ".join(dropped_schemas)
    print(f"PASS: dropped only {dropped_names} inside {LAB_DATABASE}.")
    if args.mode == "gold":
        print("Preserved: source delivery, bronze, and silver. Rerun Stage 3.")
    elif args.mode == "silver":
        print("Preserved: source delivery and bronze. Rerun Stages 2 and 3.")
    else:
        print("Preserved: source delivery. Rerun Stages 1, 2, and 3.")
else:
    if args.confirm != LAB_DATABASE:
        parser.error(
            f"database mode requires --confirm {LAB_DATABASE}; no database was removed"
        )
    drop_lab_database(args.confirm)
    print(f"PASS: removed only the {LAB_DATABASE} database.")
