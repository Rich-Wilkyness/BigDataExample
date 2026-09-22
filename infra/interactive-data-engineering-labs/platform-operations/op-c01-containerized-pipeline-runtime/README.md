# OP-C01 learner workspace

This directory contains the learner-owned runtime files for the `OP-C01 Containerized Pipeline Runtime` notebook. Start from the notebook rather than trying to run these starter files immediately.

## File responsibilities

| File | Responsibility | Learner edits? |
| --- | --- | --- |
| `.env.example` | Local PostgreSQL configuration copied to ignored `.env` | No |
| `.dockerignore` | Files excluded from the pipeline image build context | No |
| `requirements.txt` | Python packages installed in the image | No |
| `pipeline.py` | Supplied CSV → PostgreSQL → report implementation | No |
| `Dockerfile` | Recipe for the reusable pipeline image | Yes |
| `docker-compose.yml` | Runtime wiring for PostgreSQL and the pipeline | Yes |
| `run_pipeline.sh` | One-command host entry point | Yes |
| `reset_lab.sh` | Bounded removal of this lab's generated state | No |

The input CSV remains under `data/samples/`; it is mounted read-only at runtime. The generated report appears under this directory's ignored `output/` folder. PostgreSQL data lives in a Docker named volume, not in `output/`.
