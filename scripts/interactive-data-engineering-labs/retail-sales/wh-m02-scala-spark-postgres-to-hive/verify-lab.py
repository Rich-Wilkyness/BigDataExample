#!/usr/bin/env python3
"""Learner-facing checks for WH-M02 without supplying transformation code."""

from __future__ import annotations

import argparse
import os
from pathlib import Path
import re
import subprocess
import sys


DEFAULT_SCALA_PROJECT = Path("/Users/richardwilkerson/IdeaProjects/HelloWorld")
SCALA_SOURCE_RELATIVE = Path("src/main/scala/WeekendHomework.scala")
EXPECTED_CLEAN_SCHEMA = (
    ("silver_row_id", "bigint"),
    ("order_number", "int"),
    ("order_date", "date"),
    ("customer_company", "string"),
    ("product_name", "string"),
    ("product_category", "string"),
    ("unit_price", "decimal(12,2)"),
    ("quantity", "int"),
    ("sales_amount", "decimal(14,2)"),
)


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def run(command: list[str], *, cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        cwd=cwd,
        text=True,
        capture_output=True,
        check=False,
    )


def scala_project() -> Path:
    configured = os.environ.get("HELLO_WORLD_PROJECT")
    return Path(configured).expanduser().resolve() if configured else DEFAULT_SCALA_PROJECT


def load_source() -> tuple[Path, str]:
    project = scala_project()
    source_path = project / SCALA_SOURCE_RELATIVE
    require(project.is_dir(), f"Scala project does not exist: {project}")
    require(source_path.is_file(), f"Missing learner source: {source_path}")
    require((project / "build.sbt").is_file(), f"Missing build.sbt in {project}")
    require((project / ".env").is_file(), f"Missing project-local .env in {project}")
    return source_path, source_path.read_text(encoding="utf-8")


def check_infrastructure() -> None:
    for container in ("big-data-example-postgres", "hive-server"):
        result = run(["docker", "inspect", "--format", "{{.State.Running}}", container])
        require(result.returncode == 0, result.stderr.strip() or f"Cannot inspect {container}")
        require(result.stdout.strip() == "true", f"Container is not running: {container}")

    bronze_count = postgres_integer("SELECT COUNT(*) FROM bronze.sales_raw")
    require(bronze_count > 0, "bronze.sales_raw is empty")

    databases = hive_output("SHOW DATABASES;").splitlines()
    require("default" in databases, "HiveServer2 did not return its default database")
    tables = hive_output("SHOW TABLES IN silver;").splitlines() if "silver" in databases else []

    if "sales_clean" in tables:
        actual_schema = []
        for line in hive_output("DESCRIBE silver.sales_clean;").splitlines():
            parts = line.split("\t")
            if len(parts) >= 2 and parts[0] and not parts[0].startswith("#"):
                actual_schema.append((parts[0].strip(), parts[1].strip().lower()))
        require(
            tuple(actual_schema[: len(EXPECTED_CLEAN_SCHEMA)]) == EXPECTED_CLEAN_SCHEMA,
            f"silver.sales_clean schema differs from the lab contract: {actual_schema}",
        )
        hive_state = "existing clean Silver schema matches"
    else:
        hive_state = "HiveServer2 is reachable; Part 1 must create clean Silver metadata"

    print(
        f"PASS: infrastructure is reachable; PostgreSQL Bronze has {bronze_count} rows; "
        f"{hive_state}"
    )


def check_part1() -> None:
    source_path, source = load_source()
    required_tokens = (
        "silverOutputSchema",
        "rejectedKeySchema",
        "requiredEnvironmentVariable",
        "spark.read.jdbc",
        '"bronze.sales_raw"',
        "readHiveTable",
        "createExternalTableIfMissing",
        'args.contains("--setup-only")',
    )
    for token in required_tokens:
        require(token in source, f"Part 1 is missing `{token}` in {source_path}")

    require(
        source.count("createExternalTableIfMissing(") >= 3,
        "Call createExternalTableIfMissing from main before reading sales_clean; the helper definition and append helper already account for two occurrences",
    )
    setup_guard = source.index('args.contains("--setup-only")')
    transformation_section = source.index("SECTION 7")
    require(
        setup_guard < transformation_section,
        "Place the --setup-only guard before incremental selection and transformations",
    )

    print("PASS: WH-M02 Part 1 setup contract is present")


