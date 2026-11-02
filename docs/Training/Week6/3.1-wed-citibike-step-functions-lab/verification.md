# Local verification — 2026-10-14

After the instructor handoff arrived, documentation/provenance checks were rerun successfully and the guide was aligned to the coordinator/checkpoint/physical-Gold architecture. New read-only checks confirmed the coordinator configuration and ENABLED thirty-minute schedule/target. State-machine description and execution listing were denied; successful unattended runs and post-run SQL results remain unverified. The recorded local executable checks below apply to the earlier isolated reconstruction, not a completed instructor-matching deployment.

## Results

| Check | Actual result | Scope |
| --- | --- | --- |
| Python parsing | 17 files passed AST parsing | Includes references, initial copies, four adapted Glue jobs, dashboard, input helper and verifier; no Spark execution |
| JSON | Seven files parsed | Provenance, three ASL definitions, two input examples, IAM checklist |
| Workflow structure | Three state graphs fully reachable with valid transition targets | Local graph checks; AWS ASL service validation not performed |
| Source preservation | Six copies matched retrieved instructor text after documented newline normalization; six local SHA256 hashes verified | First source had CRLF; copies use LF and an additional final newline; no code-content changes |
| Input contract | Valid batch/SQL alignment and replay flag passed; injected/malformed IDs, empty intervals, future intervals rejected | Fixed-clock offline checks |
| Data API reader | Submission/completion, two result pages, null decoding, and SQL failure presentation passed | Boto3/botocore Stubber; no live API requests |
| Streamlit | AppTest sample mode displayed three metrics and three table rows with zero AWS client creation | Synthetic CSV; live Redshift mode not queried |
| Terraform formatting | `terraform fmt -check` passed | Local Terraform 1.13.5 |
| Terraform initialization | `init -backend=false -input=false` completed; HashiCorp-signed AWS provider 6.69.0 selected | Provider download only; no backend/state/AWS changes |
| Terraform configuration | `terraform validate -no-color` passed | Provider schema validation; no AWS plan/apply |
| Markdown | Local file links and fenced blocks passed; whitespace check passed | Filesystem links checked; no claim that external sites or anchors were runtime tested |

Terraform 1.13.5 was downloaded from the official HashiCorp release into `/tmp`, with the archive SHA256 checked against the release's checksum list. This temporary validator is not a system installation or a command added to the user's PATH. Provider downloads and the local provider handshake required sandbox escalation; neither operation deployed resources. `.terraform.lock.hcl` records the selected provider and checksums and is a reproducibility artifact to retain.

## Cloud observations versus execution

Read-only S3 calls retrieved the six instructor scripts. Glue configuration and run histories were inspected in Ohio. Both backfills had successful runs; each incremental job had four successful runs at the later refresh, with the latest landing load completed at 20:32:39 UTC. Those are instructor observations, not newly executed Richard tests.

The actual instructor Terraform, Step Functions workflow, merge/Gold SQL and Streamlit source were not recovered. Step Functions listing was previously denied. The local infrastructure, SQL and visual are Richard follow-along reconstructions, and the source snapshots are clearly separated.

## Pending

- Real Terraform plan/apply against AWS, role trust/access evaluation and database grants.
- Glue/Spark execution of the adapted scripts, published-file/source reconciliation and capacity/cost checks.
- Redshift engine execution of setup/acceptance SQL, atomic rollback behavior, conflicting duplicates and replay tests.
- Live dashboard Data API reads and freshness verification.
- Admission locking, closed-window scheduling, late-arrival reconciliation and end-to-end operational acceptance.
