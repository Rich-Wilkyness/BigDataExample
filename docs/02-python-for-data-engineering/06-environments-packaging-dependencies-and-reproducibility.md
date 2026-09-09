# Environments, Packaging, Dependencies, and Reproducibility

> Status: Documentation complete  
> Level: Intermediate  
> Applies to: Python packaging / Local and delivered jobs  
> Data scale: Package and environment metadata  
> Example status: Existing package inspected; reproducible delivery exercise planned  
> Evidence status: Package smoke test recorded elsewhere; build/lock/supply-chain evidence pending  
> Last reviewed: 2026-09

## Overview

A Python job is the combination of source, interpreter implementation/version,
resolved dependencies and native artifacts, configuration, data/schema versions,
and entry point. A virtual environment isolates installed packages; it does not by
itself record or reproduce that combination. Packaging makes code installable.
Resolution and lock mechanisms select versions. Delivery evidence proves the
artifact actually runs in a clean target-like environment.

This guide explains the contracts without selecting a new package manager,
lock-tool, container platform, or registry for the repository.

## Learning objectives

- Distinguish interpreter, environment, project metadata, distribution, install,
  resolution, and lock state.
- Explain why “works in my virtual environment” is weak evidence.
- Design runtime/development dependency and configuration boundaries.
- Record provenance and verify a clean, offline-capable or controlled build path.
- Evolve dependencies and Python versions with rollout and rollback plans.

## Prerequisites

Complete guides 01–05. Read the root `pyproject.toml`: the current project requires
Python 3.12+, uses setuptools, a `src` layout, and declares no runtime dependencies.

## Mental model

```text
source + pyproject + chosen lock/resolution + interpreter/platform
                         |
                     build/install
                         |
            immutable artifact/environment
                         |
       entry point + external configuration + data versions
                         |
                 observed job result
```

This resembles Gradle inputs, dependency resolution, variants, and APK/AAB
artifacts. The analogy stops because Python environments often resolve/install at
deployment time, native wheels vary by interpreter/platform tags, and no single
lock workflow is inherent in `pyproject.toml`.

## Terminology

| Term | Meaning |
| --- | --- |
| Interpreter | Python implementation, version, build mode, and platform runtime |
| Virtual environment | Isolated installation prefix associated with an interpreter |
| Source distribution | Archive used to build a project on the target/build system |
| Wheel | Built distribution tagged for compatible Python/ABI/platform combinations |
| Resolver | Tool choosing a dependency graph satisfying constraints |
| Lock state | Tool/standard-specific exact resolution and integrity metadata |
| Provenance | Evidence connecting reviewed source to built and deployed artifact |

## Current contract and invariants

The repository's authoritative project metadata is root `pyproject.toml`. The
package imports as `big_data_example` from `src/`. Runtime compatibility is
declared as `>=3.12`; that broad range is a claim requiring a test matrix if it is
kept. No third-party runtime dependencies are currently required.

Invariants for future jobs:

- A run records interpreter implementation/version, artifact version/digest,
  configuration version, schema/rule version, and dependency resolution identity.
- Runtime dependencies are declared directly and do not depend on accidental
  globally installed packages.
- Credentials and environment-specific endpoints are external configuration, not
  committed source or baked test fixtures.
- Builds use authenticated, controlled indexes and verify artifact integrity.
- Rollback restores code and compatible configuration without making new data unreadable.

## Environment and packaging behavior

`python -m venv` creates isolation from the base installation in ordinary use,
but environments are not generally portable directories. Recreate them from
declared inputs. Always invoke tools through the intended interpreter, such as
`python -m unittest`, to reduce executable/path ambiguity.

`[build-system]` declares build requirements and backend. `[project]` declares
core metadata and direct dependencies. Version ranges express compatibility, not
an exact deployment. Transitive versions and platform-specific artifacts can
change while the project file stays unchanged. A selected lock workflow should
capture exact packages, markers, artifact hashes, supported platforms, and source
indexes as appropriate; the emerging `pylock.toml` standard is not silently
adopted here because repository tooling has not been selected.

### Dependency boundaries

Keep the runtime set small and separate test/build/developer tooling. A library
should declare the broadest versions it actually supports; a deployed application
usually needs a reviewed exact resolution. Optional dependencies must not become
undeclared imports on core paths. Importing the package should not read secrets,
connect to services, migrate schemas, or configure global logging.

Native extensions can improve performance but add ABI, platform, vulnerability,
and build-toolchain constraints. Verify wheels for every target or control the
source build environment. Never assume a Linux artifact represents Windows or a
different CPU architecture.

## Ownership and trust boundaries

| Boundary | Owner | Risk/required evidence |
| --- | --- | --- |
| Project metadata | Repository maintainers | Review direct deps, Python range, build backend |
| Package index/artifacts | Supply-chain and platform owners | Authenticity, integrity, availability, allowlist |
| Resolver/lock | Build owner | Deterministic reviewed graph for target platforms |
| Built artifact/image | Delivery owner | Provenance, scan, clean install, immutable digest |
| Runtime config/secrets | Platform/operator | Least privilege, rotation, redaction, versioned non-secret config |
| Job data/output | Data-product owner | Code/config/schema lineage and compatible rollback |

