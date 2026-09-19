#!/usr/bin/env python3
"""Generate or restore the deterministic WH-M01 source delivery."""

from argparse import ArgumentParser

from big_data_example.labs.retail_sales.wh_m01_source import (
    EXPECTED_ROW_COUNT,
    write_source_delivery,
)


parser = ArgumentParser(description=__doc__)
parser.add_argument(
    "--force",
    action="store_true",
    help="Restore both source files to their deterministic contents.",
)
args = parser.parse_args()

csv_path, manifest_path = write_source_delivery(force=args.force)
print(f"PASS: verified deterministic source delivery with {EXPECTED_ROW_COUNT} rows.")
print(f"CSV: {csv_path}")
print(f"Manifest: {manifest_path}")
