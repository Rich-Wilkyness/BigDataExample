# MLflow regression serving: theory

[Step-by-step guide](README.md)

## Training to deployment

This is the capacity regression model from demo 03 with MLflow logging and registration integrated into one complete script. `fit()` trains; evaluation produces MAE and R²; `log_model()` saves the model and signature; registration creates a named version; `champion` is assigned explicitly in the registry UI to a chosen version; serving loads that saved version for HTTP inference.

The source's final model logging includes `skops_trusted_types=["sklearn.tree._tree.Tree"]` for the locally trained forest. That setting is retained from the conversation for this trusted classroom model; the full installed package versions were not captured.

## Comparing runs

Parameters describe configuration and metrics describe performance. Repeating the same data, seed, and configuration can yield identical metrics. Changing configuration creates an experiment to compare, but the newest run is not necessarily best. This script leaves promotion to an explicit learner decision. For the fully separated validation/final-test workflow, follow demo 07.

The tracked regression script saves the plot locally; it does not log that PNG as an MLflow artifact. A logged model artifact and a plot file are separate outputs.

## Serving boundary

The client sends only latitude and longitude, matching the signature. It does not query PostgreSQL or retrain the model. `--env-manager local` uses the current Python environment. The loaded model stays fixed until the serving process restarts, even if its registry alias changes.
