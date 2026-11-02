# U.S. Jobs and SNAP project agent guide

## Learning and ownership

- The user is learning Azure through this project. Teach the work in small, explainable checkpoints and check understanding before introducing several new concepts.
- Provide runnable CLI commands, Terraform guidance, or Azure console steps with what each action does, why it is needed, expected observations, and how to verify success. Label illustrative output separately from actual results.
- Let the user execute implementation and deployment steps. Do not create cloud resources, deploy infrastructure, run ingestion/ETL, or complete the pipeline for the user unless they explicitly request that action. Requests for architecture, explanations, or walkthroughs authorize guidance, not cloud execution.
- Requested documentation edits and read-only source research can proceed. Preserve the user's notes, questions, attempts, and TODOs. Do not silently replace unfinished exercises with solutions.
- Both Terraform and Data Factory visual authoring are acceptable learning paths. Explain their roles and tradeoffs when choosing a step; the implementation path is not yet selected. Do not maintain two competing resource configurations without a reason.

## Documentation contract

- Read the relevant project guide before changing its design. Keep README, architecture, data model, and source schemas aligned.
- Document each implementation checkpoint in `steps.md`: purpose, prerequisites, CLI/console/Terraform instructions, expected result, verification, observed evidence, and remaining work. Add the concrete instructions when the learner reaches the checkpoint, rather than pre-completing the entire project.
- Mark a step complete only from observed execution or user-supplied evidence; documentation and static checks do not prove Azure runtime success. Never store secrets in examples or evidence.
- Follow the root agent guide, including numbered conversational points and Markdown prose without hard wrapping. Update the actual coverage registry at `docs/AI-Generated-Training/COVERAGE.md` when scope or evidence changes.

## Accepted scope and model

- Historical baseline: January 2015–December 2025, followed by initial catch-up to each source's latest available month.
- After initial loading, process only the six reporting months ending at each source's latest available month. No automatic annual historical reconciliation, older correction replay, or expanded gap backfill. Report older gaps without silently widening the window.
- Monthly Data Factory schedule on the first day; exact time/time zone is a documented configurable default until selected during setup.
- Two facts: `fact_state_month` and `fact_state_industry_month`, with shared `dim_state` and monthly `dim_date`; the industry fact also uses `dim_industry`.
- `dim_date` has exactly `date_key`, `year`, `quarter`, `month_number`, and `month_name`, with one row per calendar month. Do not add daily rows.
- Preserve immutable Bronze snapshots by source, explicit ingestion date, run ID, and attempt ID. Retain revision metadata and old/new values without duplicating current facts.
- Process valid available records and retain legitimate partial measurements with NULLs/source-level status. Default Gold reporting views and visuals show complete comparable records/months only. Define completeness by the report's required state/industry scope, and do not disguise technical failures as missing publication data.
- Data Factory orchestrates bounded Azure Function ingestion and Databricks processing. Terraform or console authoring does not change those service responsibilities.
- Keep national-data inspection evidence separate from still-pending state/industry coverage verification. State/industry membership and source definitions must be checked before implementation claims.
