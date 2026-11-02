
from pathlib import Path
import sys

import pandas as pd
import streamlit as st

APP_DIR = Path(__file__).resolve().parent.parent
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

from bedrock_sql import generate_sql, repair_sql, explain_results
from redshift_query import query_redshift

st.set_page_config(
    page_title="Citi Bike AI Chatbot",
    layout="wide",
)

st.title("Citi Bike AI Chatbot")
st.caption(
    "Ask a question, review the generated SQL, "
    "and approve execution against Redshift."
)

schema_path = APP_DIR / "redshift_schema.txt"

if not schema_path.exists():
    st.error("Redshift schema file is missing.")
    st.stop()

schema = schema_path.read_text(encoding="utf-8")

question = st.text_area(
    "Ask a question about Citi Bike data",
    placeholder=(
        "Which 10 stations have the lowest average "
        "number of available bikes?"
    ),
    height=100,
)

if st.button("Generate SQL", type="primary"):
    if not question.strip():
        st.warning("Enter a question first.")
    else:
        # Invalidate approval and results from previous queries.
        for key in (
            "generated_sql",
            "sql_question",
            "sql_usage",
            "query_result",
            "query_error",
            "explanation",
            "explanation_usage",
        ):
            st.session_state.pop(key, None)

        try:
            with st.spinner("Generating SQL with Bedrock..."):
                sql, usage = generate_sql(
                    question.strip(), schema
                )

            st.session_state["generated_sql"] = sql
            st.session_state["sql_editor"] = sql
            st.session_state["sql_question"] = question.strip()
            st.session_state["sql_usage"] = usage
            

        except Exception as exc:
            st.error(f"SQL generation failed: {exc}")


if "generated_sql" in st.session_state:
    st.subheader("Generated SQL")

    st.text_area(
        "Review or edit SQL",
        key="sql_editor",
        height=280,
    )

    current_sql = st.session_state["sql_editor"]

    col1, col2 = st.columns([1, 1])

    with col1:
        repair_clicked = st.button(
            "Repair SQL",
            disabled="query_error" not in st.session_state,
        )

    with col2:
        execute_clicked = st.button(
            "Query Redshift",
            type="primary",
        )

    if repair_clicked:
        try:
            with st.spinner("Repairing SQL with Bedrock..."):
                fixed_sql, usage = repair_sql(
                    st.session_state["sql_question"],
                    schema,
                    current_sql,
                    st.session_state["query_error"],
                )

            if fixed_sql == "INSUFFICIENT_SCHEMA":
                st.warning("The model could not repair this query.")
            else:
                st.session_state["sql_editor"] = fixed_sql
                st.session_state["generated_sql"] = fixed_sql
                st.session_state["sql_usage"] = usage
                for key in (
                    "query_error",
                    "query_result",
                    "explanation",
                    "explanation_usage",
                    "executed_sql",
                ):
                    st.session_state.pop(key, None)
                st.rerun()

        except Exception as exc:
            st.error(f"SQL repair failed: {exc}")

    if execute_clicked:
        # Never reuse results from an earlier approved query.
        for key in (
            "query_error",
            "query_result",
            "explanation",
            "explanation_usage",
            "executed_sql",
        ):
            st.session_state.pop(key, None)

        if (
            not current_sql.strip()
            or current_sql.strip() == "INSUFFICIENT_SCHEMA"
        ):
            st.warning("No valid SQL is available for approval.")
        else:
            try:
                with st.spinner("Executing approved SQL..."):
                    columns, rows = query_redshift(current_sql)

                st.session_state["executed_sql"] = current_sql
                st.session_state["query_result"] = {
                    "columns": columns,
                    "rows": rows,
                }

            except Exception as exc:
                st.session_state["query_error"] = str(exc)

    if "query_error" in st.session_state:
        st.error(st.session_state["query_error"])
        st.caption(
            "Correct the SQL manually, or click Repair SQL "
            "to ask Bedrock to fix the failed query."
        )

    # Only display results for the exact SQL that was executed.
    if (
        "query_result" in st.session_state
        and st.session_state.get("executed_sql") == current_sql
    ):
        result = st.session_state["query_result"]
        columns = result["columns"]
        rows = result["rows"]

        st.subheader("Redshift Results")

        df = pd.DataFrame(rows, columns=columns)
        st.dataframe(df, use_container_width=True, hide_index=True)
        st.caption(f"Returned {len(rows)} rows (maximum 200).")

        if "explanation" not in st.session_state:
            try:
                with st.spinner("Analyzing query results..."):
                    answer, usage = explain_results(
                        st.session_state["sql_question"],
                        st.session_state["executed_sql"],
                        columns,
                        rows,
                    )

                st.session_state["explanation"] = answer
                st.session_state["explanation_usage"] = usage

            except Exception as exc:
                st.error(f"Analysis failed: {exc}")

        if "explanation" in st.session_state:
            st.subheader("AI Answer")
            st.markdown(st.session_state["explanation"])

    sql_usage = st.session_state.get("sql_usage", {})
    explanation_usage = st.session_state.get(
        "explanation_usage", {}
    )

    if sql_usage or explanation_usage:
        st.divider()
        st.caption(
            "Bedrock token usage — "
            f"SQL generation: "
            f"{sql_usage.get('inputTokens', 0)} input / "
            f"{sql_usage.get('outputTokens', 0)} output; "
            f"Analysis: "
            f"{explanation_usage.get('inputTokens', 0)} input / "
            f"{explanation_usage.get('outputTokens', 0)} output."
        )
