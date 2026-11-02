# Station clustering: theory

[Step-by-step guide](README.md)

## What is learned

K-Means receives latitude and longitude with no predefined neighborhood labels. `StandardScaler` scales the coordinate features; `fit_predict()` assigns each station to one of five clusters. The printed group means summarize the locations of the resulting clusters.

Cluster numbers are arbitrary identifiers, not rankings, official neighborhoods, or fraud scores. Changing `n_clusters` changes the requested number of groups. Scaling coordinates supports this classroom example but does not turn latitude/longitude into exact geographic distances.

## Pipeline

Existing AWS GBFS snapshot → local CSV/Parquet → pandas → coordinate scaling → K-Means → cluster counts and centers.

The export contains one metadata row per station ID from the selected snapshot. Rows without coordinates are dropped before clustering. This script prints results; it does not produce a map or use availability measurements.

## Classroom visuals

![Classroom concept: observations before and after grouping](<../../Screenshot 2026-10-30 at 11.54.16 AM.png>)

![Classroom concept: three groups separated by boundaries](<../../Screenshot 2026-10-30 at 11.54.45 AM.png>)

These are conceptual classroom images, not outputs from this five-cluster station script. Group boundaries depend on the selected features and distance measure.
