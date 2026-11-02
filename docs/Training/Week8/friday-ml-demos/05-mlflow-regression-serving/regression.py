"""Train and register a capacity model, then plot held-out predictions."""

import os
import pandas as pd
import matplotlib.pyplot as plt

from pathlib import Path
import sys

# Share the file-input contract while keeping each demo's own runnable script.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from shared.station_data import load_stations

import mlflow
import mlflow.sklearn
from mlflow.models import infer_signature

# The tracking server stores runs and the registry. It is separate from the
# model-serving endpoint: tracking uses 5000; inference later uses 5001.
mlflow.set_tracking_uri(os.getenv("MLFLOW_TRACKING_URI", "http://127.0.0.1:5000"))
mlflow.set_experiment("citibike-regression")

from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, r2_score

# 1. Load one exported station metadata row per ID from a local file.
# Positive-capacity and known-coordinate filtering belongs to this task;
# the unmodified export still preserves zero or missing source measurements.
df = load_stations(require_capacity=True)
if len(df) < 20:
    raise ValueError("Need at least 20 stations with positive capacity and known coordinates.")

# 2. Select input features and target
# X contains the information available to the model at inference time.
# y is the known numerical answer used for supervised training.
# Keeping capacity out of X prevents directly revealing the answer.
X = df[["latitude", "longitude"]]
y = df["capacity"]

# 3. Split into training and testing datasets
# Reserve 20% of stations for evaluation before fitting the model.
# The same seed keeps this split repeatable for the same ordered dataset.
# A spatial random split is a teaching evaluation, not a test on a new city.
X_train, X_test, y_train, y_test = train_test_split(
    X, y,
    test_size=0.2,
    random_state=42
)

# The context manager groups configuration, metrics, and the model under
# one run and ends it when this block exits. It does not perform training.
with mlflow.start_run(run_name="random-forest-regression"):

    # 100 trees vote by averaging capacity predictions. Depth limits complexity;
    # the seed controls randomness. These settings should match logged params.
    model = RandomForestRegressor(
        n_estimators=100,
        max_depth=10,
        random_state=42,
        n_jobs=-1
    )

    # This is where learning happens; registration and serving do not fit trees.
    model.fit(X_train, y_train)

    predictions = model.predict(X_test)

    # Report absolute error in docks and relative squared-error performance.
    # Changing settings repeatedly should use validation data for selection.
    mae = mean_absolute_error(y_test, predictions)
    r2 = r2_score(y_test, predictions)

    # Log hyperparameters
    # Record settings separately from measured outcomes. If you change a model
    # setting above, change its logged value here so the run stays truthful.
    mlflow.log_params({
        "n_estimators": 100,
        "max_depth": 10,
        "random_state": 42
    })

    # Log evaluation metrics
    mlflow.log_metrics({
        "mae": mae,
        "r2": r2
    })

    # Describe model inputs and outputs
    # Infer the feature names/types and output type for future input validation.
    # A signature describes the interface, not whether the predictions are good.
    signature = infer_signature(
        X_test,
        predictions
    )

    # Log the trained model
    # Save the fitted forest. The explicit trusted tree type comes from the
    # classroom serialization correction and applies to this locally trained
    # model, not arbitrary downloaded model artifacts.
    model_info = mlflow.sklearn.log_model(
        sk_model=model,
        name="citibike_capacity_model",
        signature=signature,
        input_example=X_test.head(3),
        skops_trusted_types=["sklearn.tree._tree.Tree"]
    )

    # Register the model
    # Registration gives this saved artifact a named version. Each new execution
    # can create another version even when its metrics match the last run.
    registered = mlflow.register_model(
        model_uri=model_info.model_uri,
        name="citibike_capacity_predictor"
    )

    print("Registered model version:", registered.version)

    # Registration creates a candidate. Choosing champion is a separate learner
    # decision in the registry UI; a newer run is not automatically better.
    print("Compare this candidate, then explicitly select champion in the registry UI.")

    print(f"MAE: {mae:.2f}")
    print(f"R²: {r2:.3f}")

# 7. Plot the results
# Create a figure with two axes: input geography and held-out predictions.
# The map uses all stations for context; the evaluation uses test rows only.
fig, axes = plt.subplots(1, 2, figsize=(13, 5))

# Plot 1: Actual capacity by geographic location
scatter = axes[0].scatter(
    df["longitude"],
    df["latitude"],
    c=df["capacity"],
    cmap="viridis",
    s=12,
    alpha=0.8
)

axes[0].set_title("Actual Citi Bike Station Capacity")
axes[0].set_xlabel("Longitude")
axes[0].set_ylabel("Latitude")
fig.colorbar(
    scatter,
    ax=axes[0],
    label="Station capacity"
)

# Plot 2: Actual vs predicted capacity
axes[1].scatter(
    y_test,
    predictions,
    alpha=0.6,
    s=20
)

# The dashed diagonal represents predicted = actual. Distance from that
# line is visual prediction error, not the classifier concept of accuracy.
limit = max(y_test.max(), predictions.max())

axes[1].plot(
    [0, limit],
    [0, limit],
    "r--",
    label="Perfect prediction"
)

axes[1].set_title("Regression: Actual vs Predicted")
axes[1].set_xlabel("Actual station capacity")
axes[1].set_ylabel("Predicted station capacity")
axes[1].legend()

plt.suptitle(
    f"Random Forest Regression | MAE={mae:.2f}, R²={r2:.3f}"
)

plt.tight_layout()
# Save before show(): some interactive backends clear a figure on close.
# A repeated run overwrites this local PNG; it does not log it to MLflow.
plt.savefig("regression_results.png", dpi=150)
plt.show()
