# Richard's local application adaptation

These are separate copies of the instructor's six application files. Original snapshots remain unchanged under `../reference/instructor/`. The app uses Richard's existing pipeline. On 2026-10-17 its history query and schema context were aligned to the live incremental Gold model; see the [migration record](../../3.4-wed-incremental-pipeline/verification.md).

## Changes from the instructor source

| File | Adaptation |
| --- | --- |
| `app.py` | Requires explicit `REDSHIFT_WORKGROUP` and `REDSHIFT_DATABASE` for the optional history query instead of falling back to instructor warehouse names. History reads `gold.incremental_fact_station_snapshot`; live GBFS flow is retained. |
| `bedrock_sql.py` | Reads `AWS_REGION` (default `us-east-2`); uses adaptive SDK retries with four total attempts, equivalent in count to the original Config's three retries plus first attempt. Prompts, output-token limits and model default are retained. |
| `redshift_query.py` | Reads the same region and requires explicit warehouse/database environment values; uses the SDK result paginator. Parsing, row limit, polling, decoding and best-effort cancellation are retained. |
| `pages/2_AI_SQL_Generator.py` | Stores repair output as `pending_sql`, reruns, then applies it before constructing the SQL editor. This fixes Streamlit's restriction on modifying a keyed widget after instantiation. Approval remains a separate Query Redshift click. |
| `requirements.txt` | Expands pandas upper bound to `<4` and SQLGlot to `<31` to cover the existing environment tested here. Other ranges are retained. This is a compatibility adaptation, not a lockfile or verification of every permitted version. |
| `redshift_schema.txt` | Describes the three live-verified `gold.incremental_*` tables, actual BIGINT fields, `snapshot_date` joins and capture-time grain. Instructor context remains in the reference directory. |

## Offline first

From `/Users/richardwilkerson/VSCodeProjects/BigDataExample`:

```bash
.venv/bin/python docs/Training/Week6/4.3-thur-bedrock-streamlit-lab/verify-local.py
```

Expected: 11 passing checks. This command uses synthetic service responses and makes no AWS or GBFS requests. It intentionally reproduces the instructor Repair SQL error as an expected baseline case and verifies the separate adaptation works.

## Configuration for a later local run

The application uses boto3's normal credential chain, including an already configured local profile or an instance role on a host. There is no `.env` loader. Set values in the same shell that starts Streamlit; no credential values belong in these files.

| Setting | Reader |
| --- | --- |
| `AWS_PROFILE` | SDK credential chain; use your existing authorized profile, not automatically the instructor's `company`. Leave unset when using the intended default chain/instance role. |
| `AWS_REGION` | Both adapted helpers and home history; default `us-east-2`. Set explicitly. |
| `REDSHIFT_WORKGROUP` | Both historical/AI read paths; required. Use your own verified workgroup. |
| `REDSHIFT_DATABASE` | Both historical/AI read paths; required. Database name is not schema name. |
| `BEDROCK_MODEL_ID` | Bedrock helper; default copied from instructor, `us.amazon.nova-micro-v1:0`. Verify model/profile availability and authorization before use. |

Example shell shape, with intentionally unresolved placeholders (replace before running):

```bash
export AWS_PROFILE='YOUR_AUTHORIZED_PROFILE'
export AWS_REGION='us-east-2'
export REDSHIFT_WORKGROUP='YOUR_VERIFIED_WORKGROUP'
export REDSHIFT_DATABASE='YOUR_DATABASE'
export BEDROCK_MODEL_ID='YOUR_VERIFIED_MODEL_OR_PROFILE_ID'
```

If dependencies are absent, the installation command is below. It was not run for this task; checks used the existing repository environment. The installer may contact a package registry and change that environment, so review the requirements first.

```bash
.venv/bin/python -m pip install -r docs/Training/Week6/4.3-thur-bedrock-streamlit-lab/richard/requirements.txt
```

After the [main prerequisites](../README.md) are met, the normal multipage launch is:

```bash
.venv/bin/python -m streamlit run docs/Training/Week6/4.3-thur-bedrock-streamlit-lab/richard/app.py --server.address 127.0.0.1
```

The home page immediately requests live GBFS data. Select the AI page from navigation to generate SQL. To study the AI screen independently of the map's HTTP path, use:

```bash
.venv/bin/python -m streamlit run docs/Training/Week6/4.3-thur-bedrock-streamlit-lab/richard/pages/2_AI_SQL_Generator.py --server.address 127.0.0.1
```

The AI helper creates SDK clients during import; configuration and credentials need to be ready before launching. Generation and Repair call Bedrock; Query Redshift executes SQL and then automatically invokes Bedrock to explain successful results. That explanation sends up to 50 returned rows to the model. Review both the edited SQL and the data-sharing choice before clicking. These launch commands were not executed during preparation, and no current credentials or grants were tested.

No homework analytical question is prefilled with a completed answer. If your Gold model is unfinished, keep working on your own pipeline and use the file reading/offline route now.
