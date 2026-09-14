# DV-E23: High-Engagement Video Filtering — Solution and Explanation

## Outcome

The lab reads ten synthetic video-metadata rows with an explicit schema and publishes five rows whose `view_count` is strictly greater than 1,000,000 and whose `release_year` is at least 2019. The result has the requested six columns and is ordered by `duration`, then `video_id` as a deterministic tie-break.

Return to the [guided notebook](../../../../notebooks/interactive-data-engineering-labs/content-platform/dv-e23-high-engagement-video-filtering.ipynb), or use the [lab run and reset guide](../../README.md).

## Reference implementation

- [Executable reference transformation](../../../../src/big_data_example/reference_solutions/content_platform/dv_e23_high_engagement_video_filtering.py)
- [Guided notebook](../../../../notebooks/interactive-data-engineering-labs/content-platform/dv-e23-high-engagement-video-filtering.ipynb)
- [Automated tests](../../../../tests/labs/content_platform/test_dv_e23_high_engagement_video_filtering.py)
- [Synthetic source delivery](../../../../data/samples/interactive-data-engineering-labs/content-platform/source/batch-001/videos.csv)
- [Expected rows](../../../../tests/fixtures/interactive-data-engineering-labs/content-platform/dv-e23/expected/high-engagement-videos.csv)

Run the reference solution from the repository root to prove that it satisfies the same checker used by the learner notebook:

```powershell
.\.venv\Scripts\python.exe -m big_data_example.reference_solutions.content_platform.dv_e23_high_engagement_video_filtering
```

## Why it is correct

The input grain is one metadata record per `video_id`. Both predicates must be true, so the implementation combines them with `&` and parenthesizes each Spark `Column` expression. The view boundary is strict: exactly 1,000,000 views does not qualify. The year boundary is inclusive: a qualifying video released in 2019 does qualify. A null in either predicate produces SQL unknown and is excluded by `where`, matching the lab contract.

Projection occurs after filtering and explicitly controls the consumer schema: `duration`, `genre`, `release_year`, `title`, `video_id`, and `view_count`. Ordering by `duration` satisfies the source request; adding `video_id` makes equal-duration results reproducible without changing the primary order.

`view_count` uses Spark `LongType` rather than `IntegerType` because popular-content counts can exceed the signed 32-bit limit. The raw CSV does not preserve types, so the reader supplies a schema rather than depending on inference.

## Walkthrough

`read_video_metadata` treats CSV as an untyped transport and applies `VIDEO_INPUT_SCHEMA`. `build_high_engagement_videos` constructs a lazy logical plan containing a filter, projection, and global ordering operation. Execution begins only when the notebook or tests call actions such as `show`, `count`, or `collect`.

The fixture contains ordinary qualifying rows plus an exact view-threshold row, an old viral row, null popularity, null release year, and an equal-duration pair. These records make the boundary and deterministic-order contracts observable.

## Alternatives and tradeoffs

The same relational operation can be expressed with Spark SQL after registering a temporary view. That can be valuable when comparing plans or working in a SQL-oriented team, but it does not change the underlying filter/projection/sort semantics. A Python UDF would be inappropriate: built-in expressions remain visible to Spark's optimizer and avoid Python serialization for this work.

If ordering is only needed by a dashboard query, omitting `orderBy` from the reusable dataset build and sorting at the consumption boundary can avoid a global shuffle. This exercise retains ordering because it is part of the requested output contract.

## Pitfalls

- Using `>= 1_000_000` incorrectly includes the threshold row.
- Using `release_year > 2019` incorrectly excludes 2019.
- Using Python `and` instead of Spark `&` attempts to evaluate distributed column expressions as local booleans.
- Omitting parentheses around comparisons changes or breaks expression construction because of Python operator precedence.
- Calling `inferSchema` makes correctness depend on the particular fixture values and extra scan behavior.
- Comparing `show()` output by eye does not verify types, null behavior, column order, or boundary conditions.
- Sorting only by `duration` leaves ties unspecified and can make exact row-order tests flaky.

## Distributed and performance behavior

Filtering and projection are narrow transformations and can run independently within input partitions. The final global `orderBy` requires an exchange so Spark can establish total ordering across partitions. `collect()` moves every result row to the driver and is safe only because this fixture is deliberately tiny; a production pipeline would write distributed output or apply a bounded limit before collecting.

## Verification evidence

Run the focused lab test from the repository root:

```powershell
.\.venv\Scripts\python.exe -m unittest tests.labs.content_platform.test_dv_e23_high_engagement_video_filtering
```

Run the complete current suite with:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests
```

Evidence executed on 2026-09-12:

- Focused author suite: 5 tests passed in 22.839 seconds, including acceptance of the reference result and rejection of the untransformed starter result.
- Complete repository suite: 6 tests passed in 22.961 seconds.
- The learner module is intentionally committed with an incomplete starter function, so **Check my work** fails until the learner implements the transformation; the maintained reference implementation supplies the passing author evidence above.
- The documented reference-solution command executed successfully and printed the same five expected rows accepted by the learner checker.
- Earlier reference execution produced five expected rows, and its formatted physical plan contained pushed CSV predicates, projection, range-partitioning exchange, and global sort; this is local plan evidence only.

## Production extension

A production content pipeline would separate immutable ingestion, schema validation and quarantine, deduplication, metric definition versioning, partitioned publication, reconciliation, access control, and orchestration. Those concerns are intentionally excluded here because this Easy technique drill is meant to isolate DataFrame filtering, projection, ordering, schema use, and testable function boundaries.
