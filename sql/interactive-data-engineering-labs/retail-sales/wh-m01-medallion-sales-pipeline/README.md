# WH-M01 SQL Artifacts

Stage-specific PostgreSQL DDL, transformations, analytical queries, and validations live here as the learner reaches each stage.

All future SQL in this directory must target only `week3_medallion_lab`. Database creation and bounded reset behavior are owned by the reusable Python helper and commands linked from the notebook.

## Stage 1

- `01-create-bronze.sql` creates `bronze.sales_transactions` with permissive text source fields and stable ingestion lineage.
- The Python loader verifies the tracked source manifest, replaces only `retail-sales-batch-001`, and inserts all 40 source rows without cleaning.
- No Silver or Gold objects are created by Stage 1.
