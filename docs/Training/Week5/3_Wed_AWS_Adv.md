> Organized walkthrough: [Citi Bike AWS Bronze → Silver steps](3.2-wed-citibike-steps.md). Use the walkthrough for consistent configuration and corrected instructions; the rough lecture capture below is preserved. AWS execution remains pending permissions.



# Lecture Notes
our company AWS sign in:
https://enhanceit.signin.aws.amazon.com/console
- we use our company email for the username
- richard.wilkerson@techconsulting.tech                   

## his plan for a project

using NYC public biking data

batch ELT pipeline:

ingest into S3

Process it with a Spark job on EMR Serverless

Output to a Data Warehouse on Redshift Serverless

bonus:
Streamlit app for visualization hosted on ECS/Fargate

or 
Alternative visual tool: AWS Quicksight
- might not use due to cost



## Quicksight
- competitor to Tableau and Power BI
- Those are call business intelligence tools - basically for data visualization


## ECS
Elastic Container Service
- The containers that it's talking about are Docker containers
- alternative to EC2, you can still use docker container on EC2, but ECS is more lightweight and lower cost


## Fargate
- essentially serverless ECS
- Effectively what it means is that the container is hosted and available to be accessed by the public - but if no one is accessing it, then there is no cost to you


## AWS CLI Authentication

- `aws --version`
    - can install using apt or pip

curl -fsSL https://awscli.amazonaws.com/v2/install.sh | bash

pip install awscli --upgrade --user


```bash
# bashrc file
# Placeholder for company aws account passwords
export AWS_ACCESS_KEY_ID=""
export AWS_SECRET_ACCESS_KEY=""
export AWS_DEFAULT_REGION="us-west-1"
```

- AWS requires region

use `source file` to refresh the passwords added

- extract Access key id and scret access key from IAM
    - might need to create an access key
        - define it is for the CLI
        - note you cannot reaccess the access key info, you can download the csv with the info, which should be placed in a secure location

- aws configure --profile company
    - fill in the info
    - json


- this is useful for many reasons
    - more control over EC2 and other environments that only have CLI and no GUI


## setup for our project

### Get s3 bucket
aws s3api create-bucket \
--bucket citi-bike-nyc-pipeline \
--region us-west-1 \
--create-bucket-configuration LocationConstraint=us-east-2 \
--profile company
- these are required to create a bucket
- profile says where to find the auth credentials

s3 buckets are global, so you cannot name the bucket something that someone else has named it (in or out of the company)

- remove block all public access
    - makes it difficult for education reasons as it puts more layers of auth required

### get access to data on s3

```python
# ingestion_check.py
import json
# can use import requests as well
import urllib.request
from datetime import datetime, timezone


GBFS_URL = "https://gbfs.citibikenyc.com/gbfs/gbfs.json"

WANTED_FEEDS = {
    "station_information",
    "station_status",
    "system_information"
}


def get_json(url):
    print(f"GET {url}")

    with urllib.request.urlopen(url, timeout=30) as response:
        return json.loads(response.read())


# ---------------------------------------------------------
# 1. Read the GBFS discovery document
# ---------------------------------------------------------

gbfs = get_json(GBFS_URL)

feeds = gbfs["data"]["en"]["feeds"]


# ---------------------------------------------------------
# 2. Find the feeds we care about
# ---------------------------------------------------------

feed_urls = {}

for feed in feeds:
    if feed["name"] in WANTED_FEEDS:
        feed_urls[feed["name"]] = feed["url"]


print("\nFeeds discovered:")

for name, url in feed_urls.items():
    print(f"{name}: {url}")


# ---------------------------------------------------------
# 3. Download each feed
# ---------------------------------------------------------

datasets = {}

for name, url in feed_urls.items():
    datasets[name] = get_json(url)


# ---------------------------------------------------------
# 4. Inspect station information
# ---------------------------------------------------------

station_info = datasets["station_information"]["data"]["stations"]

print("\n" + "=" * 70)
print("STATION INFORMATION")
print("=" * 70)

print(f"Stations: {len(station_info)}")

for station in station_info[:3]:
    print(json.dumps(station, indent=2))
    print("-" * 50)


# ---------------------------------------------------------
# 5. Inspect current station status
# ---------------------------------------------------------

station_status = datasets["station_status"]["data"]["stations"]

print("\n" + "=" * 70)
print("STATION STATUS")
print("=" * 70)

print(f"Station status records: {len(station_status)}")

for station in station_status[:3]:
    print(json.dumps(station, indent=2))
    print("-" * 50)


# ---------------------------------------------------------
# 6. Inspect system information
# ---------------------------------------------------------

system_info = datasets["system_information"]["data"]

print("\n" + "=" * 70)
print("SYSTEM INFORMATION")
print("=" * 70)

print(json.dumps(system_info, indent=2))


# ---------------------------------------------------------
# 7. Basic validation
# ---------------------------------------------------------

info_ids = {
    station["station_id"]
    for station in station_info
}

status_ids = {
    station["station_id"]
    for station in station_status
}

print("\n" + "=" * 70)
print("VALIDATION")
print("=" * 70)

print(f"Station information IDs: {len(info_ids)}")
print(f"Station status IDs:      {len(status_ids)}")

print(
    f"Status stations missing metadata: "
    f"{len(status_ids - info_ids)}"
)

print(
    f"Metadata stations missing status: "
    f"{len(info_ids - status_ids)}"
)

print(
    f"Snapshot time: "
    f"{datetime.now(timezone.utc).isoformat()}"
)

```




