# What runs locally, and which credentials are needed?

[Demo index](README.md) · [Shared setup](setup.md)

All ten demos are designed to be walked through on your Mac using local processes. Only the optional OpenAI explanation action requires an API key and provider access. Running locally does not mean every feature runs offline: fetching live public data or requesting an OpenAI explanation still uses the internet.

| Demo | Local inputs/processes | Credentials needed to run |
| --- | --- | --- |
| 01 Clustering | Exported station CSV/Parquet and Python | None after export |
| 02 Status enrichment | Exported information/status files; optional live API mode | None; live mode needs internet |
| 03 Capacity regression | Station file, scikit-learn, Matplotlib | None |
| 04 Station classification | Station file, scikit-learn, Matplotlib | None |
| 05 MLflow regression | Station file, local MLflow tracking and model serving | None |
| 06 Time-series regression | Locally generated synthetic values | None |
| 07 Kafka fraud training | Local Kafka KRaft, collector, trainer, MLflow | None |
| 08 Fraud inference | Local Kafka, registry artifact, local identity-reporting model API | None |
| 09 Flask dashboard | Local SQLite/Flask, prediction collector; optional sample preview | No key for preview/display; `OPENAI_API_KEY` and `OPENAI_MODEL` for Explain |
| 10 Monitoring | Local Kafka predictions and MLflow | None |

AWS credentials are needed only to refresh data from your private S3 bucket, not to read the exported files or train the local models. No Databricks account, cloud SQL database, Bedrock credentials, or cloud deployment is required. A ChatGPT subscription is separate from OpenAI API access; provider billing and account/model permissions apply to the Explain action.

Start with demos 01–04 and 06, which need no running infrastructure after export. Then add the local MLflow server for 05. Demos 07–10 share a local broker and build on the model and prediction stream. Demo 09 also has an independent sample preview if you want to inspect the dashboard before starting Kafka.

OpenAI’s [developer quickstart](https://developers.openai.com/api/docs/quickstart) documents setting `OPENAI_API_KEY` in your environment. Keep the key in the Flask terminal, not in a source file or this conversation.

The [verification record](verification.md) separates executed local checks from live integrations that remain pending. Do not interpret the intended run sequence as proof that every service has already been tested together on your machine.
