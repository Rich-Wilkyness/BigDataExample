
import time

import boto3
from sqlglot import exp, parse

REGION = "us-east-2"
DATABASE = "dev"
WORKGROUP = "citibike-wg"

MAX_ROWS = 200
TIMEOUT_SECONDS = 90

client = boto3.client("redshift-data", region_name=REGION)


def validate_sql(sql):
    statements = parse(sql, read="redshift")

    if len(statements) != 1 or statements[0] is None:
        raise ValueError("Exactly one SQL statement is required.")

    tree = statements[0]

    if not isinstance(tree, (exp.Select, exp.Union)):
        raise ValueError("Only SELECT queries are permitted.")

    forbidden = (
        exp.Insert,
        exp.Update,
        exp.Delete,
        exp.Drop,
        exp.Create,
        exp.Alter,
        exp.Command,
        exp.Into,
    )

    if any(tree.find(node_type) for node_type in forbidden):
        raise ValueError("SQL contains a prohibited operation.")

    # This is defense in depth, not a database security boundary.
    return tree.sql(dialect="redshift")


def convert_field(field):
    if field.get("isNull"):
        return None

    for key in (
        "stringValue",
        "longValue",
        "doubleValue",
        "booleanValue",
    ):
        if key in field:
            return field[key]

    return None


def query_redshift(sql):
    safe_sql = validate_sql(sql)

    # Bound the number of rows returned to the application.
    bounded_sql = (
        "SELECT * FROM (\n"
        + safe_sql.rstrip(";")
        + f"\n) AS approved_query LIMIT {MAX_ROWS}"
    )

    response = client.execute_statement(
        WorkgroupName=WORKGROUP,
        Database=DATABASE,
        Sql=bounded_sql,
    )

    statement_id = response["Id"]
    deadline = time.monotonic() + TIMEOUT_SECONDS

    while time.monotonic() < deadline:
        status = client.describe_statement(Id=statement_id)
        state = status["Status"]

        if state == "FINISHED":
            break

        if state in ("FAILED", "ABORTED"):
            raise RuntimeError(
                status.get("Error", "Redshift query failed.")
            )

        time.sleep(1)
    else:
        # Best effort: cancel an overdue query.
        try:
            client.cancel_statement(Id=statement_id)
        except Exception:
            pass

        raise TimeoutError("Redshift query timed out.")

    if not status.get("HasResultSet", False):
        return [], []

    columns = []
    rows = []
    next_token = None

    while len(rows) < MAX_ROWS:
        params = {"Id": statement_id}
        if next_token:
            params["NextToken"] = next_token

        page = client.get_statement_result(**params)

        if not columns:
            columns = [
                col.get("label") or col["name"]
                for col in page["ColumnMetadata"]
            ]

        for record in page["Records"]:
            rows.append([convert_field(v) for v in record])

            if len(rows) >= MAX_ROWS:
                break

        next_token = page.get("NextToken")
        if not next_token:
            break

    return columns, rows
