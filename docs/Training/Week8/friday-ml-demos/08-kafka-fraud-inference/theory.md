# Kafka fraud inference: theory

[Step-by-step guide](README.md)

## Streaming inference

Kafka event → five input features → HTTP `/invocations` → saved classifier prediction → Kafka `fraud-predictions`.

The consumer does not train. It sends only the expected five features to the model, then compares the prediction with the synthetic label and publishes the result. The label enables immediate demo accuracy checks; real financial outcomes are usually delayed.

## Consumer groups and delivery

The inference group is independent of training-data collection. It publishes the prediction, waits for acknowledgement, then commits that exact input record's next offset. A crash between output and input commit can replay a prediction; this is not an exactly-once transaction.

## Actual model identity

`select-model.py` pins a numbered registry URI and its source run in `deployment.json`. `serve-model.py` loads that artifact once and reports the same identity from `/metadata` and each prediction response. It does not resolve a moving alias for every request. The consumer discovers and verifies this identity instead of accepting a manual version label.

If the server is restarted with another model while inference is running, the mismatch stops the consumer before it publishes another mislabeled result. Restart the consumer to explicitly accept the new identity. Start a new monitor run for that version as well.

The output preserves original transaction features for dashboard analysis. This endpoint returns binary classes, not fraud probabilities. Cumulative terminal accuracy, fixed validation metrics, final test metrics, and rolling monitoring metrics measure different populations.
