# Local verification record

[Demo index](README.md) · [Requirements and API keys](local-requirements.md)

Verified on October 31, 2026 local time / November 1 UTC, using Python 3.14.5 on Apple-silicon macOS. Primary package versions are recorded in [requirements-local.txt](requirements-local.txt). Dependencies were installed in an isolated temporary environment, leaving the repository's existing environment unchanged. This records work actually executed, not an assertion that every end-to-end service combination has passed.

## Data verified

The connected AWS tool successfully performed read-only STS identity and scoped S3 listings in the existing account. Two existing raw snapshot objects were downloaded, and the conversion script ran locally. Information/status snapshots each contain 2,519 unique station IDs; the local one-to-one join retains all 2,519. Filtering for positive capacity and known coordinates leaves 2,483 station-model examples. The CSVs and payload/provenance files remain under Git-ignored `data/raw/week8-friday-citibike/`; no S3 object, cloud compute, database, IAM policy, or schedule was modified.

## Executed script checks

| Demo or workflow | Actual result | Boundary |
| --- | --- | --- |
| 01 Clustering | Exit 0; five groups with counts 524, 496, 560, 410, 529 | Actual local export; cluster IDs are arbitrary |
| 02 Saved status join | Exit 0; 2,519 information rows, 2,519 status rows, 2,519 matched IDs | Local saved snapshot mode; optional live feed not exercised |
| 03 Capacity regression | Exit 0; MAE approximately 6.32 docks, R² approximately 0.637; PNG generated | Actual export and current packages, not the teacher's earlier dataset/result |
| 04 Station classification | Exit 0; accuracy approximately 64.99%; report and PNG generated | Rank-derived teaching categories, not official station labels |
| 05 MLflow capacity model | Exit 0; trained, logged, registered numbered version; MAE/R² agree with 03 | Temporary local SQLite tracking store and artifacts; generic CLI HTTP server not started |
| 06 Synthetic time series | Exit 0; linear MAE approximately 2.84/R² 0.008; forest MAE approximately 1.99/R² 0.494; PNG generated | Known synthetic generator, chronological future period |
| 07 Candidate and final evaluation | Two candidate CLI runs, distinct registered versions, one final-test CLI run succeeded | Transparent test fixtures and a local SQLite MLflow store; not a real Kafka-collected dataset or fraud-quality benchmark |
| 08 Selection/model handler | Explicit selection CLI wrote a temporary pinned manifest; actual registered classifier loaded; POST handler returned a prediction and matching `/metadata` identity | Flask test client, not a bound TCP server or live Kafka inference loop |
| 09 Flask dashboard | Twelve offline tests passed | Real SQLite/Flask and real SDK with mocked provider transport; no paid response or trace export |
| Shared data/learning workflow | Ten offline tests passed | CSV/Parquet IDs, duplicate-key detection, snapshots, fixed papers, replay conflicts, commit order, model identity, label leakage, and source-run-bound promotion |

Plot scripts used a noninteractive Agg backend and saved outputs into temporary working directories. Their interactive windows and dashboard browser appearance were not inspected in this pass. Joblib emitted a local CPU-detection warning during clustering; the script completed successfully. The optional direct Boto3 S3-download branch was not executed; this workspace used the connected AWS downloader followed by local conversion.

The candidate smoke-test fixtures deliberately encode easily learned synthetic structure. Their scores establish that the fitting/logging/evaluation mechanics work, not generalization to real-world fraud. No smoke-test model is deployed into the user's lesson state.

## Re-run offline checks

From `friday-ml-demos`, after installing `requirements-local.txt`:

```bash
python test-learning-workflow.py
cd 09-flask-genai
python -m unittest -v test_demo
```

Both suites passed: **22 tests total**. Python parsing, Markdown link targets/fences, shell-block syntax, and dashboard JavaScript syntax also passed. Homework, the two original chat files, and all six original screenshots were checked against their saved hashes and are unchanged.

## Remaining runtime checkpoints

- Start the documented Kafka 4.4.0 broker with its intended persistent local state and exercise real producer/collector commits.
- Collect a real local Kafka training cohort, compare candidates, final-test the chosen version, and serve that artifact through the documented startup command.
- Exercise the complete Kafka → model HTTP API → prediction topic → Flask/monitor path, including a restart/replay.
- Request an actual OpenAI explanation using the user's API key and selected model, then inspect actual exported MLflow traces.

These pending checks can be performed while you walk through the guides. Every component is local except optional data refresh/live-feed access and the OpenAI provider call. They are not reasons to require a cloud deployment or a SQL database.
