# Flask fraud dashboard and GenAI: theory

[Step-by-step guide](README.md)

## Responsibilities

The Random Forest classifies transactions. The Kafka collector stores prediction records in SQLite. Flask displays them. OpenAI generates an interpretation of a selected transaction's features and prediction.

This directory now includes a new reconstruction of that application, rather than the missing original ZIP. The final application choice was Flask plus OpenAI. The earlier Streamlit/Bedrock/Redshift integration was replaced during the conversation, so it is not a prerequisite for this demo.

## Features and explanation quality

The classifier output must include the nested `features` dictionary from demo 08. It supplies amount, hour, distance from home, new-device status, and recent transaction count. Old records created without those fields do not acquire them when code changes.

The generated text is a risk assessment, not verified fraud evidence or a faithful account of the Random Forest's internal decision process. Explanations should state uncertainty and avoid inventing facts about the customer.

## Tracing versus evaluating

`mlflow.openai.autolog()` instruments OpenAI calls in the Python process where it runs. Adding it to an unrelated app does not trace Flask's requests. The decorator adds an application-level trace around the actual explanation function. Available automatic fields depend on the installed integration version.

Tracing records what happened. Quality evaluation asks whether it was useful and supported. Review 10–20 selected transactions for groundedness, correct interpretation of the classifier output, uncertainty, actionability, and consistency. The chat proposed that review; it did not supply an implemented evaluation dataset or scoring job.

Classifier accuracy and LLM explanation quality are separate measurements. Even a correctly classified transaction can have an unsupported explanation. API calls and traces may contain the supplied transaction details; this classroom data is synthetic.

## Persistence and replay in the reconstruction

The collector writes one row per transaction ID and model version. It commits SQLite first and then commits only that message's Kafka partition offset. A crash before the offset commit can replay the event, but the unique key prevents another stored row. This is local duplicate handling, not an end-to-end exactly-once guarantee.

Dashboard statistics cover all stored rows, across model versions; the table shows the latest 100 arrivals. Use demo 10 for a rolling metric window tied to one selected model version. Sample-preview metrics come from four hand-authored fixtures, not classifier predictions.
