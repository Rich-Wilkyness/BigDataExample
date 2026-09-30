# Part 3 starting point

This starter adapts the class weather example. `producer.py` polls Open-Meteo for five cities, including Boise, once per minute and sends JSON to `homework-weather`, keyed by city. `consumer.py` parses those records and retains `key`, `partition`, and `offset`. It adds `processed_at` and can write to the console or MongoDB database `homework_streaming`, collection `weather`. Your meaningful Spark transformation is still a TODO. Choose your own locations or data changes before submitting. The dashboard and schema-evolution exercise come later in Parts 4 and 5.

## Install on the Mac host

Run from the repository root. Your Python scripts run on the Mac; Kafka and MongoDB run in Docker and publish ports to the Mac. No copying scripts into containers is needed.

```bash
cd /Users/richardwilkerson/VSCodeProjects/BigDataExample
source .venv/bin/activate
unset SPARK_HOME
python -m pip install "pyspark==4.2.0" requests kafka-python pymongo pandas streamlit
java -version
spark-submit --version
```

If `.venv` does not exist, create it with `python3 -m venv .venv` before activation. Install Docker Desktop for Apple silicon if missing and open it before using Docker. Spark 4 requires Java 17 or later; Java 21 is a suitable choice. If you need Java and use Homebrew, run `brew install openjdk@21`, then set `JAVA_HOME` with `export JAVA_HOME="$(brew --prefix openjdk@21)/libexec/openjdk.jdk/Contents/Home"` and set `export PATH="$JAVA_HOME/bin:$PATH"` in each Spark terminal. Confirm Spark reports 4.2.0. You do not need a separate Spark download, a native MongoDB install, or a separate `mongosh` download for this Docker route. `pymongo`, `pandas`, and `streamlit` are for the later dashboard; the Spark sink uses the JVM MongoDB connector.

## Start services and create your topic

First run `docker ps -a` to inspect existing containers. Reuse your class Kafka broker if available; use `docker start kafka` if it exists but is stopped. Only run the following creation commands when the named services do not already exist and their host ports are free:

```bash
docker run -d --name kafka -p 127.0.0.1:9092:9092 apache/kafka:4.3.1
docker run -d --name week4-mongo -p 127.0.0.1:27017:27017 -v week4-mongo-data:/data/db mongo:8.0
```

For an existing stopped MongoDB container, use `docker start week4-mongo`. If another MongoDB service already provides port 27017, use that service. Once Kafka is ready, create the topic idempotently:

```bash
docker exec kafka /opt/kafka/bin/kafka-topics.sh --create --if-not-exists --topic homework-weather --partitions 3 --replication-factor 1 --bootstrap-server localhost:9092
docker exec kafka /opt/kafka/bin/kafka-topics.sh --describe --topic homework-weather --bootstrap-server localhost:9092
```

## Checkpoint 1: see parsed events

In terminal 1, activate `.venv`, unset `SPARK_HOME`, and run from the repository root:

```bash
spark-submit --packages org.apache.spark:spark-sql-kafka-0-10_2.13:4.2.0 docs/Training/Week4/2.3_Tue_HW/consumer.py
```

In terminal 2, activate `.venv` and run from the repository root:

```bash
python docs/Training/Week4/2.3_Tue_HW/producer.py
```

Look for rows containing the city, temperature, `key`, `partition`, `offset`, and `processed_at`. `key` should equal the city. Open-Meteo observations may stay the same between polls; `event_time` in this starter is the fetch time, not the API observation time. Empty Spark batches are normal between polls. The producer waits for Kafka acknowledgements during `flush()` and prints API errors if requests fail. Stop a running script with Ctrl-C.

## Checkpoint 2: implement your transformation and write to MongoDB

Edit the TODO in `consumer.py`. Pick one operation you can explain, such as deriving an alert from wind speed or categorizing temperature. Assign the resulting DataFrame back to `events` before `processed` is built. Stop the console consumer, then start the MongoDB consumer:

