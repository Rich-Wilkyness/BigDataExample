"""Find coordinate-based station groups without supplying target labels."""

# This sibling import executes its local CSV/Parquet read. Run from this directory
# so the loader and this script belong to the same self-contained demo.
from load_citibike import df

from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler

# Use only coordinates. Capacity and bike availability do not influence
# these groups, so interpret the result as geographic similarity.
features = ["latitude", "longitude"]

# Square brackets select columns; dropna removes rows missing a coordinate.
# The original row index is preserved so results can be joined back safely.
X = df[features].dropna()

# K-Means uses distances. Standardizing makes each feature have comparable
# scale in this dataset; it is not a conversion to physical distances.
# There is no held-out prediction test in this exploratory clustering demo.
scaler = StandardScaler()
X_scaled = scaler.fit_transform(X)

# Ask for five groups. A seed and multiple starts stabilize this classroom
# example; five is a choice, not a discovered number of neighborhoods.
model = KMeans(
    n_clusters=5,
    random_state=42,
    n_init=10
)

# Use the retained indices to avoid assigning labels to rows we dropped.
# copy() gives us an independent table for the new cluster column.
results = df.loc[X.index].copy()
# fit_predict learns centers and returns one integer group ID per row.
# Group IDs are arbitrary names: cluster 4 is not better than cluster 0.
results["cluster"] = model.fit_predict(X_scaled)

print("\nStations per cluster:")
print(results["cluster"].value_counts().sort_index())

# These are group means expressed in original latitude/longitude units.
# They summarize each group, rather than being official geographic labels.
print("\nCluster centers:")
print(
    results.groupby("cluster")[
        ["latitude", "longitude"]
    ].mean()
)
