# Flask fraud dashboard and GenAI: steps

[Demo index](../README.md) · [Theory](theory.md) · [Shared setup](../setup.md) · [Reconstruction provenance](provenance.md)

## What is included

This is a new implementation reconstructed from the classroom conversation. The original ZIP is not needed. The app collects demo 08's prediction events into SQLite, displays recent transactions, and requests OpenAI explanations on demand. MLflow tracing is built into the Flask process.

## Preview with sample records

Use this first if Kafka and MLflow are not running. This previews the actual dashboard with four clearly labeled sample records. It does not train a classifier, consume Kafka, call OpenAI, or create MLflow traces.

1. From `friday-ml-demos`, activate the shared environment from [setup](../setup.md), install Flask, and enter this directory:

   ```bash
   source .venv/bin/activate
   python -m pip install 'Flask>=3.1,<4'
   cd 09-flask-genai
   ```

2. Use a separate preview database and load the fixtures:

   ```bash
   export FRAUD_DB_PATH="$PWD/preview.sqlite3"
   python load_sample.py
   export MLFLOW_TRACING_ENABLED=false
   python app.py
   ```

3. Open `http://127.0.0.1:5050`. The four fixtures produce 4 processed, 2 flagged, and 50% accuracy. They deliberately include a correct legitimate prediction, correct fraud prediction, false positive, and false negative. These are fixture values, not model evaluation results. Re-running the loader does not duplicate them.

4. The Explain button requires API configuration; without it, the page displays a configuration message. Browsing and automatic refresh make no paid requests. Stop Flask with Ctrl+C before starting the connected workflow below.

## Connect to the classroom pipeline

Complete [demo 08](../08-kafka-fraud-inference/README.md) and keep Kafka, the MLflow tracking server, fraud model server, producer, and inference consumer running. Prediction events must include the five original transaction features. This app does not require PostgreSQL, Bedrock, Redshift, or the earlier Streamlit application.

1. In an activated terminal, from `friday-ml-demos`, install this demo's full requirements:

   ```bash
   source .venv/bin/activate
   cd 09-flask-genai
   python -m pip install -r requirements.txt
   ```

2. Configure the Flask process in that terminal:

   ```bash
   export FRAUD_DB_PATH="$PWD/fraud.sqlite3"
   export MLFLOW_TRACING_ENABLED=true
   export MLFLOW_TRACKING_URI=http://127.0.0.1:5000
   export OPENAI_API_KEY='YOUR_API_KEY'
   export OPENAI_MODEL='YOUR_AVAILABLE_MODEL'
   python app.py
   ```

   Set an actual model available to your API account. The sample preview's database remains separate. Tracing is enabled by default and requires the tracking server to be available when Flask starts. The API client uses a 30-second timeout and no automatic retries.

3. In another terminal, from `friday-ml-demos`, start the collector using the same live database:

   ```bash
   source .venv/bin/activate
   cd 09-flask-genai
   export FRAUD_DB_PATH="$PWD/fraud.sqlite3"
   export KAFKA_BOOTSTRAP_SERVERS=localhost:9092
   python collector.py
   ```

   The default consumer group is `fraud-flask-collector-v2`. A new group starts with new messages; an existing group resumes saved offsets. Leave the producer and inference consumer from demos 07–08 running so new predictions arrive.

4. Open `http://127.0.0.1:5050`. Check that new transactions and their amounts appear. The latest 100 stored predictions refresh every three seconds; summary statistics cover all records in this database, across model versions. Each row identifies its model version.

5. Click Explain on one transaction. The request sends its features and classifier prediction to OpenAI, then displays the generated text. Ground-truth labels and the correctness field are excluded from the explanation prompt. Older events without complete features remain visible and cannot be explained.

6. In MLflow at `http://127.0.0.1:5000`, open the `fraud-genai-analysis` experiment and inspect the Traces tab after an explanation request. The app already calls `mlflow.openai.autolog()` and wraps its explanation function with `mlflow.trace`; no manual code changes are needed. Review explanation quality using the criteria in [theory](theory.md). Live classifier monitoring remains [demo 10](../10-live-model-monitoring/README.md).

7. Stop Flask and the collector with Ctrl+C when finished. Stored SQLite records persist between starts. The app binds to loopback on port 5050 and uses Flask's local development server.

## Files and outputs

| File | Responsibility |
| --- | --- |
| `app.py` | Flask routes, on-demand OpenAI Responses calls, and MLflow instrumentation |
| `collector.py` | Kafka consumer, SQLite persistence, and explicit offset commits |
| `storage.py` | Schema, event validation, duplicate handling, and dashboard queries |
| `templates/index.html` | Dashboard structure |
| `static/dashboard.js` | Three-second refresh and Explain requests |
| `static/dashboard.css` | Dashboard presentation |
| `requirements.txt` | Dependencies for the connected demo |
| `sample-predictions.json` and `load_sample.py` | Optional sample-only preview |
| `test_demo.py` | Offline behavior checks |
| `provenance.md` | Reconstructed versus source-supplied behavior and verification limits |

The default database is `fraud.sqlite3` beside these scripts. `FRAUD_DB_PATH` overrides it; use the same absolute path for Flask and the collector. SQLite may create temporary WAL/SHM sidecar files. No key is saved in the database or source code. Explanations are displayed on demand and traced when enabled; this reconstruction does not persist explanation text in SQLite.

## Verification

Run the offline checks after installing requirements:

```bash
python -m unittest -v test_demo
```

Twelve tests passed using temporary SQLite databases, Flask's test client, a mocked Kafka consumer, and mocked OpenAI responses, including the actual SDK with a mock HTTP transport. JavaScript syntax also passed `node --check static/dashboard.js`. The checked environment used Python 3.14.5, Flask 3.1.3, OpenAI 3.42.0, and kafka-python 3.0.12. No real broker connection, MLflow trace export, paid API request, or visual browser inspection was performed; those connected checks remain pending.

## Implementation references

The integration follows the [OpenAI Python Responses API](https://developers.openai.com/api/reference/python/resources/responses/methods/create) and [MLflow OpenAI tracing documentation](https://mlflow.org/docs/latest/genai/tracing/integrations/listing/openai/). Route checks use [Flask's test client](https://flask.palletsprojects.com/en/stable/testing/). These references were reviewed October 31, 2026; they document the APIs, not the origin of the missing classroom ZIP.

## Learning checkpoints

**Before running:** For preview, load the four fixtures into a separate database. For live records, start the collector and demo 08. Supply an OpenAI key/model only for Explain.

**Expected output:** Preview shows 4 processed, 2 flagged, and 50% accuracy. Connected mode shows real local prediction events. An explicit Explain click requests provider text.

**Interpret it:** Polling reads local SQLite only. A classifier label, generated explanation, and request trace have different meanings.

**Check your understanding:**

1. Why should refreshing the table not make another paid OpenAI request?
2. Does a correct classifier prediction guarantee the generated explanation is supported?

Record your observed result before moving to another demo. Sample/reported metrics describe their stated data and environment, not a required answer for your machine.