```bash
spark-submit --packages org.apache.spark:spark-sql-kafka-0-10_2.13:4.2.0,org.mongodb.spark:mongo-spark-connector_2.13:11.1.0 docs/Training/Week4/2.3_Tue_HW/consumer.py --sink mongodb

# use this if spark 4.2 is having conflicts with another spark version like 3.5.9 we used for scala
.venv/bin/spark-submit \
  --packages org.apache.spark:spark-sql-kafka-0-10_2.13:4.2.0,org.mongodb.spark:mongo-spark-connector_2.13:11.1.0 \
  docs/Training/Week4/2.3_Tue_HW/consumer.py --sink mongodb
```

`--packages` downloads the JVM connectors and dependencies on first launch; these are separate from pip packages. MongoDB connector 11.1.0 supports Spark 4.0 or later. The console and MongoDB sinks have separate checkpoints under the gitignored `data/checkpoints/` directory. The first run of each sink reads retained records from the beginning; later runs resume from its checkpoint. MongoDB uses append writes, so retries or intentional replay can produce duplicates.

## Checkpoint 3: inspect MongoDB

Open the shell bundled in the MongoDB container:

```bash
docker exec -it week4-mongo mongosh
```

At the `mongosh` prompt, start with these queries and adapt the filter to your chosen data:

```javascript
// use this to swap what db you are adding the files to
use homework_streaming 

// find takes (filter, column/projection)
// {} filter nothing, hide _id
db.weather.find({}, { _id: 0 }).sort({ processed_at: -1 }).limit(5)

// find where city = boise, hide _id
db.weather.find({ city: "Boise" }, { _id: 0 }).limit(5)

// $gt is "<" for mongo
// find temp greater than 20
db.weather.find({ temperature: { $gt: 20 } }, { _id: 0 }).sort({ temperature: -1 }).limit(5)

// indexing the column "processed_at"
// -1 = descending order (newest first)
db.weather.createIndex({ processed_at: -1 })
db.weather.getIndexes()
```

The index supports retrieving recent documents by processing time. A temperature filter may return no rows depending on the current weather; choose a threshold supported by your data. Type `exit` to leave `mongosh`. Add your transformation description, data choices, and screenshots when the pipeline works.


## Checkpoint 4: bonus
to demonstrate whether MongoDB performs a:
COLLSCAN or IXSCAN

```bash
# IXSCAN
db.weather.find({}, { _id: 0 })
  .sort({ processed_at: -1 })
  .limit(5)
  .explain("executionStats")

# COLLSCAN
# `hint({ $natural: 1 })` causes the COLLSCAN because:
# 1. `hint()` tells MongoDB which access path to use. `$natural` means the collection’s own document traversal order rather than a field index. `1` requests traversal in the forward direction.
# without hint, it will look at indexes first
db.weather.find({}, { _id: 0 })
  .sort({ processed_at: -1 })
  .limit(5)
  .hint({ $natural: 1 })
  .explain("executionStats")
```


## Checkpoint 5: Streamlit

Use the class weather dashboard as your starting point, saved as `dashboard.py` in this homework folder. Connect it to `homework_streaming.weather`. Use the stored Kafka field names `key`, `partition`, and `offset`; only display fields that your consumer actually writes.

### Start the dashboard

From the repository root with `.venv` active, run:

```bash
python -m streamlit run docs/Training/Week4/2.3_Tue_HW/dashboard.py
```

Open the local URL printed in the terminal, usually `http://localhost:8501`. For live updates, keep Kafka, MongoDB, the producer, and the consumer running, with the consumer using `--sink mongodb`. To display previously stored records, only MongoDB and the dashboard need to run.

### How the API fits together

`import streamlit as st` gives the Streamlit module the short name `st`. Calls such as `st.subheader(...)` and `st.line_chart(...)` add elements to the page, generally in execution order. Your dashboard queries MongoDB, converts the records to a pandas DataFrame, prepares that data, and displays it through Streamlit.

```text
MongoDB query → Python records → pandas DataFrame → Streamlit display
```

### Important functions