```python
# injestion_to_s3.py
import json
import urllib.request
from datetime import datetime, timezone

import boto3


# =========================================================
# CONFIGURATION
# =========================================================

GBFS_URL = "https://gbfs.citibikenyc.com/gbfs/gbfs.json"

BUCKET = "citi-bike-nyc"

AWS_PROFILE = "company"

AWS_REGION = "us-east-2"

WANTED_FEEDS = {
    "station_information",
    "station_status",
    "system_information"
}


# =========================================================
# HTTP
# =========================================================

def get_json(url):

    print(f"Downloading: {url}")

    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": "NYC-DOT-DataEngineering-Demo/1.0"
        }
    )

    with urllib.request.urlopen(
        request,
        timeout=30
    ) as response:

        raw = response.read()

    return json.loads(raw)


# =========================================================
# AWS
# =========================================================

session = boto3.Session(
    profile_name=AWS_PROFILE,
    region_name=AWS_REGION
)

s3 = session.client("s3")


# =========================================================
# S3 WRITE
# =========================================================

def write_json_to_s3(dataset_name, data, snapshot_time):

    key = (
        f"bronze/citibike/{dataset_name}/"
        f"year={snapshot_time:%Y}/"
        f"month={snapshot_time:%m}/"
        f"day={snapshot_time:%d}/"
        f"hour={snapshot_time:%H}/"
        f"{dataset_name}_{snapshot_time:%Y%m%dT%H%M%SZ}.json"
    )

    body = json.dumps(
        data,
        separators=(",", ":")
    ).encode("utf-8")

    s3.put_object(
        Bucket=BUCKET,
        Key=key,
        Body=body,
        ContentType="application/json"
    )

    print(
        f"Uploaded {len(body):,} bytes -> "
        f"s3://{BUCKET}/{key}"
    )

    return key


# =========================================================
# MAIN INGESTION
# =========================================================

def main():

    snapshot_time = datetime.now(timezone.utc)

    print("=" * 70)
    print("CITI BIKE INGESTION")
    print("=" * 70)

    print(f"Snapshot: {snapshot_time.isoformat()}")
    print(f"Bucket:   {BUCKET}")
    print()


    # -----------------------------------------------------
    # Discover feeds
    # -----------------------------------------------------

    discovery = get_json(GBFS_URL)

    feeds = discovery["data"]["en"]["feeds"]

    feed_urls = {}

    for feed in feeds:

        name = feed["name"]

        if name in WANTED_FEEDS:
            feed_urls[name] = feed["url"]


    # -----------------------------------------------------
    # Validate discovery
    # -----------------------------------------------------

    missing = WANTED_FEEDS - set(feed_urls)

    if missing:
        raise RuntimeError(
            f"Missing expected feeds: {missing}"
        )


    # -----------------------------------------------------
    # Save discovery document itself
    # -----------------------------------------------------

    write_json_to_s3(
        "gbfs_discovery",
        discovery,
        snapshot_time
    )


    # -----------------------------------------------------
    # Download + store each feed
    # -----------------------------------------------------

    uploaded = []

    for dataset_name, url in feed_urls.items():

        print()
        print(f"Processing {dataset_name}")

        data = get_json(url)

        key = write_json_to_s3(
            dataset_name,
            data,
            snapshot_time
        )

        uploaded.append(key)


    # -----------------------------------------------------
    # Summary
    # -----------------------------------------------------

    print()
    print("=" * 70)
    print("INGESTION COMPLETE")
    print("=" * 70)

    print(f"Files uploaded: {len(uploaded) + 1}")

    for key in uploaded:
        print(f"  {key}")


if __name__ == "__main__":
    main()

```


