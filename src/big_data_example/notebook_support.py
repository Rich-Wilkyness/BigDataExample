"""Shared environment and path helpers for interactive notebooks."""

from __future__ import annotations

import os
import sys
from pathlib import Path

from pyspark.sql import SparkSession


PROJECT_ROOT = Path(__file__).resolve().parents[2]


def project_path(*parts: str) -> Path:
    """Resolve a path from the repository root without depending on notebook cwd."""

    return PROJECT_ROOT.joinpath(*parts)


def local_spark(app_name: str, *, threads: int = 2) -> SparkSession:
    """Create or reuse a deterministic local Spark session for a practice lab."""

    if threads < 1:
        raise ValueError("threads must be at least 1")

    os.environ["PYSPARK_PYTHON"] = sys.executable
    os.environ["PYSPARK_DRIVER_PYTHON"] = sys.executable

    return (
        SparkSession.builder.master(f"local[{threads}]")
        .appName(app_name)
        .config("spark.ui.enabled", "false")
        .config("spark.sql.session.timeZone", "UTC")
        .config("spark.sql.shuffle.partitions", str(threads))
        .getOrCreate()
    )