def check_part2() -> None:
    source_path, source = load_source()
    required_tokens = (
        'withColumn(\n            "silver_row_id"',
        '"left_anti"',
        "existingProcessedIds",
        "dropDuplicates",
        "to_date",
        'cast("decimal(12,2)")',
        'cast("decimal(14,2)")',
        '"rejection_reason"',
        '"sales_amount"',
        '"sales_clean"',
        '"sales_rejected"',
    )
    for token in required_tokens:
        require(token in source, f"Part 2 is missing `{token}` in {source_path}")

    require(source.count("appendToHiveTable(") >= 3, "Append both valid and rejected DataFrames")
    print("PASS: WH-M02 Part 2 static transformation contract is present")


def postgres_integer(sql: str) -> int:
    result = run(
        [
            "docker",
            "exec",
            "big-data-example-postgres",
            "psql",
            "-X",
            "-U",
            "bigdata",
            "-d",
            "week3_hive_migration",
            "-tAc",
            sql,
        ]
    )
    require(result.returncode == 0, result.stderr.strip() or "PostgreSQL query failed")
    return int(result.stdout.strip())


def hive_output(sql: str) -> str:
    result = run(
        [
            "docker",
            "exec",
            "hive-server",
            "beeline",
            "-u",
            "jdbc:hive2://localhost:10000/default",
            "--silent=true",
            "--showHeader=false",
            "--outputformat=tsv2",
            "-e",
            sql,
        ]
    )
    require(result.returncode == 0, result.stderr.strip() or "Hive query failed")
    return result.stdout.strip()


def hive_integer(sql: str) -> int:
    output = hive_output(sql)
    integer_lines = [line.strip() for line in output.splitlines() if re.fullmatch(r"\s*\d+\s*", line)]
    require(integer_lines, f"Hive query did not return an integer: {output}")
    return int(integer_lines[-1])


def check_runtime() -> None:
    bronze_rows = postgres_integer("SELECT COUNT(*) FROM bronze.sales_raw")
    clean_rows = hive_integer("SELECT COUNT(*) FROM silver.sales_clean;")
    rejected_rows = hive_integer("SELECT COUNT(*) FROM silver.sales_rejected;")
    clean_duplicates = hive_integer(
        "SELECT COUNT(*) FROM (SELECT silver_row_id FROM silver.sales_clean GROUP BY silver_row_id HAVING COUNT(*) > 1) d;"
    )
    rejected_duplicates = hive_integer(
        "SELECT COUNT(*) FROM (SELECT silver_row_id FROM silver.sales_rejected GROUP BY silver_row_id HAVING COUNT(*) > 1) d;"
    )
    overlap = hive_integer(
        "SELECT COUNT(*) FROM silver.sales_clean c JOIN silver.sales_rejected r ON c.silver_row_id = r.silver_row_id;"
    )

    require(clean_duplicates == 0, f"Found {clean_duplicates} duplicated clean IDs")
    require(rejected_duplicates == 0, f"Found {rejected_duplicates} duplicated rejected IDs")
    require(overlap == 0, f"Found {overlap} IDs in both clean and rejected tables")
    require(
        bronze_rows == clean_rows + rejected_rows,
        f"Reconciliation failed: Bronze={bronze_rows}, clean={clean_rows}, rejected={rejected_rows}",
    )

    print(
        "PASS: WH-M02 runtime reconciles "
        f"Bronze={bronze_rows}, clean={clean_rows}, rejected={rejected_rows}; "
        "duplicate and overlap counts are zero"
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--mode",
        choices=("infrastructure", "part1", "part2", "runtime"),
        required=True,
    )
    arguments = parser.parse_args()

    checks = {
        "infrastructure": check_infrastructure,
        "part1": check_part1,
        "part2": check_part2,
        "runtime": check_runtime,
    }

    try:
        checks[arguments.mode]()
    except (AssertionError, FileNotFoundError, OSError, ValueError) as error:
        print(f"FAIL: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
