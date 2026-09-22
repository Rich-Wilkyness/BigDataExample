# OP-C02 supplied runtime

This directory contains the completed container runtime for `OP-C02 Python Pipeline Setup with SQLAlchemy`. The infrastructure is supplied because the learner already practiced it in OP-C01.

The learner edits only:

```text
src/big_data_example/labs/platform_operations/op_c02_sqlalchemy_pipeline_setup.py
```

The runtime builds that learner module into the pipeline image, mounts the immutable OP-C01 sales fixture, starts an isolated PostgreSQL 18 database on host port `55433`, and writes the report under this directory's ignored `output/` folder.

Start from the OP-C02 notebook. Do not edit the supplied transform or infrastructure files.
