

## DBT
DAG - Not the same sense of DAG in Spark
- Spark is about stages, moving from one stage to the next in a lower level operation
- airflow DAG is high level and descriptive 
- dbt could be like medallion bronze -> silver -> gold
    - dbt itself doesn't know what these are, but if you design it that way, it works. these layers are not inherent to the structure.