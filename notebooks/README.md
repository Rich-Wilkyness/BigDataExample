# Notebooks

Notebooks are for exploration, visualization, and guided experiments. Reusable
pipeline logic must move into `src/big_data_example`, and durable transformations
should be versioned under `sql/` when SQL is the appropriate owner.

Committed notebooks must have bounded output, deterministic inputs, no secrets,
and a documented way to reproduce their environment.

