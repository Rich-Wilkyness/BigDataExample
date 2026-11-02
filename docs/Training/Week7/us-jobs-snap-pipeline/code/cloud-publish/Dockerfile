FROM python:3.12-slim-bookworm

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Shared staging utilities, merge rules and publication entrypoint.
COPY stage_refresh.py monthly_merge.py publish_refresh.py ./

USER 10001:10001

ENTRYPOINT ["python", "publish_refresh.py"]
