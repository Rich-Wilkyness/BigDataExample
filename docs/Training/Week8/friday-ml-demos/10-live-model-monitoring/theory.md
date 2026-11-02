# Live fraud model monitoring: theory

[Step-by-step guide](README.md)

## Rolling evaluation

The monitor reads `fraud-predictions` with its own consumer group. It stores the latest 500 matching-version labels and predictions in bounded queues and logs metrics every 100 processed events. The first update uses the available 100 events; the window grows to 500 and then rolls forward. The metric step is the processed-event count.

Accuracy, precision, recall, F1, and confusion-matrix counts evaluate the classifier, not OpenAI's explanations. Immediate evaluation is possible because the synthetic producer supplies ground truth.

## Three evaluation populations

Candidate validation and final-test metrics come from their separate fixed subsets of the initial collected cohort. Demo 08 prints cumulative accuracy since inference startup. This monitor calculates metrics on a recent rolling window. They can differ because they cover different examples and populations.

A drop in metrics can motivate an investigation but does not by itself prove data drift. Replayed prediction messages can also influence these instructional metrics because the monitor does not deduplicate transaction IDs.

## Model version

The monitor reads the actual loaded model identity from `/metadata` at startup and ignores events with a different recorded version or source run. Start a new monitoring process for another model version. Prediction metadata now comes from the identity-reporting model server in demo 08.
