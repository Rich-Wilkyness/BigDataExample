#!/usr/bin/env python3
"""Create and idempotently load the WH-M01 Bronze layer."""

from big_data_example.labs.retail_sales.wh_m01_bronze import (
    check_stage1,
    create_bronze_schema,
    load_bronze,
)


create_bronze_schema()
loaded_rows = load_bronze()
evidence = check_stage1()
print(f"PASS: loaded {loaded_rows} rows into Bronze.")
print(evidence)
