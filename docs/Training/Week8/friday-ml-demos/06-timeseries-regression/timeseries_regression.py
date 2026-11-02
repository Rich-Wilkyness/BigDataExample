"""Compare a linear trend and forest on a synthetic future time period."""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

from sklearn.linear_model import LinearRegression
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, r2_score

# --------------------------------------------------
# 1. Generate synthetic hourly station availability
# --------------------------------------------------
# Use a repeatable random generator for a teaching simulation.
# None of these rows are historical Citi Bike observations.
rng = np.random.default_rng(42)

# 30 days times 24 hours gives 720 ordered timestamps. Each row is one
# simulated hourly observation, rather than one station metadata record.
dates = pd.date_range(
    "2026-10-01",
    periods=24 * 30,
    freq="h"
)

df = pd.DataFrame({"timestamp": dates})

# Derive known calendar features from each timestamp. These values would
# be available when forecasting, unlike future measured bike availability.
df["hour"] = df["timestamp"].dt.hour
df["day_of_week"] = df["timestamp"].dt.day_of_week

# Simulate daily patterns:
# Fewer bikes during commuting hours
# A bell-shaped dip around 08:00 models a morning rush; the later dip is
# centered around 18:00. We impose these patterns instead of discovering
# real commuting behavior from observed data.
morning_rush = 9 * np.exp(
    -0.5 * ((df["hour"] - 8) / 2) ** 2
)

evening_rush = 7 * np.exp(
    -0.5 * ((df["hour"] - 18) / 2) ** 2
)

# Add a slight downward trend across the month
df["time_index"] = np.arange(len(df))
trend = -0.005 * df["time_index"]

# Add random variation
noise = rng.normal(0, 2, len(df))

# Combine baseline, repeated dips, downward trend, and noise. clip keeps
# values between 0 and 30; these are continuous teaching values, not counts
# reported by the live API.
df["bikes_available"] = np.clip(
    20 - morning_rush - evening_rush + trend + noise,
    0,
    30
)

# --------------------------------------------------
# 2. Chronological train/test split
# --------------------------------------------------
# Preserve chronological order: train on earlier rows and test on later ones.
# Shuffling would answer a different question from future forecasting.
split = int(len(df) * 0.8)

train = df.iloc[:split]
test = df.iloc[split:]

# Linear regression using elapsed time
linear = LinearRegression()

# Fit one straight-line relationship with elapsed hours. The fitted slope
# can extrapolate in time but cannot represent repeating daily dips.
linear.fit(
    train[["time_index"]],
    train["bikes_available"]
)

linear_predictions = linear.predict(
    test[["time_index"]]
)

# Random Forest using time-based features
# The forest also sees hour-of-day and weekday, allowing repeating patterns.
# Including elapsed time does not make a tree extrapolate a linear trend.
features = ["hour", "day_of_week", "time_index"]

forest = RandomForestRegressor(
    n_estimators=100,
    max_depth=8,
    random_state=42
)

# Train on the earlier period, then use the fixed model on later features.
forest.fit(
    train[features],
    train["bikes_available"]
)

forest_predictions = forest.predict(
    test[features]
)

# --------------------------------------------------
# 3. Evaluate models
# --------------------------------------------------
# Compare both models on exactly the same future targets. Lower MAE and
# higher R2 indicate better fit on this particular synthetic test period.
for name, predictions in [
    ("Linear Regression", linear_predictions),
    ("Random Forest", forest_predictions)
]:
    print(f"\n{name}")
    print(
        "MAE:",
        round(mean_absolute_error(
            test["bikes_available"],
            predictions
        ), 2)
    )
    print(
        "R2:",
        round(r2_score(
            test["bikes_available"],
            predictions
        ), 3)
    )

# --------------------------------------------------
# 4. Plot results
# --------------------------------------------------
# The top panel shows trend against the whole series; the bottom isolates
# the future evaluation period so actual values and predictions can be read.
fig, axes = plt.subplots(2, 1, figsize=(13, 9))

# Plot A: Complete series and linear trend
axes[0].plot(
    df["timestamp"],
    df["bikes_available"],
    alpha=0.5,
    label="Simulated available bikes"
)

axes[0].plot(
    df["timestamp"],
    linear.predict(df[["time_index"]]),
    color="red",
    linewidth=2,
    label="Linear regression trend"
)

axes[0].set_title(
    "Bike Availability Over Time: Linear Trend"
)
axes[0].set_ylabel("Available bikes")
axes[0].legend()

# Plot B: Predictions on unseen future data
axes[1].plot(
    test["timestamp"],
    test["bikes_available"],
    label="Actual simulated values",
    color="black"
)

axes[1].plot(
    test["timestamp"],
    linear_predictions,
    label="Linear Regression",
    color="red"
)

axes[1].plot(
    test["timestamp"],
    forest_predictions,
    label="Random Forest",
    color="blue"
)

axes[1].set_title(
    "Forecasting on the Test Period"
)
axes[1].set_ylabel("Available bikes")
axes[1].set_xlabel("Date")
axes[1].legend()

plt.tight_layout()
plt.savefig(
    "timeseries_regression.png",
    dpi=150
)
plt.show()

# --------------------------------------------------
# 5. Explain the trend
# --------------------------------------------------
# coef_[0] is the fitted change per elapsed hour. Multiplying by 24 converts
# the rate to a day. Correlation describes association, not causation;
# this example deliberately generated its own downward trend.
print(
    "\nLinear slope per hour:",
    round(linear.coef_[0], 5)
)

print(
    "Linear slope per day:",
    round(linear.coef_[0] * 24, 3)
)

print(
    "Correlation between elapsed time and bikes:",
    round(
        df["time_index"].corr(
            df["bikes_available"]
        ),
        3
    )
)
