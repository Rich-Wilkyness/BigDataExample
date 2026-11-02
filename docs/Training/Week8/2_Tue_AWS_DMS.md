First we can break this up between Tue, Wed, or Thur files. This all happened over those days, but i really only took notes on things that stood out to me. It was mostly going over things we already covered with AWS or Azure, but with GCP and I already created a docs/Training/Week7/gcp-data-engineering-scope.md and docs/Training/Week7/gcp-resume-topic-reference.md. So it might be better to move those files to these days in some way, but not certain how to best break it up. 

GCP was not working for him today, so we are planning on using AWS DMS to transfer data from Azure to AWS. 
- this is similar to what he was trying to do with GCP STS

He actually got STS working for a different project, so he went over that
- He then went over differences of STS and DMS
    - DMS can take local postgres to S3
    - STS needs to turn the SQL format into parquet or avro


GCS bronze -> GCS silver
python bronze_to_silver.py \
    --input="$SAMPLE_URI" \
    --output="gs://$BUCKET/silver/station_information/stations" \
    --runner=DataflowRunner \
    --project="$PROJECT_ID" \
    --region="$REGION" \
    --temp_location="gs://$BUCKET/dataflow-temp/" \
    --???="gs://$BUCKET/dataflow-staging/" \
    --???="citibike-bronze-to-silver-$(date +%s)" \
    --worker_machine_type=e2-standard-2 \
    --num_workers=1 \
    --max_num_workers=1 \
    --save_main_session



runner vs dataflowrunner

save_main_session

- first serverless warehouse was BigQuery
GCS silver -> BigQuery Gold

```python
def run():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--table", required=True)

    args, pipeline_args = parser.parse_known_args()
    options = PipelineOptions(pipeline_args)

# each pipe creates a visual step in DataFlow console Job Graph
# this is essentially a DAG 
    with beam.Pipeline(options=options) as pipeline:
        (
            pipeline
            | "Read Silver" >> beam.io.ReadFromText(args.input)
            | "Parse Records" >> beam.Map(parse_station)
            | "Remove Invalid" >> beam.Filter(lambda x: x is not None)
            | "Key By Station" >> beam.Map(
                lambda x: (x["station_id"], x)
            )
            | "Latest Per Station" >> beam.CombinePerKey(
                lambda records: max(
                    records,
                    key=lambda r: r.get("source_last_updated") or 0
                )
            )
            | "Remove Keys" >> beam.Values()
            | "Write BigQuery Dimension" >> beam.io.WriteToBigQuery(
                table=args.table,
                schema=SCHEMA,
                method=beam.io.WriteToBigQuery.Method.FILE_LOADS,
                create_disposition=BigQueryDisposition.CREATE_NEVER,
                write_disposition=BigQueryDisposition.WRITE_TRUNCATE,
                custom_gcs_temp_location=None,
            )
        )
```

we talked about branching in beam, but suggested typically you wont have branching, he gave an example of writing the output to two different locations

probably would be good to have some basic pipe api notes 


```python
def run():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--table", required=True)

    args, pipeline_args = parser.parse_known_args()
    options = PipelineOptions(pipeline_args)

# each pipe creates a visual step in DataFlow console Job Graph
# this is essentially a DAG 
    with beam.Pipeline(options=options) as pipeline:
        (
            pipeline
            | "Read Silver" >> beam.io.ReadFromText(args.input)
            | "Transform Fact" >> beam.Map(transform)
            | "Key Snapshot" >> beam.Map(
                lambda row: (
                    (
                        row["station_id"],
                        row["snapshot_timestamp"]
                    ),
                    row
                )
            )
            | "Deduplicate Snapshots" >> beam.CombinePerKey(
                choose_snapshot
            )
            | "Remove Keys" >> beam.Values()
            | "Write BigQuery Dimension" >> beam.io.WriteToBigQuery(
                table=args.table,
                schema=SCHEMA,
                method=beam.io.WriteToBigQuery.Method.FILE_LOADS,
                create_disposition=BigQueryDisposition.CREATE_NEVER,
                write_disposition=BigQueryDisposition.WRITE_TRUNCATE,
                custom_gcs_temp_location=None,
            )
        )
```

we talked about the use of snapshot keys, keys are always pairs and the first value is treated as the key, the second as the value, but not sure why we added it here.