# Interactive Data Engineering Labs

This directory owns source intake, lab design, and solution explanations for derivative, job-shaped data-engineering labs. Executable learner entry points and their setup instructions live in [`notebooks/interactive-data-engineering-labs/`](../../notebooks/interactive-data-engineering-labs/README.md). Final labs are organized by reusable business scenario rather than by source order.

- [`question-dump.md`](question-dump.md) preserves the user-provided raw question intake.
- [`question-catalog.md`](question-catalog.md) assigns stable IDs, identifies contract defects, and groups the 40 retained raw-dump entries plus the existing High-Engagement Video Filtering notebook by proposed scenario and durable transformation skill.
- [`scenario-data-plan.md`](scenario-data-plan.md) proposes reusable source deliveries, entities, layers, fixture ownership, and duplication controls.
- [`coverage.md`](coverage.md) tracks implemented tool, workflow, correctness, and operational depth so the lab sequence grows toward job readiness rather than accumulating disconnected puzzles.
- [`template.md`](template.md) defines difficulty, delivery scope, notebook guidance, artifacts, data contracts, tests, and separate solution explanations.
- [`DV-E23 guided notebook`](../../notebooks/interactive-data-engineering-labs/content-platform/dv-e23-high-engagement-video-filtering.ipynb) is the first complete worked lab.
- [`DV-E23 solution and explanation`](solutions/content-platform/dv-e23-high-engagement-video-filtering.md) documents correctness, alternatives, pitfalls, distributed behavior, and executed evidence.
- [`OP-C01 guided notebook`](../../notebooks/interactive-data-engineering-labs/platform-operations/op-c01-containerized-pipeline-runtime.ipynb) isolates containerized pipeline setup from pandas transformation work.
- [`OP-C01 solution and explanation`](solutions/platform-operations/op-c01-containerized-pipeline-runtime.md) explains image, container, Compose, mount, network, volume, Bash, and SQLAlchemy boundaries.
- [`OP-C02 guided notebook`](../../notebooks/interactive-data-engineering-labs/platform-operations/op-c02-sqlalchemy-pipeline-setup.ipynb) isolates Python and SQLAlchemy pipeline setup from supplied transformation and container work.
- [`OP-C02 solution and explanation`](solutions/platform-operations/op-c02-sqlalchemy-pipeline-setup.md) explains runtime configuration, engine and transaction boundaries, DDL, full-refresh loading, report SQL, and artifact publication.

The permanent track name is `interactive-data-engineering-labs`. DV-E23 is implemented and machine-verified; learner-usability feedback is the remaining template-validation boundary. Open the [learner guide](../../notebooks/interactive-data-engineering-labs/README.md) to run it, or open the [DV-E23 solution](solutions/content-platform/dv-e23-high-engagement-video-filtering.md) after attempting it.
