# Station classification: theory

[Step-by-step guide](README.md)

## Classification task

The inputs are latitude and longitude. The target is a teaching category derived from station capacity: Small, Medium, or Large. The script ranks capacities, divides the ranks into three quantile groups, and uses a stratified 80/20 split so each class is represented in the training and test sets.

These are dataset-relative teaching labels, not official Citi Bike categories. `rank(method="first")` breaks ties by row order, so identical capacities can receive different labels. Fixed business thresholds would have different semantics.

## Metrics and plots

Accuracy is the fraction of correct predictions. For a particular class, precision asks how many predictions of that class are correct; recall asks how many actual members were found. F1 is their harmonic mean. Support is the number of actual examples per class in the test set.

The confusion matrix has actual classes in rows and predicted classes in columns; diagonal entries are correct predictions. The geographic plot shows predicted categories. This predicts station size, rather than future bike availability or fraud.

## Classroom visual

![Simplified classroom map of ML tasks](<../../Screenshot 2026-10-30 at 11.53.34 AM.png>)

This demo uses one of three mutually exclusive station-size labels per station, so it is multiclass classification. Multiple labels simultaneously would be a different task. The picture is a simplified taxonomy rather than a complete map of ML.
