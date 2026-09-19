"""Author-side tests for the deterministic WH-M01 source delivery."""

from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase

from big_data_example.labs.retail_sales.wh_m01_source import (
    EXPECTED_ROW_COUNT,
    GENERATOR_SEED,
    MANIFEST_FILENAME,
    SOURCE_FILENAME,
    build_csv_bytes,
    verify_source_delivery,
    write_source_delivery,
)


class MedallionLabSourceTest(TestCase):
    def test_generator_is_deterministic_and_manifest_is_valid(self) -> None:
        self.assertEqual(build_csv_bytes(), build_csv_bytes())
        with TemporaryDirectory() as temporary_directory:
            delivery_directory = Path(temporary_directory)
            write_source_delivery(delivery_directory)
            manifest = verify_source_delivery(delivery_directory)

        self.assertEqual(manifest["generator_seed"], GENERATOR_SEED)
        self.assertEqual(manifest["row_count"], EXPECTED_ROW_COUNT)
        self.assertEqual(len(manifest["sha256"]), 64)

    def test_modified_source_is_detected_and_force_restores_it(self) -> None:
        with TemporaryDirectory() as temporary_directory:
            delivery_directory = Path(temporary_directory)
            csv_path, manifest_path = write_source_delivery(delivery_directory)
            csv_path.write_bytes(csv_path.read_bytes() + b"changed\n")

            with self.assertRaisesRegex(ValueError, "differs"):
                verify_source_delivery(delivery_directory)
            with self.assertRaisesRegex(ValueError, "differs"):
                write_source_delivery(delivery_directory)

            write_source_delivery(delivery_directory, force=True)
            verify_source_delivery(delivery_directory)
            self.assertTrue((delivery_directory / SOURCE_FILENAME).is_file())
            self.assertTrue((delivery_directory / MANIFEST_FILENAME).is_file())


if __name__ == "__main__":
    from unittest import main

    main()
