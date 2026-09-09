"""Bootstrap verification for the repository's Python package."""

import sys
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SOURCE_ROOT = PROJECT_ROOT / "src"
sys.path.insert(0, str(SOURCE_ROOT))

import big_data_example  # noqa: E402


class PackageTest(unittest.TestCase):
    def test_package_exposes_a_version(self) -> None:
        self.assertEqual("0.1.0", big_data_example.__version__)


if __name__ == "__main__":
    unittest.main()

