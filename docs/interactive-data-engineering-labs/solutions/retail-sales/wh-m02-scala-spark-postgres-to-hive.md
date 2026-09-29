# WH-M02 Solution Explanation: Scala/Spark PostgreSQL-to-Hive Silver Pipeline

> Open this explanation after attempting the notebook checkpoints. The executable learner artifact remains `/Users/richardwilkerson/IdeaProjects/HelloWorld/src/main/scala/WeekendHomework.scala`.

## Part 1 reasoning

The Spark driver runs on the Mac, so it reaches PostgreSQL through the container's published host port. The Hive warehouse path exists inside `hive-server`, so the local Spark process cannot read it as a normal host path. The supplied application therefore uses two explicit Hive paths: Beeline inside the container for metastore operations and `docker cp` for Parquet data movement.

The clean contract begins as `silverOutputSchema`. The application maps that Spark schema to Hive column types, creates the container directory, and issues idempotent external-table DDL. Those operations establish filesystem and catalog structure without adding rows. `--setup-only` returns after both source and target reads, while the surrounding `finally` still removes temporary files and stops Spark.

The important evidence is not just a zero exit code. PostgreSQL, clean Silver, and rejected Silver counts must remain unchanged across setup-only mode.

## Part 2 reasoning

`bronze_row_id` is the stable source identity. Silver carries the same value as `silver_row_id`. The job unions IDs already present in clean and rejected Silver, makes that union distinct, and left-anti joins Bronze against it. That operation protects ordinary reruns because only never-processed IDs reach cleaning.

Within the new candidate batch, duplicate profiling remains separate from replay protection. An order number alone is not a safe business key because one order can contain multiple sale lines. When conflicting rows share a supposedly unique identity, a deterministic survivor rule needs trustworthy ordering evidence; otherwise the conflict should be rejected for investigation.

Cleaning creates parsed columns without immediately destroying raw values. Failed casts and date parsing become null, which feeds an explicit `rejection_reason`. Valid rows are projected into the exact clean contract, while rejected rows retain raw diagnostic values. The reconciliation invariant is:

```text
new candidates = valid rows + rejected rows
```

No ID may appear in both outcomes.

## Runtime evidence

A complete check needs two kinds of evidence:

1. A two-pass test shows that a batch is processed once and that an unchanged rerun does not increase either Hive table.
2. Independent PostgreSQL and Hive queries prove Bronze equals clean plus rejected, each target has unique `silver_row_id` values, and clean/rejected overlap is zero.

## Production limits

The classroom helper writes local Parquet, copies files into a container directory, and then updates or queries Hive metadata. Those steps are not one atomic commit. A crash after a file copy can leave partially visible state, and repeated one-file appends create a small-file problem. A production design would normally use isolated environments plus a transactional table format or another controlled publish protocol with recovery and compaction.

The current lab also shares Week 3 training state, so it deliberately does not provide an automatic destructive reset. A later hardened version should own an isolated fixture, warehouse directory, catalog namespace, and bounded reset command.
