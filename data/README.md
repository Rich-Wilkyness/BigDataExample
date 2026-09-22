# Data workspace

This directory will hold local inputs, staged outputs, curated outputs, and
checkpoint state created by exercises. Those generated directories are ignored
by Git.

Only small, redistributable, deterministic fixtures should be committed. Every
fixture must document its origin, license, schema, generation procedure, and any
privacy constraints. Production data, credentials, personal data, and opaque
downloads do not belong in this repository.

## Interactive lab fixtures

- [`OP-C01` sales delivery](samples/interactive-data-engineering-labs/platform-operations/op-c01-containerized-pipeline-runtime/README.md) provides the immutable eight-row input for the containerized pipeline runtime lab.
