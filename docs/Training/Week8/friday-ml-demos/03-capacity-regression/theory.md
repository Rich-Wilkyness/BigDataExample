# Capacity regression: theory

[Step-by-step guide](README.md)

## Prediction task

Features are latitude and longitude. The target is station capacity. Rows require positive capacity and non-null coordinates. The model uses an 80/20 random split with seed 42, trains 100 Random Forest trees with depth 10, and predicts capacity for the held-out stations. The script requires at least 20 usable rows.

The forest averages its trees' numerical predictions. Location can capture geographic patterns but may not sufficiently explain capacity; this is a teaching problem rather than a demonstrated operational capacity-planning tool.

## MAE and R²

MAE is the mean absolute difference between predicted and actual capacity, measured in docks. For absolute errors of 4, 7, 5, and 8, MAE is 6 docks. It is an average over examples, not a guarantee about an individual prediction.

`R² = 1 - sum((actual - predicted)²) / sum((actual - mean(actual))²)`.

For nonconstant test targets, 1 means perfect predictions, 0 matches the test-mean reference's squared error, and a negative value is worse. R² is not a percentage of predictions that are correct. The conversation reported MAE 6.09 and R² 0.652; these were not reproduced here.

## Reading the plots

The map colors stations by actual capacity. The scatter plot compares held-out actual capacities with predictions. Points near the diagonal have smaller errors. Lower MAE is better; larger R² is better on the same evaluation data. Compare settings on validation data before making claims about the best final model.

## Classroom visual

![Classroom examples of numerical regression relationships](<../../Screenshot 2026-10-30 at 11.52.50 AM.png>)

These illustrate several relationship shapes. They are not the Random Forest’s fitted Citi Bike plots. The script’s own actual/predicted plot is generated only when you run the demo.
