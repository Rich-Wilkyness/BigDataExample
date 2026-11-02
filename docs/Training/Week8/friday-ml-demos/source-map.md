# Source map and consolidation decisions

[Demo index](README.md)

The two original conversations are preserved unchanged. Line ranges below refer to those original files at cleanup time, not the generated scripts.

| Destination | Source | What was retained |
| --- | --- | --- |
| Common theory | `chat.md` 909–1670; `chat2.md` 640–953 and 1421–1810 | Features, targets, ML types, lifecycle, metrics, reproducibility, experiment comparison |
| 01 clustering | `chat.md` 3063–3079, 3250–3314 | Station view, pandas loader, final metadata-based K-Means script |
| 02 live status | `chat.md` 3250–3275, 3326–3389 | Its own loader, station view, one-shot status enrichment script |
| 03 capacity regression | `chat.md` 3833–4014 | Final PostgreSQL capacity model and Matplotlib plots |
| 04 classification | `chat2.md` 1–270 | Complete station-size classification example supplied before the class moved on |
| 05 MLflow serving | `chat2.md` 274–545 and 584–638, plus 03's base script | Integrated tracking/registration block and final tree serialization setting, serving and request sequence |
| 06 time series | `chat2.md` 954–1272 | Complete synthetic series generator, chronological split, two models, and plots |
| 07 Kafka training | `chat2.md` 2195–2283 and 2285–2648 | Final labeled producer, CSV collector, and repeated batch trainer; broker setup now uses the documented Kafka 4.4.0/KRaft adaptation |
| 08 Kafka inference | `chat2.md` 2925–3265, 3390–3620, 4462–4480 | Deployment procedure, later full inference script, and final nested feature payload |
| 09 Flask/GenAI | `chat2.md` 4415–4642 and 4937–5198 | Final Flask/OpenAI app choice, collector configuration, explanation workflow, and tracing in the correct process |
| 10 monitoring | `chat2.md` 4644–4935 | Full rolling-window monitor and metric interpretation |

## Final-file adjustments

- The first cleanup replaced Linux database settings with `DATABASE_URL`. The current lessons now use shared local CSV/Parquet readers and the verified AWS snapshot export; SQL files are retained only as historical references.
- Demo 05 combines the supplied MLflow block with the full regression script and incorporates `skops_trusted_types` directly, so no patch-by-patch reconstruction is required.
- Demo 08 preserves original features and now pins a numbered model in a local deployment file. The server reports its loaded version/URI/source run, and inference/monitoring discover that identity instead of relying on manually supplied version labels.
- New demo directory names use kebab case. Recovered Python filenames retain the names used in the conversations so their imports and process commands remain recognizable.
- Package lists collect the dependencies of the recovered scripts; they are not recovered version locks. No generated CSV, PNG, MLflow database, model artifact, Kafka data, or API key is bundled.

## Earlier alternatives kept out of the final walkthroughs

The initial class agenda and local fraud batch scripts in `chat.md` 1–908 were planning material, followed by a different final Kafka-fed training workflow. Their `foreign`/`velocity` feature schema is incompatible with the later `distance_from_home`/`transactions_last_hour` schema. The earlier `train_fraud.py` proposal in `chat2.md` 1810–2193 was likewise replaced by the Kafka-fed trainer. The final guides use that later producer and trainer together.

The Databricks/Unity Catalog variation, standalone reasoning-model tracing example, and original S3/Parquet five-algorithm examples were proposed alternatives rather than the final local workflow. They remain in the original conversations. The original forecasting examples assumed status history that the local PostgreSQL data did not contain; the final time-series demo explicitly generates synthetic observations.

The attempted Streamlit/Bedrock/Redshift extension in `chat2.md` 3621–4413 was replaced by Flask/OpenAI. AWS profiles, Redshift access, and Bedrock code are therefore excluded from the finalized dashboard demo. Error stack traces, exploratory schema listings, file searches, abandoned connection fixes, and diagnostic tracing tests are omitted from the cleaned guides.

The conversation reports a working Flask dashboard, but does not include its generated ZIP source. Demo 09 now supplies a new implementation of its described behavior. Its [provenance](09-flask-genai/provenance.md) distinguishes the known workflow from reconstructed database, routes, prompt, interface, and sample data; these are not claimed to be the original files. The time-series MLflow integration and automated GenAI quality evaluation were suggested extensions without complete implementations; they are not presented as completed demo files.

## Current learning material

The [main Friday lecture](../5_Fri_ML_Flow.md) remains the comprehensive theory reference and retains all six original screenshots. The [old steps page](../5.1_ML_steps.md) now routes to the per-demo procedures so old Linux paths, ZooKeeper commands, and missing-attachment instructions do not compete with the current guides. Homework and the source chats are unchanged.

The current Kafka setup is an intentional modernization to Kafka 4.4.0/KRaft based on Apache's quickstart and release documentation reviewed October 31, 2026; it is not a claim about the teacher's original broker. The commented configuration isolates this local lab's state. The earlier comment-only pass preserved Python/SQL logic; the subsequent local-data and fixed-evaluation revision intentionally changes Python behavior as recorded below. New visuals are labeled illustrations, not reproduced classroom or pipeline metrics.

## Current robustness and learning revision

All demo guides now include starting-state checks, expected outputs, interpretation, and knowledge questions. A local AWS export replaces the mandatory PostgreSQL path. The collector/trainer cooperate through file locks and immutable snapshots; the fraud workflow uses persistent validation/final-test papers and explicit promotion. The fraud serving wrapper is a documented new adaptation that loads MLflow artifacts while returning their identity. These changes intentionally extend the recovered scripts; earlier claims of unchanged Python behavior apply only to the prior comment-only revision.
