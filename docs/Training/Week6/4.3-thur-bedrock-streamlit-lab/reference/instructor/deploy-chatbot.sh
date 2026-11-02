#!/usr/bin/env bash
set -euo pipefail

APP_DIR="$1"
SERVICE="$2"
S3="s3://citi-bike-nyc-pipeline/scripts/dashboard"

cd "$APP_DIR"

# Stage all files before modifying the running application.
STAGE=$(mktemp -d)
trap 'rm -rf "$STAGE"' EXIT
mkdir -p "$STAGE/pages"

aws s3 cp "$S3/app.py" "$STAGE/app.py" --region us-east-2
aws s3 cp "$S3/bedrock_sql.py" "$STAGE/bedrock_sql.py" --region us-east-2
aws s3 cp "$S3/redshift_schema.txt" "$STAGE/redshift_schema.txt" --region us-east-2
aws s3 cp "$S3/requirements.txt" "$STAGE/requirements.txt" --region us-east-2
aws s3 cp "$S3/pages/2_AI_SQL_Generator.py" \
  "$STAGE/pages/2_AI_SQL_Generator.py" --region us-east-2

# Verify Python syntax before deploying.
python3 -m py_compile \
  "$STAGE/app.py" \
  "$STAGE/bedrock_sql.py" \
  "$STAGE/pages/2_AI_SQL_Generator.py"

# Detect an existing virtual environment.
if [ -x "$APP_DIR/.venv/bin/python" ]; then
  PYTHON="$APP_DIR/.venv/bin/python"
elif [ -x "$APP_DIR/venv/bin/python" ]; then
  PYTHON="$APP_DIR/venv/bin/python"
else
  echo "No application virtual environment found; stopping."
  exit 1
fi

"$PYTHON" -m pip install -r "$STAGE/requirements.txt"

# Back up existing application files.
BACKUP="$APP_DIR/backup-$(date +%Y%m%d-%H%M%S)"
mkdir -p "$BACKUP"
for file in app.py bedrock_sql.py redshift_schema.txt requirements.txt; do
  if [ -f "$APP_DIR/$file" ]; then
    cp -p "$APP_DIR/$file" "$BACKUP/"
  fi
done
if [ -f "$APP_DIR/pages/2_AI_SQL_Generator.py" ]; then
  mkdir -p "$BACKUP/pages"
  cp -p "$APP_DIR/pages/2_AI_SQL_Generator.py" "$BACKUP/pages/"
fi

# Install application files.
mkdir -p "$APP_DIR/pages"
install -m 644 "$STAGE/app.py" "$APP_DIR/app.py"
install -m 644 "$STAGE/bedrock_sql.py" "$APP_DIR/bedrock_sql.py"
install -m 644 "$STAGE/redshift_schema.txt" "$APP_DIR/redshift_schema.txt"
install -m 644 "$STAGE/requirements.txt" "$APP_DIR/requirements.txt"
install -m 644 "$STAGE/pages/2_AI_SQL_Generator.py" \
  "$APP_DIR/pages/2_AI_SQL_Generator.py"

# Restart the existing Streamlit service.
systemctl restart "$SERVICE"
sleep 4
systemctl --no-pager --full status "$SERVICE"

echo "Deployment complete. Backup: $BACKUP"
