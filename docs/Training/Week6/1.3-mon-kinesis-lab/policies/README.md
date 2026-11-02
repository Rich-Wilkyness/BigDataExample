# Policy templates and identities

These are identity permissions templates, not deployed policies, provisioning permissions, or trust policies. Replace every `__PLACEHOLDER__` with the exact dedicated lab resource before review/use. Keep rendered account-specific copies in your scratch directory.

## Read the shared policy structure first

- `Version`: IAM policy language version, not a version number for your application.
- `Statement`: The list of permission rules. Each statement describes one purpose.
- `Sid`: A readable statement label. It helps you locate a rule; it does not grant permission by itself.
- `Effect = Allow`: This statement grants the listed actions within its scope. Other applicable policies and explicit denies still affect the final decision.
- `Action`: The API permissions the identity may use.
- `Resource`: The exact AWS resource boundary where those actions apply.
- `Condition`: An additional requirement, such as the S3 prefix allowed for listing.

Standard JSON cannot contain comments. Use the sections below as the commentary for each file; keep the deployable JSON free of extra explanatory keys.

## producer-permissions.template.json — publish events

[Open the file](producer-permissions.template.json). Its single statement allows `kinesis:PutRecord` for the first manual exercise and `kinesis:PutRecords` for the batched producer. Both are scoped to `__STREAM_ARN__` so permission to publish to the lab stream does not automatically grant publication to every stream.

Attach reviewed permissions to the publishing identity. This file does not grant stream creation/deletion, reads, IAM role changes, or S3 delivery. It illustrates the producer's responsibility at the ingestion boundary.

## reader-permissions.template.json — inspect the stream and archive

[Open the file](reader-permissions.template.json). Read its statements as **stream inspection → bucket listing → object reading**.

- `InspectDedicatedStream`: Describes the stream/shards and reads records. The stream ARN scopes those operations to the dedicated source.
- `ListBronzeArchive`: Lists objects in the bucket, with an `s3:prefix` condition limiting the requested listing to `bronze/station-status/`. Listing is a bucket operation, so its resource is the bucket ARN.
- `ReadBronzeArchive`: Downloads object content under the same prefix. Reading is an object operation, so its resource includes the object path and wildcard.

These statements are separate because seeing an object name and reading its content are different permissions. This identity cannot publish stream events or write archive objects using this template alone.

## firehose-permissions.template.json — read the source and deliver files

[Open the file](firehose-permissions.template.json). Read its statements as **source reads → bucket metadata → object delivery → error logging**.

- `ReadDedicatedSource`: Lets Firehose read the Kinesis records that it will deliver.
- `ArchiveBucketMetadata`: Supplies the bucket-level location/listing/multipart-discovery permissions required by this delivery setup.
- `WriteDedicatedArchiveAndErrors`: Supplies the documented object operations within the archive and error prefixes. `AbortMultipartUpload` supports cleanup of an interrupted multipart upload; it is different from deleting a completed object.
- `DeliveryErrorLogging`: Writes diagnostic events to the exact configured log stream so failed delivery can be investigated.

Attach these permissions to the Firehose service role, not to the producer. The console-created role also needs separate service trust so Firehose can assume it; inspect that trust and retain appropriate service-supported confused-deputy conditions. An identity permissions document alone cannot make a service assume a role.

## Replace placeholders before reviewing a concrete policy

The templates follow the [Kinesis authorization reference](https://docs.aws.amazon.com/service-authorization/latest/reference/list_kinesis.html) and [Firehose S3 role example](https://docs.aws.amazon.com/firehose/latest/dev/controlling-access.html), reviewed 2026-10-12. Bucket and object permissions are separated to make their different resource boundaries visible. No policy is attached by any script in this directory.

`__STREAM_ARN__` is the dedicated Kinesis stream ARN. `__BUCKET_NAME__` is a bucket name, not an ARN or URL. `__FIREHOSE_LOG_STREAM_ARN__` is the exact existing log-stream ARN configured for delivery errors. The Firehose console can provision logging resources; the data-plane template does not grant permission to create them.

## Assumptions and verification limits

These templates assume same-account resources and the lab's default S3 encryption configuration. Customer-managed KMS encryption needs separately scoped key access and compatible key policies. Provisioning, console discovery, IAM role creation/pass-role, cross-account access, and organization restrictions require separate review. JSON parsing is not proof that IAM will authorize a live request.