refresh s3
- will see the bronze directory
- if we navigate all the way to the file and click, you'll notice we don't see our data, we have s3 uri, ARN, etag, and object URL
    - there is an open button in the top right that opens a new tab in the browser


aws s3 ls s3://citi-bike-nyc-pipeline/bronze/citibike/ \
    -- recursive \
    --profile company


### now we will use an EventBridge with Lambda

mkdir -p ~/citibike-lambda
cd ~/citibike-lambda
- this is not required, it is just to create the place where he put it, we'll have ours in our Week5/AWS-citibike (or whatever name you want)
```python
# ingestion_lambda_function.py

# imports boto3
# - this might create issues in the AWS environment because it is a dependency that locally python knows where it is, but AWS does not, we'll need to create a VM, zip it, put it in S3, then have lambda look at that S3. 
#   - i didn't really follow this, but ok...

```


create IAM trust policy
- teacher is not certain this is required, so he'll move forward without it unless AWS requires it
```json
// lambda-trust-policy.json

```


give lambda cloudwatch logging permission
- how we use logs/monitoring in AWS
- very important for diagnosing problems


many more permissions come up, but he's skipping for now
aws iam create-role \ 
--role-name CitiBikeLambdaRole \
--assume-role-policy-document file://lambda-trust-policy.json \
--profile company
{
    "Role": {
        Path
        RoleName
        RoleId
        Arn
        CreateDate
        AssumeRolePolicyDocument{
            Version
            Statement {
                Effect
                Principal {
                    Service
                },
                Action
            }
        }
    }
}

aws iam attach-role-policy \
--role-name
--policy-arn
--profile company

provide write policy 
aws iam create-policy \
--

ACCOUNT_ID=$(aws sts get-caller-identity \
--profile company
--query Account
--output text)

echo $ACCOUNT_ID

aws iam attach-role-policy \
--role-name
-policy-arn
--profile company

zip lambda.zip lambda_function.py
- we can add dependencies in subdirectories of the zip, like for bolo3

get the IAM role ARN so we can pass it to the lambda

LAMDA_ROLE_ARN=$(aws iam get-role \
)

create lambda
aws lambda create
--function-name
--runtime
--role
--handler
--zip-file
--timeout
--memory-size
--region us-east-2
--profile company


we can then refresh the AWS lambda, find our zip
- we can now make changes to this script on the website gui


manually invoke lambda cli or gui
aws lambda invoke \
--function-name
--payload
--region us-east-2
--profile company
<output file location>

output was to our local directory

check cloudwatch
aws
/aws/

- short asside, logging best practices
    - cloudwatch does use print statements, there are others python libraries that exist, but not required, he uses print most of the time
    - try, except are not required to get the error in the logs, but will help gracefully fail


scheduling lambda functions eventbridge
- using the gui console -> click add trigger (above "code") -> source = EventBridge (cloudwatch or scheduler) scheduler is legacy and what we used in class -> create new rule -> created a rate-based schedule every 5 mins
payload = {}
use existing role = CitiBikeLambdaRole

CitiBikeLambdaRole did not work for the scheduler
need to create a separate scheduler trust policy
```json
// provide role for scheduler
```
- select the new role


Now it will start adding to our S3 bucket

added a new role policy because our s3 did not add what we thought it would on the 5 min timeline
- this fixed the problem

Going to take our bronze output from above into silver using EMR

we'll create the emr directory locally
```python
# bronze_to_silver.py
# using spark



```


upload spark job to s3
aws s3 cp \
bronze_to_silver.py \
s3://citi-bike-nyc-pipeline/scripts/bronze_to_silver.py \
--profile company

create serverless EMR in the console
- navigate to EMR -> right panel -> EMR serverless -> manage applications -> click setup -> create application
    - type spark, release default, 

- add trust-policy (emr-trust-policy.json)
- add iam role (emr-s3-policy.json)
- attach role

submit spark job from the console
- use default settings
- create it

now we add a job to the EMR
- submit sample job run
- role = CitiBikeEMRRole
- script location - s3 location of zip we created for the emr


inspect silver
aws s3 ls \
s3://... \


now we can check on the console in the s3 to see the silver parquet files there now

https://chatgpt.com/share/6ac6b233-183c-83e8-900c-0abc2bfae418
- instructions the teacher followed to create the pipeline

Homework is to complete this:
create your own s3 buckets based on your name
- s3://richard-wilkerson/citi-bike-nyc-pipeline/bronze/citibike/
Set up Lambda to ingest data regularly into the S3 bucket
Set up EMR serverless to process the bronze data and move it to silver