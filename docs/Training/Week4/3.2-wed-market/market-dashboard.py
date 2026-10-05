import json
from pathlib import Path

import pandas as pd
import streamlit as st


# ============================================================
# CONFIG
# ============================================================

SPARK_FILE = Path("/tmp/spark-market.jsonl")
FLINK_FILE = Path("/tmp/flink-market.jsonl")

MAX_EVENTS = 15000

MARKET_WINDOW_SECONDS = 30
PROCESS_WINDOW_SECONDS = 12

# 100 ms buckets
BUCKET_MS = 100


# ============================================================
# PAGE
# ============================================================

st.set_page_config(
    page_title="Streaming Engine Race",
    page_icon="📈",
    layout="wide"
)


st.markdown(
    """
    <style>

    .stApp {
        background:
            radial-gradient(
                circle at 10% 5%,
                rgba(40,100,180,.08),
                transparent 30%
            ),
            radial-gradient(
                circle at 90% 5%,
                rgba(130,70,150,.06),
                transparent 30%
            );
    }

    .hero {
        padding: 1.3rem 1.5rem;
        border: 1px solid rgba(130,130,130,.2);
        border-radius: 16px;
        margin-bottom: 1rem;
    }

    .hero h1 {
        margin: 0;
    }

    .hero p {
        opacity: .7;
        margin-bottom: 0;
    }

    .engine-box {
        border: 1px solid rgba(130,130,130,.2);
        border-radius: 14px;
        padding: 1rem 1.2rem;
        margin-bottom: .5rem;
    }

    .big-label {
        font-size: 1.4rem;
        font-weight: 700;
    }

    </style>
    """,
    unsafe_allow_html=True
)


# ============================================================
# LOAD JSONL
# ============================================================

def load_jsonl(path):

    if not path.exists():
        return pd.DataFrame()

    try:

        with path.open() as f:
            lines = f.readlines()[-MAX_EVENTS:]

    except Exception:
        return pd.DataFrame()

    records = []

    for line in lines:

        try:
            records.append(
                json.loads(line)
            )

        except json.JSONDecodeError:
            continue

    if not records:
        return pd.DataFrame()

    return pd.DataFrame(records)


# ============================================================
# PREPARE
# ============================================================

def prepare(df, engine):

    if df.empty:
        return df

    df = df.copy()

    df["engine"] = engine

    for column in [
        "exchange_ts",
        "api_ts",
        "kafka_ts",
        "processed_ts"
    ]:

        if column in df.columns:

            df[column] = pd.to_datetime(
                df[column],
                utc=True,
                errors="coerce"
            )

    for column in [
        "sequence",
        "price",
        "size",
        "batch_id",
        "processing_latency_ms",
        "end_to_end_latency_ms"
    ]:

        if column in df.columns:

            df[column] = pd.to_numeric(
                df[column],
                errors="coerce"
            )

    return df


# ============================================================
# OWN RELATIVE TIMELINE FOR EACH ENGINE
# ============================================================