The package artifact is authoritative for code bytes, not for runtime configuration
or dataset semantics. A lock file records selected packages; it does not prove
they are safe, correct, or compatible with representative workloads.

## Failure model and recovery

| Failure | Detection | Containment/recovery |
| --- | --- | --- |
| Wrong interpreter selected | Startup metadata/version guard | Fail before processing; fix launcher/environment |
| Undeclared dependency works locally | Clean-environment import/test | Declare or remove; rebuild artifact |
| Resolution changes unexpectedly | Lock/digest diff | Review graph; restore known artifact/lock |
| No compatible native wheel | Target build/install test | Build in controlled target or change dependency |
| Index/package compromise | Signature/hash/scan/advisory process | Block artifact, rotate credentials, rebuild from trusted inputs |
| Secret logged or baked in artifact | Scan/audit | Revoke, remove, rebuild, assess exposed data |
| New code writes unreadable state | Mixed-version/rollback test | Hold rollout; dual-read/expand contract or forward repair |

Do not repair an environment interactively in production and then lose the diff.
Replace it with a reviewed immutable artifact and preserve incident evidence.

## Testing, delivery evidence, and operations

| Evidence | Environment/procedure | Expected result | Result |
| --- | --- | --- | --- |
| Package smoke test | Existing local Python 3.12.3 test run | Import succeeds | Previously locally verified in coverage |
| Clean build/install | Fresh isolated environment | Wheel builds, installs, imports without repo path | Pending |
| Python/platform matrix | Declared supported targets | Tests pass on every claimed target | Pending |
| Resolution replay | Selected lock workflow | Same reviewed artifacts/digests | Pending; tool not selected |
| Supply-chain review | Dependency graph/artifacts | Known ownership, license, advisories, integrity | Pending |
| Rollout/rollback | Target-like job and old/new data | Mixed versions safe and rollback readable | Pending |

At startup emit safe artifact, interpreter, configuration, and schema identifiers.
Measure startup/import time, environment size, resolution/build duration, failure
rate, and artifact age. Do not put secrets in command lines, logs, trace attributes,
package metadata, or metric labels.

## Debugging guide and pitfalls

Capture the exact executable path, `sys.version`, platform/architecture, package
artifact digest, resolved distributions, entry point, and non-secret configuration
version. Reproduce from an empty environment, not by modifying the broken one.
Compare resolution and artifact hashes before debugging application logic.

Pitfalls include treating a virtual environment as a lock, relying on `PATH`,
using broad untested Python/dependency ranges, installing transitive packages
directly without declaration, importing from the working tree accidentally,
allowing build isolation to download unreviewed inputs, and embedding secrets.

## Compatibility and tradeoffs

Exact locks improve deployment repeatability but require deliberate updates and
multi-platform representation. Broad library constraints help downstream
composition but expand the compatibility matrix. Containers capture OS-level
inputs but do not remove the need for Python metadata, provenance, scanning, or
data-schema compatibility. Prefer the smallest workflow satisfying the actual
delivery contract, then test it from clean inputs.

## Working example

- Existing source: Root `pyproject.toml` and `src/big_data_example`
- Try it: Existing package test command documented in repository coverage
- Evidence: Local Python 3.12.3 package smoke test only
- Planned: Clean wheel build/install, target matrix, selected lock workflow, and provenance
- Remaining risk: Reproducibility, supply chain, target platform, rollout, and rollback

## Knowledge check

1. Explain why recreating a venv from unconstrained ranges may change behavior.
2. Identify which facts belong to project metadata, lock state, artifact, and runtime config.
3. Design a clean-environment test that cannot import accidentally from the repo root.
4. Plan a dependency upgrade with compatibility, canary, data, and rollback checks.
5. Decide when a native extension is justified and list new evidence it requires.

## Key takeaways

- A virtual environment isolates installations; it is not a reproducibility proof.
- Project metadata, exact resolution, artifact, interpreter, and config are distinct inputs.
- Clean builds and target-like runs expose undeclared and platform-specific assumptions.
- Dependency security includes provenance, integrity, access, review, and response.
- Code rollback must remain compatible with data written during rollout.

## Resources

- [Python Packaging User Guide: `pyproject.toml`](https://packaging.python.org/en/latest/specifications/pyproject-toml/)
- [Python Packaging User Guide: reproducible environments](https://packaging.python.org/en/latest/specifications/section-reproducible-environments/)
- [Python 3.12 virtual environments](https://docs.python.org/3.12/library/venv.html)
- [Python packaging binary distribution format](https://packaging.python.org/en/latest/specifications/binary-distribution-format/)

## Related topics

- [Area README](README.md)
- [Functions, classes, dataclasses, protocols, and modules](03-functions-classes-dataclasses-protocols-and-modules.md)
- [Testing, profiling, memory, and Python performance](08-testing-profiling-memory-and-python-performance.md)

## Completion checklist

- [x] Environment, packaging, lock, platform, ownership, and supply-chain model covered
- [x] Current repository contract and evidence limitations recorded
- [ ] Build/installation and compatibility matrix executed
- [ ] Lock, provenance, scan, rollout, and rollback workflow selected and verified

