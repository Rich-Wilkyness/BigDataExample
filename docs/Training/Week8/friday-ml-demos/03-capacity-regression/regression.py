"""Train, evaluate, and plot station-capacity regression from coordinates."""

import pandas as pd
import matplotlib.pyplot as plt

from pathlib import Path
import sys

# Share the file-input contract while keeping each demo's own runnable script.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from shared.station_data import load_stations

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

# 4. Train the regression model
# A forest averages many decision-tree predictions. n_estimators controls
# the number of trees; max_depth limits their complexity. n_jobs=-1 uses
# available CPU cores, while random_state controls algorithm randomness.
model = RandomForestRegressor(
    n_estimators=100,
    max_depth=10,
    random_state=42,
    n_jobs=-1
)

# fit() is the learning operation. The target values influence the fitted
# trees here; later predict() calls reuse these trees without retraining.
model.fit(X_train, y_train)

# 5. Predict capacity for unseen stations
predictions = model.predict(X_test)

# 6. Evaluate
# MAE is average absolute error in docks. R2 compares squared prediction
# error with the test-target mean reference; it is not percent accuracy.
mae = mean_absolute_error(y_test, predictions)
r2 = r2_score(y_test, predictions)

print(f"Mean Absolute Error: {mae:.2f} docks")
print(f"R-squared: {r2:.3f}")

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
