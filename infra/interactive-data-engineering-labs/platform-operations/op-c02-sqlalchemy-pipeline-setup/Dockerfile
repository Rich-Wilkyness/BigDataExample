FROM python:3.12-slim

WORKDIR /app

RUN python -m pip install --no-cache-dir \
    "pandas>=2.2,<4" \
    "SQLAlchemy>=2.0,<3" \
    "psycopg[binary]>=3.2,<4"

COPY src/big_data_example ./big_data_example

CMD ["python", "-m", "big_data_example.labs.platform_operations.op_c02_sqlalchemy_pipeline_setup"]
