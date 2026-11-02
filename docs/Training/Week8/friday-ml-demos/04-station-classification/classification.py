"""Predict teaching-defined station-size classes from location."""

import pandas as pd
import matplotlib.pyplot as plt

from pathlib import Path
import sys

# Share the file-input contract while keeping each demo's own runnable script.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from shared.station_data import load_stations

from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    ConfusionMatrixDisplay
)

# 1. Load one exported station metadata row per ID from a local file.
# Positive-capacity and known-coordinate filtering belongs to this task;
# the unmodified export still preserves zero or missing source measurements.
df = load_stations(require_capacity=True)
if len(df) < 20:
    raise ValueError("Need at least 20 stations with positive capacity and known coordinates.")

# 2. Create classification labels
# Quantile bins produce roughly equal-sized classes
# Rank capacities and split ranks into three roughly equal-sized groups.
# These are teaching labels computed from this dataset, not official sizes.
# Ties are broken by row order, so equal capacities can receive different
# labels. Fixed thresholds would be a different labeling contract.
df["size_category"] = pd.qcut(
    df["capacity"].rank(method="first"),
    q=3,
    labels=["Small", "Medium", "Large"]
)

# 3. Features and target
# Use coordinates as inputs and the derived category as the known target.
# Including capacity itself would reveal how we constructed the labels.
X = df[["latitude", "longitude"]]
y = df["size_category"]

# 4. Split into train and test data
# stratify=y approximately preserves each class proportion in both splits.
# Enough examples of every class must exist for this split to be possible.
X_train, X_test, y_train, y_test = train_test_split(
    X, y,
    test_size=0.2,
    random_state=42,
    stratify=y
)

# 5. Train classifier
# The classifier combines decision-tree votes to choose a category.
# Tree depth is a complexity setting; changing it may change generalization.
model = RandomForestClassifier(
    n_estimators=100,
    max_depth=10,
    random_state=42,
    n_jobs=-1
)

# Learn only from the training examples; predicting test rows does not fit.
model.fit(X_train, y_train)

# 6. Predict
predictions = model.predict(X_test)

# 7. Evaluate
# Accuracy counts correct labels. The report also gives per-class precision,
# recall, F1, and support, so mistakes in one category remain visible.
accuracy = accuracy_score(y_test, predictions)

print(f"Accuracy: {accuracy:.2%}")
print(classification_report(y_test, predictions))

# 8. Visualize
fig, axes = plt.subplots(1, 2, figsize=(13, 5))

# Rows are actual classes and columns are predicted classes. Supplying the
# label order makes Small/Medium/Large appear consistently across runs.
ConfusionMatrixDisplay.from_predictions(
    y_test,
    predictions,
    labels=["Small", "Medium", "Large"],
    cmap="Blues",
    ax=axes[0],
    colorbar=False
)

axes[0].set_title("Classification Confusion Matrix")

# Plot predictions geographically
category_colors = {
    "Small": "blue",
    "Medium": "orange",
    "Large": "green"
}

# Align predictions with their corresponding held-out coordinates.
# copy() avoids mutating the original feature DataFrame.
test_results = X_test.copy()
test_results["predicted"] = predictions

# Plot each predicted category separately so the legend matches the colors.
# This map shows predicted classes; it is not an independent evaluation.
for category, color in category_colors.items():
    subset = test_results[
        test_results["predicted"] == category
    ]

    axes[1].scatter(
        subset["longitude"],
        subset["latitude"],
        c=color,
        s=15,
        alpha=0.7,
        label=category
    )

axes[1].set_title("Predicted Station Size by Location")
axes[1].set_xlabel("Longitude")
axes[1].set_ylabel("Latitude")
axes[1].legend()

plt.suptitle(
    f"Citi Bike Classification | Accuracy: {accuracy:.2%}"
)

plt.tight_layout()
# Write the visual output beside this script before opening its plot window.
plt.savefig("classification_results.png", dpi=150)
plt.show()
