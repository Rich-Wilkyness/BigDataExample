"""Shared environment and path helpers for interactive notebooks."""

from __future__ import annotations

import os
import sys
from pathlib import Path

from pyspark.sql import SparkSession


PROJECT_ROOT_ENV = "BIG_DATA_EXAMPLE_PROJECT_ROOT"


def project_root() -> Path:
    """Find the source checkout that owns repository fixtures and notebooks."""

    configured_root = os.environ.get(PROJECT_ROOT_ENV)
    if configured_root:
        root = Path(configured_root).expanduser().resolve()
        if _is_project_root(root):
            return root
        raise FileNotFoundError(
            f"{PROJECT_ROOT_ENV} does not identify the BigDataExample checkout: {root}"
        )

    search_starts = (Path.cwd().resolve(), Path(__file__).resolve().parent)
    for start in search_starts:
        for candidate in (start, *start.parents):
            if _is_project_root(candidate):
                return candidate

    raise FileNotFoundError(
        f"Could not find the BigDataExample checkout; set {PROJECT_ROOT_ENV} explicitly"
    )


def _is_project_root(path: Path) -> bool:
    """Identify this repository without relying on the installed package path."""

    return (path / "pyproject.toml").is_file() and (
        path / "src" / "big_data_example"
    ).is_dir()


def project_path(*parts: str) -> Path:
    """Resolve a path from the repository root without depending on notebook cwd."""

    return project_root().joinpath(*parts)


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
