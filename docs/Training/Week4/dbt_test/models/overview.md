{% docs __overview__ %}
# Customer pipeline: PostgreSQL and dbt

This small project demonstrates a source declaration, model dependencies, data tests, and an analytical summary.

```text
bronze.customers (loaded outside dbt)
    → bronze_customers (view)
    → silver_customers (cleaned table, one row per customer)
    → gold_customer_summary (table, one summary row)
```

The raw source lives in the PostgreSQL `bronze` schema. Models are built in the profile's output schema, currently `dbt_dev`. The folders `models/bronze`, `models/silver`, and `models/gold` organize code; they do not create matching database schemas.

Silver requires unique, non-null customer IDs and non-null names. The custom `assert_customer_names_present` test also rejects empty or whitespace-only names. These tests report invalid data; they do not repair it or add database constraints.

The Gold count assumes one Silver row per customer. It records the count at build time and must be rebuilt to reflect changed Silver data. A count of zero is valid for an empty input and does not prove that ingestion was complete.
{% enddocs %}
