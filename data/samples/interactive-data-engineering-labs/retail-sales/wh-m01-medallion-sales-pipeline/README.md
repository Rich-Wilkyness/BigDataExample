# WH-M01 Generated Source Data

Stage 1 uses the deterministic generator in `src/big_data_example/labs/retail_sales/wh_m01_source.py`. The tracked `source/batch-001/` delivery contains 40 transaction rows in `sales-transactions.csv` and its integrity contract in `manifest.json`.

This lab will not read from `docs/Training/Week2/sample_warehouse/` or from the `week3_hw` database.

## Source integrity contract

The machine-readable manifest records:

- Delivery ID and schema version.
- Fixed generator seed.
- Expected row count.
- CSV SHA-256 checksum.
- Expected intentional data-quality cases.

Bronze adds stable source batch ID, source file name, and source row number values without rewriting the source-oriented transaction fields. The Stage 1 **Check my work** cell verifies the manifest and exact source-to-Bronze preservation.

Filesystem read-only permissions are not the integrity control. They are not portable across every learner environment, Git does not preserve a general read-only bit, and a local process can change them. The checksum detects accidental edits exactly, while the deterministic generator provides a documented way to restore the source delivery.
