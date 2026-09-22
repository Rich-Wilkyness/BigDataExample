#!/usr/bin/env python3
"""Learner-facing checks for OP-C01 without exposing a completed solution."""

from __future__ import annotations

import argparse
import csv
import os
from collections import defaultdict
from decimal import Decimal
from pathlib import Path
import subprocess
import sys


LAB_RELATIVE_PATH = Path(
    "infra/interactive-data-engineering-labs/platform-operations/"
    "op-c01-containerized-pipeline-runtime"
)
SOURCE_RELATIVE_PATH = Path(
    "data/samples/interactive-data-engineering-labs/platform-operations/"
    "op-c01-containerized-pipeline-runtime/sales.csv"
)
LEARNER_FILES = ("Dockerfile", "docker-compose.yml", "run_pipeline.sh")


def find_repository_root() -> Path:
    current = Path(__file__).resolve()
    return next(
        candidate
        for candidate in current.parents
        if (candidate / "pyproject.toml").is_file() and (candidate / "AGENTS.md").is_file()
    )


def run(command: list[str], *, cwd: Path, environment: dict[str, str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        cwd=cwd,
        env=environment,
        text=True,
        capture_output=True,
        check=False,
    )


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def read_env_file(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        key, value = stripped.split("=", maxsplit=1)
        values[key] = value
    return values


def static_check(repository_root: Path) -> tuple[Path, Path, dict[str, str]]:
    lab_directory = repository_root / LAB_RELATIVE_PATH
    source_csv = repository_root / SOURCE_RELATIVE_PATH
    environment = os.environ.copy()
    environment["SALES_CSV_PATH"] = str(source_csv)

    require(source_csv.is_file(), f"Missing immutable input fixture: {source_csv}")
    for filename in LEARNER_FILES:
        path = lab_directory / filename
        require(path.is_file(), f"Missing learner file: {path}")
        require("__" not in path.read_text(encoding="utf-8"), f"Finish every placeholder in {filename}")

    run_script = lab_directory / "run_pipeline.sh"
    require(os.access(run_script, os.X_OK), "run_pipeline.sh must be executable")

    shell_result = run(["bash", "-n", str(run_script)], cwd=lab_directory, environment=environment)
    require(shell_result.returncode == 0, shell_result.stderr.strip() or "run_pipeline.sh has invalid Bash syntax")

    dockerfile = (lab_directory / "Dockerfile").read_text(encoding="utf-8")
    for required_text in ("FROM python:", "WORKDIR /app", "pip install", 'CMD ["python", "pipeline.py"]'):
        require(required_text in dockerfile, f"Dockerfile is missing: {required_text}")

    compose_result = run(
        [
            "docker",
            "compose",
            "--env-file",
            ".env.example",
            "-f",
            "docker-compose.yml",
            "config",
            "--quiet",
        ],
        cwd=lab_directory,
        environment=environment,
    )
    require(
        compose_result.returncode == 0,
        compose_result.stderr.strip() or "Docker Compose configuration is invalid",
    )

    compose_text = (lab_directory / "docker-compose.yml").read_text(encoding="utf-8")
    for required_text in (
        "postgres:18",
        "condition: service_healthy",
        "postgres:5432",
        "postgres-data:/var/lib/postgresql",
        "${SALES_CSV_PATH}",
        "./output",
    ):
        require(required_text in compose_text, f"docker-compose.yml is missing: {required_text}")

    script_text = run_script.read_text(encoding="utf-8")
    for required_text in (
        "set -euo pipefail",
        "export SALES_CSV_PATH",
        "docker compose up --detach --wait postgres",
        "docker compose run --rm --build pipeline",
    ):
        require(required_text in script_text, f"run_pipeline.sh is missing: {required_text}")

    return lab_directory, source_csv, environment


def expected_report(source_csv: Path) -> list[dict[str, str]]:
    totals: dict[str, tuple[int, Decimal]] = defaultdict(lambda: (0, Decimal("0.00")))
    with source_csv.open(newline="", encoding="utf-8") as source_file:
        for row in csv.DictReader(source_file):
            category = row["category"].strip().title()
            quantity = int(row["quantity"])
            revenue = Decimal(row["unit_price"]) * quantity
            current_units, current_revenue = totals[category]
            totals[category] = (current_units + quantity, current_revenue + revenue)

    ordered = sorted(totals.items(), key=lambda item: (-item[1][1], item[0]))
    return [
        {
            "category": category,
            "total_units": str(units),
            "total_revenue": f"{revenue:.2f}",
        }
        for category, (units, revenue) in ordered
    ]


def runtime_check(repository_root: Path) -> None:
    lab_directory, source_csv, environment = static_check(repository_root)
    env_path = lab_directory / ".env"
    require(env_path.is_file(), "Run ./run_pipeline.sh first so the local .env file exists")
    env_values = read_env_file(env_path)

    compose_prefix = [
        "docker",
        "compose",
        "--env-file",
        str(env_path),
        "-f",
        "docker-compose.yml",
    ]
    container_result = run(
        [*compose_prefix, "ps", "-q", "postgres"],
        cwd=lab_directory,
        environment=environment,
    )
    container_id = container_result.stdout.strip()
    require(container_result.returncode == 0 and container_id, "The OP-C01 PostgreSQL container is not running")

    health_result = run(
        ["docker", "inspect", "--format", "{{.State.Health.Status}}", container_id],
        cwd=lab_directory,
        environment=environment,
    )
    require(health_result.stdout.strip() == "healthy", "The OP-C01 PostgreSQL container is not healthy")

    row_count_result = run(
        [
            *compose_prefix,
            "exec",
            "-T",
            "postgres",
            "psql",
            "-U",
            env_values["POSTGRES_USER"],
            "-d",
            env_values["POSTGRES_DB"],
            "-tAc",
            "SELECT COUNT(*) FROM reporting.sales_transactions",
        ],
        cwd=lab_directory,
        environment=environment,
    )
    require(row_count_result.returncode == 0, row_count_result.stderr.strip())
    require(row_count_result.stdout.strip() == "8", "Expected 8 PostgreSQL rows")

    report_path = lab_directory / "output" / "sales_report.csv"
    require(report_path.is_file(), f"Missing generated report: {report_path}")
    with report_path.open(newline="", encoding="utf-8") as report_file:
        actual_report = list(csv.DictReader(report_file))
    require(actual_report == expected_report(source_csv), "sales_report.csv does not match the source totals")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=("static", "runtime"), default="static")
    arguments = parser.parse_args()
    repository_root = find_repository_root()

    try:
        if arguments.mode == "static":
            static_check(repository_root)
            print("PASS: OP-C01 setup files satisfy the static contract")
        else:
            runtime_check(repository_root)
            print("PASS: OP-C01 runtime, PostgreSQL rows, and report are correct")
    except (AssertionError, FileNotFoundError, KeyError, ValueError) as error:
        print(f"FAIL: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
