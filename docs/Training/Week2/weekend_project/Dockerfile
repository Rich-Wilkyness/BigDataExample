# A Dockerfile is an image recipe. This image contains the Python runtime, dependencies, and
# pipeline code. It does not contain PostgreSQL, the input CSV, database data, .env, or the report;
# Compose supplies those pieces when it creates containers from the image.
FROM python:3.12-slim

# WORKDIR sets the default directory used by later COPY, RUN, and CMD instructions.
WORKDIR /

# Copy the dependency list first so Docker can reuse the installed-dependency layer when only
# pipeline.py changes.
COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

# This COPY bakes the Python program into the image. The CSV is mounted later at runtime instead.
COPY pipeline.py .

# CMD is the default internal command when a pipeline container starts from this image.
CMD ["python", "pipeline.py"]