| Function | Purpose | Example |
| --- | --- | --- |
| `st.set_page_config()` | Configure the browser title and page layout | `st.set_page_config(page_title="Weather", layout="wide")` |
| `st.title()` | Main page title | `st.title("Weather Dashboard")` |
| `st.header()` | Large section heading | `st.header("Weather")` |
| `st.subheader()` | Smaller section heading | `st.subheader("Current Humidity")` |
| `st.caption()` | Small explanatory text | `st.caption("Refreshes every two seconds")` |
| `st.write()` | General purpose display | `st.write(df)` |
| `st.metric()` | Display a prominent value | `st.metric("Cities", city_count)` |
| `st.dataframe()` | Interactive table | `st.dataframe(df, hide_index=True)` |
| `st.columns()` | Create containers side by side | `left, right = st.columns(2)` |
| `st.line_chart()` | Plot a measurement over time | `st.line_chart(temperature_chart)` |
| `st.bar_chart()` | Compare measurements across categories | `st.bar_chart(humidity_chart)` |
| `st.warning()` | Display a warning message | `st.warning("Waiting for data...")` |
| `st.selectbox()` | Return the user's selected option | `city = st.selectbox("City", ["Boise", "London"])` |

### Charts: understand the input DataFrame

For your existing temperature chart, pandas `pivot_table()` creates one row per processing timestamp and one temperature column per city. `st.line_chart()` uses the DataFrame index as the horizontal axis when `x` is omitted, and plots the numeric city columns as separate lines.

```python
temperature_chart = df.pivot_table(
    index="processed_at",
    columns="city",
    values="temperature",
    aggfunc="mean",
).sort_index()

st.subheader("Temperature Over Time")
st.line_chart(temperature_chart)
```

`aggfunc="mean"` combines multiple records for the same city and processing timestamp. This chart shows temperature against processing time; use a genuine observation timestamp if you want to chart when the weather was measured.

For your humidity chart, `.set_index("city")` makes the city names the horizontal axis, and the remaining `humidity` column supplies the bar heights:

```python
humidity_chart = latest[["city", "humidity"]].set_index("city")

st.subheader("Current Humidity")
st.bar_chart(humidity_chart)
```

You can also explicitly name the axes without changing the DataFrame index:

```python
st.bar_chart(latest, x="city", y="humidity")
```

### Columns and metrics

`st.columns(2)` returns two containers. Calling a display method on a container places the element inside that column:

```python
left, right = st.columns(2)
left.metric("Stored Events", total_events)
right.metric("Cities", city_count)
```

Use `with` when placing several elements in one column:

```python
with left:
    st.subheader("Temperature")
    st.metric("Average", f"{avg_temperature:.1f} °C")
```

Label the document count as "Stored Events" because `collection.count_documents({})` counts MongoDB documents. Your city metrics come from the latest record per city within the 500 records fetched by the dashboard, so they describe that selected data rather than every city ever produced.

### Automatic refresh and reruns

Streamlit normally reruns the script from top to bottom when a user changes a widget. A fragment can rerun independently. Your decorator schedules the dashboard function to rerun every two seconds while the session is active:

```python
@st.fragment(run_every="2s")
def dashboard():
    # Query MongoDB, prepare the DataFrame, and display elements here.
    ...

dashboard()
```

The decorator configures the fragment; the final `dashboard()` call executes it initially. Keep the MongoDB query inside the function so each refresh reads fresh records. A refresh only displays new records if the producer and consumer have written them to MongoDB.

### Optional interaction

A widget returns a Python value that you can use to filter the displayed data. Place this example after creating `df` inside your dashboard function:

```python
city = st.selectbox("Choose a city", sorted(df["city"].dropna().unique()))
selected = df[df["city"] == city]
st.dataframe(selected, hide_index=True)
```

Here, Streamlit collects the selection, pandas filters the rows, and Streamlit displays the filtered table. This changes the display; it does not change the documents stored in MongoDB.

### References

- [Streamlit API reference](https://docs.streamlit.io/develop/api-reference)
- [Line charts](https://docs.streamlit.io/develop/api-reference/charts/st.line_chart)
- [Bar charts](https://docs.streamlit.io/develop/api-reference/charts/st.bar_chart)
- [Fragments and automatic refresh](https://docs.streamlit.io/develop/api-reference/execution-flow/st.fragment)
