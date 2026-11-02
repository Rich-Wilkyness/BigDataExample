# Verification record — 2026-10-15

## Environment and command

Working directory: `/Users/richardwilkerson/VSCodeProjects/BigDataExample`. Existing repository `.venv`: Python 3.14.5, Streamlit 1.64.0, pandas 3.0.5, requests 2.34.2, pydeck 0.9.3, boto3/botocore 1.43.108, SQLGlot 30.21.0. No dependency installation was performed. pandas 3 and SQLGlot 30 exceed the instructor requirements' `<3` and `<30` bounds; the adaptation permits them. Results therefore establish checks in this environment, not installation or behavior of the instructor's declared dependency set or every allowed adaptation version.

```bash
.venv/bin/python docs/Training/Week6/4.3-thur-bedrock-streamlit-lab/verify-local.py
```

Result: **11 tests passed**. The verifier sets dummy credentials, disables metadata credential lookup and denies socket connections during tests. It uses SDK Stubber for AWS contracts and Streamlit AppTest with service doubles. No cloud API call, public feed fetch or database statement was sent.

| Check | Result and scope |
| --- | --- |
| `test_snapshots_and_structure` | All 17 snapshot SHA-256 hashes match the recorded manifest. All lab Python parses as AST, all JSON parses, prohibited generated artifact suffixes are absent, and lab Markdown links/fences are checked. |
| `test_shell_syntax` | `bash -n` passes for deployment script, bootstrap template, three selected SSM command bodies and fenced bash examples. Commands are parsed only, never executed. Template placeholders remain literal during parsing; Terraform template evaluation is not established. |
| `test_auth_configuration` | Adapted helper reads dummy explicit workgroup/database values. No credential or grant validity is established. |
| `test_sql_boundary` | SELECT, CTE, UNION and Redshift QUALIFY examples accepted; empty/multiple statements, DELETE, DROP and SELECT INTO rejected. A deliberately nonexistent column/table is accepted, demonstrating that parsing does not enforce schema existence or object access. This is a bounded case set, not an exhaustive security proof. |
| `test_decoder` | Data API synthetic NULL, false, zero, double and string values decode as expected. Blob/unsupported types are not covered or implemented. |
| `test_query_pagination` | Stubber verifies configured warehouse/database, outer LIMIT 200, FINISHED handling, two result pages and NULL decoding. It does not measure real result sizes, truncation under 200+ rows or Redshift SQL semantics. |
| `test_query_failure` | FAILED with a permission error raises and stops result processing. This does not verify any actual permission. |
| `test_timeout_cancellation` | With an immediate synthetic deadline, helper requests cancellation and raises TimeoutError. Cancellation failure, SDK latency and real statement termination remain unverified. |
| `test_bedrock_requests` | Stubber validates generation/repair Converse request shape, token limits, schema/question/error context and code-fence stripping. Explanation request capture checks 50-row sampling from 60 synthetic rows, count metadata and explicit 700 output-token limit; explanation response itself is a mock. No model reasoning, availability, quality or billing is tested. |
| `test_instructor_repair_defect` | AppTest reproduces the original keyed-widget mutation error as the expected baseline outcome. Test pass means the defect was observed, not that the original UI is corrected. |
| `test_richard_approval_repair_results` | Generation makes no query; explicit execution fails under a double; Repair updates editor through rerun without widget error; subsequent explicit execution displays synthetic rows/explanation; changing editor SQL hides prior rows. No browser/server, real backend or live map is exercised. |

Expected environment warnings: AppTest emits a missing ScriptRunContext warning in bare mode; retained instructor-style `use_container_width` emits a Streamlit deprecation notice. They did not fail the checks. The first verifier attempt exposed test-harness issues (native dependency import during temporary module patching, and a disabled Repair button requiring a subsequent rerun); those harness issues were fixed and the full suite rerun successfully.

## Additional source review

All 17 captured files were also compared byte-for-byte with their original files in Downloads at preparation time. Inventory: 10 Python files, 4 JSON files, 5 Markdown files and 4 Terraform source files. All 32 lab-local links and both new coverage links resolved; 9 fenced bash blocks parsed. Coverage `git diff --check` passed. Authored/adapted source whitespace checks passed, excluding the unchanged schema text, whose original tab-separated metadata contains trailing tabs. Deployment assumptions, missing files, stale README instructions and security/lifecycle gaps are recorded in [deployment-review.md](deployment-review.md). Reference originals retain their original formatting; adaptation and authored Markdown are checked for trailing whitespace. Primary AWS/Streamlit API documentation was reviewed, as linked in the [lab guide](README.md).

Attempted `terraform fmt -check docs/Training/Week6/4.3-thur-bedrock-streamlit-lab/reference/instructor`: **not run successfully**, shell exit 127, `command not found: terraform`. No Terraform CLI/provider/template validation, init, plan, apply, import or destroy was performed. The source was inspected manually; no HCL validation pass is claimed. Source copies remain unchanged.

## Pending evidence

- Instructor original dependency installation and broad version compatibility.
- Live GBFS endpoints/field contracts, map rendering/filtering, home-page chart behavior and optional history reads.
- Interactive browser/server launch and deployment host/systemd/SSM behavior.
- Local AWS credential identity, IAM/SCP/boundary permissions, Bedrock model/profile availability, regional routing, quotas and actual inference.
- Database identity, exact grants, DDL/procedure definitions, schema drift, canonical/Gold freshness, uniqueness, join cardinality and completeness.
- Real Data API execution, cancellation/retry behavior, result truncation, SQL correctness and model repair/explanation accuracy.
- EC2 AMI/subnet/network reachability, full artifact publication, atomic release/rollback, authentication/TLS and production access controls.
- Pipeline scheduling, checkpoint advancement, concurrent writers, replay/backfill integrity, runtime performance, cost and billing.

No resources were deployed, schedules changed, jobs started, grants applied, homework answers written or Wednesday reconstructed Terraform modified. Offline checks do not upgrade area-level integration, security, resilience or operational evidence.
# Incremental Gold adaptation — 2026-10-17

The Richard adaptation now uses `gold.incremental_fact_station_snapshot` for dashboard history and an updated `redshift_schema.txt` describing all 19 columns of the three incremental Gold tables. Column names/types/order were read from the live `information_schema.columns` catalog after migration. Date joins use `snapshot_date`, numeric counts/capacities are BIGINT, and station names belong to the station dimension. Instructor originals remain unchanged.

After these edits, `.venv/bin/python docs/Training/Week6/4.3-thur-bedrock-streamlit-lab/verify-local.py` passed all 11 tests (`Ran 11 tests in 0.701s`, `OK`). Existing ScriptRunContext/deprecation warnings were nonfatal. Python AST, updated SQL-reference, documentation-fence and local-link checks passed. The live procedure definition matched the submitted Gold definition, ignoring its terminating semicolon and whitespace.

The exact dashboard history SELECT ran successfully through the Redshift Data API against Richard's existing Ohio workgroup/database `dev`, returning two hourly groups with 2,518 observations and 2,518 stations each. This verifies SQL/data access for the owner identity, not a restricted dashboard reader or a running Streamlit UI. See [pipeline migration evidence](../3.4-wed-incremental-pipeline/evidence/2026-10-17-gold-migration.json). No Bedrock inference, browser interaction, EC2 deployment or new Glue execution occurred. The preparation records below describe earlier work and retain their original evidence boundaries.

