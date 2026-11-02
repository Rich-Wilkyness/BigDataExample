# Reading the demo code

[Demo index](README.md) · [Main lecture](../5_Fri_ML_Flow.md) · [Visual companion](visuals/README.md)

Read a demo's theory, then its steps, then the source file. Comments inside the code explain what each stage changes and why it belongs there. The top-level classroom scripts execute as soon as Python runs them; importing `load_citibike.py` also executes its database read. The Flask app instead uses functions and a main guard so tests can import it without launching a server.

## Follow the inputs and outputs

| Demo | Read these files in order | What to watch |
| --- | --- | --- |
| 01 | `shared/station_data.py` → `load_citibike.py` → `clustering.py` | Local file validation, one row per station, coordinate scaling, arbitrary cluster IDs |
| 02 | `load_citibike.py` → `live_status.py` | Static metadata versus current snapshot, HTTP envelope, station-ID inner join |
| 03 | `regression.py` | X/y separation, held-out split, fit versus predict, MAE/R², two plot axes |
| 04 | `classification.py` | Rank-based teaching labels, stratification, confusion-matrix orientation |
| 05 | `regression.py` | Tracking server, run context, logged artifact, registry version, mutable alias |
| 06 | `timeseries_regression.py` | Generated patterns, chronological slicing, linear trend versus tree extrapolation |
| 07 | `fraud_producer.py` → `fraud_training_consumer.py` → `train_streaming_fraud.py` | Synthetic labels, JSON bytes, Durable CSV rows, immutable snapshots, fixed validation/final-test papers, batch fitting |
| 08 | `fraud_inference_consumer.py` | Explicit selection, identity-reporting model API, exact five features, output acknowledgement, commit boundary |
| 09 | `storage.py` → `collector.py` → `app.py` → `templates/index.html` → `static/dashboard.js` | Shared SQLite schema, deduplication, route actions, polling versus paid calls |
| 10 | `monitor_fraud.py` | Independent group, version filter, paired rolling queues, metric step |

The commented [Kafka configuration](kafka-server.properties) controls the broker and controller, rather than the Python application. The [figure generator](visuals/generate-learning-figures.py) is an optional local teaching aid: it uses synthetic values and fits no model.

## Read the Python syntax in context

| Expression | Meaning here | Why it matters |
| --- | --- | --- |
| `df[["latitude", "longitude"]]` | Select two columns as a DataFrame | Maintains named model inputs instead of one unstructured array |
| `df.loc[X.index].copy()` | Select the retained rows and make an independent table | Attaches cluster labels to the correct stations after rows were dropped |
| `model.fit(X_train, y_train)` | Learn model state from known examples | This is training; saving or serving is a separate operation |
| `model.predict(X_test)` | Apply learned state to other inputs | Tests generalization without refitting on the answers |
| `with mlflow.start_run(...)` | Group logging inside a managed run lifetime | Associates parameters, metrics, and the artifact with one execution |
| `json.dumps(value).encode("utf-8")` | Convert Python data into Kafka bytes | Defines the event wire format for other processes |
| `producer.send(...).get(timeout=10)` | Wait for an output acknowledgement | Establishes a publish-before-commit ordering, not a distributed transaction |
| `deque(maxlen=500)` | Keep the most recent 500 items | Bounds memory and defines the rolling evaluation population |
| `if __name__ == "__main__"` | Run startup only for direct script execution | Lets tests import Flask/storage logic without launching services |
| `@app.post(...)` | Register an explicit action endpoint | An Explain request can call a paid provider; polling stays read-only |

## Know the example boundaries

Changing comments does not change a model's behavior. Kafka broker version, Python client package version, and model registry version are three independent version numbers. KRaft changes cluster metadata management; it does not retrain the model or change transaction features.

The updated CSV and inference consumers explicitly commit each processed record’s next offset after the corresponding write/output acknowledgement. Snapshot locking coordinates the local collector and trainer. A crash can still replay input/output, as explained in the comments. The reconstructed Flask collector explicitly commits each processed message's next offset after a SQLite commit and deduplicates transaction/model identities. Neither is claimed to provide an atomic end-to-end exactly-once system. No retries, production deployment, or additional learner work are implied by this annotation pass.

The optional `station-view.sql` files remain only as historical references; the active lessons require no SQL database. `export-station-data.py` converts existing AWS GBFS snapshots to the local station files. `training_data.py` owns the fixed fraud validation/test papers. `select-model.py` and `serve-model.py` make the deployed version explicit.
