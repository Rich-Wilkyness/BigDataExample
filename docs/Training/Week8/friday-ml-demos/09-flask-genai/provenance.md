# Reconstruction provenance

[Step-by-step guide](README.md)

## What is known

`chat2.md` names `fraud_flask_demo.zip`, `app.py`, `collector.py`, and `requirements.txt`, but does not include their source or a usable attachment URL. The chat says the assistant created a complete downloadable application. This suggests a generated attachment, but does not establish whether the teacher obtained it that way or where any original files now exist. No public demo origin or original implementation can be confirmed from the supplied text.

The original ZIP remains unavailable. The files now in this directory are a new reconstruction, not recovered original files. They implement the behavior described in the conversation without requiring that attachment.

## Behavior described by the conversation

- Read `fraud-predictions` from Kafka and store prediction records in SQLite.
- Display recent transactions, flagged counts, and classification accuracy in Flask on port 5050.
- Refresh the table every three seconds and provide an Explain action per transaction.
- Pass original transaction features and the classifier prediction to OpenAI on demand.
- Instrument the Flask process's OpenAI calls with MLflow in `fraud-genai-analysis`.
- Use the final feature-bearing output from demo 08 and the collector group `fraud-flask-collector-v2` with a new group's initial position at the latest events.

## Choices made for this implementation

The original schema, routes, prompt, database filename, and page source are unknown. This reconstruction defines `fraud.sqlite3`, `/api/predictions`, and a POST explanation route. A shared storage module keeps the collector and Flask app on the same schema. Model versions remain strings to accept demo 08's configurable version metadata.

Records are unique by transaction ID and model version. SQLite commits happen before the collector commits the corresponding partition offset. Replaying a record does not inflate dashboard counts. Invalid prediction records stop the collector without committing that record; no automatic dead-letter or repair workflow is implemented.

Features are validated as finite numeric inputs. Older records without features can still be displayed; the app does not invent values or ask OpenAI to explain incomplete evidence. The prompt excludes ground-truth labels, asks for uncertainty, and requests risk indicators, possible legitimate explanations, and next steps. It does not request a probability from the binary classifier output.

The optional sample loader uses four labeled fixtures and a separate preview database. Tracing can be disabled explicitly for that preview. These choices support local learning and are not claims about the missing app or a production deployment.

## Evidence boundary

Twelve offline tests passed, covering database persistence, duplicate replay, separate model versions, statistics, old featureless events, invalid data, on-demand requests, configuration errors, provider errors, SDK request/response handling, and commit ordering. JavaScript syntax, Python syntax, Markdown links, and shell-block syntax were checked. Real Kafka integration, MLflow export, paid OpenAI responses, and visual browser behavior remain unverified.

The later local-data/fixed-evaluation revision adds ten shared workflow tests (22 total with this app’s twelve). Prediction identity is now supplied by the pinned model server, not a manually typed version. See the current [verification record](../verification.md) for actual locally executed station and model checks; the original missing ZIP remains unavailable.