def engine_histogram(df):

    """
    Build a histogram relative to THIS ENGINE'S
    newest processed event.

    This is critical.

    Spark and Flink are deliberately NOT aligned
    using one common newest timestamp.
    """

    if (
        df.empty
        or
        "processed_ts" not in df
    ):
        return pd.Series(dtype=float)

    clean = (
        df
        .dropna(
            subset=["processed_ts"]
        )
        .copy()
    )

    if clean.empty:
        return pd.Series(dtype=float)

    # --------------------------------------------------------
    # THIS ENGINE'S OWN "NOW"
    # --------------------------------------------------------

    engine_now = (
        clean["processed_ts"].max()
    )

    start = (
        engine_now
        -
        pd.Timedelta(
            seconds=PROCESS_WINDOW_SECONDS
        )
    )

    recent = (
        clean[
            clean["processed_ts"]
            >= start
        ]
        .copy()
    )

    if recent.empty:
        return pd.Series(dtype=float)

    # --------------------------------------------------------
    # Convert every event into milliseconds before THIS
    # engine's latest event.
    #
    # Example:
    #
    # -11.9
    # -11.8
    # ...
    # -2.0
    # -1.9
    # ...
    # 0
    # --------------------------------------------------------

    recent["relative_seconds"] = (
        (
            recent["processed_ts"]
            -
            engine_now
        )
        .dt.total_seconds()
    )

    # --------------------------------------------------------
    # Quantize into 100ms buckets
    # --------------------------------------------------------

    recent["bucket_number"] = (
        (
            recent["relative_seconds"]
            * 1000
        )
        /
        BUCKET_MS
    ).round().astype(int)

    counts = (
        recent
        .groupby("bucket_number")
        .size()
    )

    # --------------------------------------------------------
    # Create EVERY possible bucket.
    # --------------------------------------------------------

    bucket_count = int(
        PROCESS_WINDOW_SECONDS
        * 1000
        /
        BUCKET_MS
    )

    all_buckets = range(
        -bucket_count,
        1
    )

    counts = counts.reindex(
        all_buckets,
        fill_value=0
    )

    # Convert bucket IDs back to seconds.

    counts.index = [
        round(
            bucket
            * BUCKET_MS
            / 1000,
            1
        )
        for bucket in counts.index
    ]

    counts.index.name = (
        "Seconds before latest engine output"
    )

    return counts


# ============================================================
# LATENCY
# ============================================================

def latency_stats(df):

    if (
        df.empty
        or
        "processing_latency_ms" not in df
    ):
        return None

    values = (
        df["processing_latency_ms"]
        .dropna()
        .tail(2000)
    )

    if values.empty:
        return None

    return {
        "avg": values.mean(),
        "median": values.median(),
        "p95": values.quantile(.95),
        "max": values.max()
    }


# ============================================================
# DASHBOARD
# ============================================================

