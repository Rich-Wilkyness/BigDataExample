# Friday ML demos

Start here to find each demo's steps, theory, and supporting files. Each directory contains its own scripts; demo 09 is a labeled reconstruction of the missing app; follow the demos in order when a later one needs an earlier model or event stream.

| Demo | What it does | Depends on |
| --- | --- | --- |
| [01 Station clustering](01-station-clustering/README.md) | Groups real station coordinates with K-Means | Local station export |
| [02 Live station status](02-live-station-status/README.md) | Joins station metadata with a live availability snapshot | Local station/status files; optional public live feed |
| [03 Capacity regression](03-capacity-regression/README.md) | Predicts capacity and plots actual versus predicted values | Local station export |
| [04 Station classification](04-station-classification/README.md) | Predicts teaching categories: Small, Medium, Large | Local station export |
| [05 MLflow regression serving](05-mlflow-regression-serving/README.md) | Tracks, registers, and serves the capacity model | Local station export; MLflow |
| [06 Time-series regression](06-timeseries-regression/README.md) | Compares a linear trend with a Random Forest forecast | Generated synthetic data |
| [07 Kafka fraud training](07-kafka-fraud-training/README.md) | Generates labeled events, collects CSV data, and trains model versions | Local Kafka and MLflow |
| [08 Kafka fraud inference](08-kafka-fraud-inference/README.md) | Sends Kafka events to the deployed model and publishes predictions | Model and producer from 07 |
| [09 Flask and GenAI](09-flask-genai/README.md) | Displays predictions and requests OpenAI explanations | 08 for live data; included fixtures for preview |
| [10 Live model monitoring](10-live-model-monitoring/README.md) | Logs rolling classification metrics to MLflow | 08; independent of Flask |

Read the [local requirements and API-key matrix](local-requirements.md) and [data preparation](data-preparation.md), then [shared setup](setup.md); it uses Kafka 4.4.0 with KRaft. Use the [main Friday lecture](../5_Fri_ML_Flow.md) for comprehensive theory, the [theory reading map](theory.md) to connect concepts to demos, and the [code reading guide](code-reading-guide.md) to follow the commented files. Individual demo theory files explain their own models, metrics, and limits. The [source map](source-map.md) records which conversation sections supplied the final files and which earlier proposals were superseded.

The source conversations remain at [chat.md](../chat.md) and [chat2.md](../chat2.md) for reference. The cleaned guides contain the final sequence rather than the debugging history. The [older Friday steps page](../5.1_ML_steps.md) is now a navigation route to these guides, rather than another copy of their commands. [Homework](../5.2_Fri_HW.md) remains separate and unchanged. The [visual companion](visuals/README.md) keeps the six classroom screenshots in context and adds explanatory charts and diagrams.

## Evidence

The [verification record](verification.md) distinguishes executed local checks from pending integration. The station snapshot was exported read-only from existing AWS objects; demos 01–04 and 06 executed locally, demo 05 trained/logged/registered locally, and the revised fraud workflow completed candidate/final evaluation and actual model-handler checks using temporary fixture data. Twenty-two offline tests passed. The original homework, chats, and six screenshots remain unchanged. Real Kafka integration, generic capacity HTTP serving, paid OpenAI requests, trace export, and browser inspection remain pending.

## Improving model comparisons

Demo 07 now freezes complete CSV snapshots, keeps fixed validation/final-test papers, and registers candidates without automatic promotion. Demo 08 explicitly selects a numbered model and supplies server-reported identity in prediction records. Each guide ends with starting conditions, expected output, interpretation, and two knowledge-check questions.
