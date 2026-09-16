"""Tests for repository path resolution used by labs and notebooks."""

import unittest
from pathlib import Path

from big_data_example.notebook_support import project_path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


class NotebookSupportTest(unittest.TestCase):
    def test_project_path_resolves_from_the_source_checkout(self) -> None:
        self.assertEqual(
            PROJECT_ROOT / "pyproject.toml",
            project_path("pyproject.toml"),
        )


if __name__ == "__main__":
    unittest.main()