@st.fragment(run_every="250ms")
def dashboard():

    spark = prepare(
        load_jsonl(SPARK_FILE),
        "Spark"
    )

    flink = prepare(
        load_jsonl(FLINK_FILE),
        "Flink"
    )


    # ========================================================
    # HEADER
    # ========================================================

    st.markdown(
        """
        <div class="hero">

        <h1>Real-Time Market Streaming Lab</h1>

        <p>
        Synthetic Exchange → REST API → Kafka →
        Spark Structured Streaming + Apache Flink
        </p>

        </div>
        """,
        unsafe_allow_html=True
    )


    if spark.empty and flink.empty:

        st.warning(
            "Waiting for streaming data..."
        )

        return


    # ========================================================
    # LIVE MARKET
    # ========================================================

    st.header(
        "Live Simulated Market"
    )

    st.caption(
        "30-second rolling market view"
    )


    market = (
        flink.copy()
        if not flink.empty
        else spark.copy()
    )


    if (
        not market.empty
        and
        "exchange_ts" in market
    ):

        market = (
            market
            .dropna(
                subset=[
                    "exchange_ts",
                    "symbol",
                    "price"
                ]
            )
            .sort_values(
                "exchange_ts"
            )
        )


        if not market.empty:

            newest = (
                market[
                    "exchange_ts"
                ].max()
            )


            market = market[
                market["exchange_ts"]
                >=
                newest
                -
                pd.Timedelta(
                    seconds=
                    MARKET_WINDOW_SECONDS
                )
            ]


            # =================================================
            # CURRENT PRICES
            # =================================================

            latest = (
                market
                .sort_values(
                    "sequence"
                )
                .groupby(
                    "symbol"
                )
                .tail(1)
                .sort_values(
                    "symbol"
                )
            )


            symbols = list(
                latest["symbol"]
            )


            if symbols:

                cols = st.columns(
                    len(symbols)
                )


                for column, symbol in zip(
                    cols,
                    symbols
                ):

                    row = (
                        latest[
                            latest[
                                "symbol"
                            ] == symbol
                        ]
                        .iloc[-1]
                    )


                    history = (
                        market[
                            market[
                                "symbol"
                            ] == symbol
                        ]
                        .sort_values(
                            "exchange_ts"
                        )
                    )


                    if len(history) > 1:

                        delta = (
                            row["price"]
                            -
                            history.iloc[0][
                                "price"
                            ]
                        )

                    else:

                        delta = 0


                    column.metric(
                        symbol,
                        f"${row['price']:,.2f}",
                        f"{delta:+.2f}"
                    )


            # =================================================
            # PRICE CHART
            # =================================================

            prices = (
                market
                .pivot_table(
                    index="exchange_ts",
                    columns="symbol",
                    values="price",
                    aggfunc="last"
                )
                .sort_index()
                .ffill()
            )


            if not prices.empty:

                base = (
                    prices
                    .bfill()
                    .iloc[0]
                )


                normalized = (
                    (
                        prices / base
                    )
                    - 1
                ) * 100


                st.line_chart(
                    normalized,
                    height=400,
                    x_label="Market time",
                    y_label="Price change (%)"
                )


    # ========================================================
    # MAIN DEMONSTRATION
    # ========================================================

    st.divider()

    st.header(
        "Same Kafka Feed — Two Processing Models"
    )


    st.markdown(
        """
        Both applications are consuming the **same stream of
        market events**.

        The charts below answer one question:

        **How many events did the application process during
        each 100 ms interval?**
        """
    )


    # ========================================================
    # CREATE HISTOGRAMS
    # ========================================================

    flink_hist = engine_histogram(
        flink
    )

    spark_hist = engine_histogram(
        spark
    )


    # ========================================================
    # SIDE-BY-SIDE
    # ========================================================

    left, right = st.columns(2)


    # --------------------------------------------------------
    # FLINK
    # --------------------------------------------------------

    with left:

        st.markdown(
            """
            <div class="engine-box">

            <div class="big-label">
            Apache Flink
            </div>

            Continuous record processing

            </div>
            """,
            unsafe_allow_html=True
        )


        if not flink_hist.empty:

            st.bar_chart(
                flink_hist,
                height=350,
                x_label=(
                    "Seconds before latest output"
                ),
                y_label=(
                    "Events / 100 ms"
                )
            )


            flink_active = (
                flink_hist > 0
            ).sum()


            st.metric(
                "Active 100 ms intervals",
                flink_active
            )


    # --------------------------------------------------------
    # SPARK
    # --------------------------------------------------------

    with right:

        st.markdown(
            """
            <div class="engine-box">

            <div class="big-label">
            Spark Structured Streaming
            </div>

            2-second microbatch trigger

            </div>
            """,
            unsafe_allow_html=True
        )


        if not spark_hist.empty:

            st.bar_chart(
                spark_hist,
                height=350,
                x_label=(
                    "Seconds before latest output"
                ),
                y_label=(
                    "Events / 100 ms"
                )
            )


            spark_active = (
                spark_hist > 0
            ).sum()


            st.metric(
                "Active 100 ms intervals",
                spark_active
            )


    # ========================================================
    # INTERPRETATION
    # ========================================================

    st.info(
        """
        **Read these charts from left to right.**

        If an engine is processing records continuously,
        activity should be distributed across many time buckets.

        If an engine is processing microbatches, activity should
        be concentrated into large periodic spikes separated by
        quiet periods.

        Each chart uses that engine's **own latest output as
        time zero**, so neither engine can disappear simply
        because one is currently ahead of the other.
        """
    )


    # ========================================================
    # SPARK BATCH INSPECTOR
    # ========================================================

    st.header(
        "Spark Microbatches"
    )


    if (
        not spark.empty
        and
        "batch_id" in spark
    ):

        valid = (
            spark
            .dropna(
                subset=[
                    "batch_id",
                    "sequence",
                    "processed_ts"
                ]
            )
        )


        if not valid.empty:

            batches = (
                valid
                .groupby(
                    "batch_id"
                )
                .agg(
                    Events=(
                        "sequence",
                        "count"
                    ),
                    First_sequence=(
                        "sequence",
                        "min"
                    ),
                    Last_sequence=(
                        "sequence",
                        "max"
                    ),
                    Processed_at=(
                        "processed_ts",
                        "max"
                    ),
                    Avg_latency_ms=(
                        "processing_latency_ms",
                        "mean"
                    )
                )
                .reset_index()
                .sort_values(
                    "batch_id",
                    ascending=False
                )
                .head(12)
            )


            # ------------------------------------------------
            # Batch chart
            # ------------------------------------------------

            batch_sizes = (
                batches
                .sort_values(
                    "batch_id"
                )
                .set_index(
                    "batch_id"
                )
                ["Events"]
            )


            st.bar_chart(
                batch_sizes,
                height=280,
                x_label="Microbatch ID",
                y_label="Events processed"
            )


            st.dataframe(
                batches,
                use_container_width=True,
                hide_index=True
            )


    # ========================================================
    # LATENCY SUMMARY
    # ========================================================

    st.divider()

    st.header(
        "Processing Latency"
    )


    spark_stats = latency_stats(
        spark
    )

    flink_stats = latency_stats(
        flink
    )


    rows = []


    if spark_stats:

        rows.append({

            "Engine":
                "Spark",

            "Average (ms)":
                round(
                    spark_stats["avg"],
                    1
                ),

            "Median (ms)":
                round(
                    spark_stats["median"],
                    1
                ),

            "P95 (ms)":
                round(
                    spark_stats["p95"],
                    1
                ),

            "Maximum (ms)":
                round(
                    spark_stats["max"],
                    1
                )
        })


    if flink_stats:

        rows.append({

            "Engine":
                "Flink",

            "Average (ms)":
                round(
                    flink_stats["avg"],
                    1
                ),

            "Median (ms)":
                round(
                    flink_stats["median"],
                    1
                ),

            "P95 (ms)":
                round(
                    flink_stats["p95"],
                    1
                ),

            "Maximum (ms)":
                round(
                    flink_stats["max"],
                    1
                )
        })


    if rows:

        st.dataframe(
            pd.DataFrame(rows),
            use_container_width=True,
            hide_index=True
        )


    # ========================================================
    # SAME EVENT TABLE
    # ========================================================

    st.header(
        "Same Events Through Both Engines"
    )


    if (
        not spark.empty
        and
        not flink.empty
    ):

        spark_side = (
            spark[
                [
                    "sequence",
                    "symbol",
                    "price",
                    "processed_ts",
                    "processing_latency_ms",
                    "batch_id"
                ]
            ]
            .rename(
                columns={

                    "processed_ts":
                        "Spark processed",

                    "processing_latency_ms":
                        "Spark latency",

                    "batch_id":
                        "Spark batch"
                }
            )
        )


        flink_side = (
            flink[
                [
                    "sequence",
                    "processed_ts",
                    "processing_latency_ms"
                ]
            ]
            .rename(
                columns={

                    "processed_ts":
                        "Flink processed",

                    "processing_latency_ms":
                        "Flink latency"
                }
            )
        )


        matched = (
            spark_side
            .merge(
                flink_side,
                on="sequence",
                how="inner"
            )
            .sort_values(
                "sequence",
                ascending=False
            )
            .head(20)
        )


        if not matched.empty:

            st.dataframe(
                matched,
                use_container_width=True,
                hide_index=True
            )


    # ========================================================
    # EXPLANATION
    # ========================================================

    with st.expander(
        "What this demonstration is showing"
    ):

        st.markdown(
            """
### Flink

Conceptually:

`event → process`

`event → process`

`event → process`

Records flow independently through the streaming operators.

### Spark Structured Streaming

For this lab we deliberately configured a two-second trigger:

`events arrive → events accumulate → microbatch executes`

Then the process repeats.

The batch inspector provides another direct view of those
boundaries because every Spark event carries its `batch_id`.

### Trading relevance

For latency-sensitive applications, the time between an event
becoming available and the application reacting to it can matter.

A market may move several times while an older observation is
waiting to be processed.

### Important

This is an educational visualization of processing models,
not a performance benchmark.

The REST API, Python processes, JSONL files and Streamlit
dashboard introduce substantial latency of their own and would
not belong in the critical path of a real HFT system.
        """
        )


dashboard()
