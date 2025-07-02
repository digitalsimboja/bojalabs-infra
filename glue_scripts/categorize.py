import sys
import boto3
import json
import os
from awsglue.utils import getResolvedOptions
from awsglue.context import GlueContext
from awsglue.job import Job
from pyspark.context import SparkContext
import pandas as pd
import tempfile

args = getResolvedOptions(sys.argv, ['JOB_NAME', "S3_FILE_PATH", "LAMBDA_FUNCTION_NAME"])

JOB_NAME = args["JOB_NAME"]
S3_FILE_PATH = args["S3_FILE_PATH"]
LAMBDA_FUNCTION_NAME = args["LAMBDA_FUNCTION_NAME"]

sc = SparkContext()
glueContext = GlueContext(sc)
spark = glueContext.spark_session
job = Job(glueContext)
job.init(JOB_NAME, args)

print(f"JOB_NAME: {JOB_NAME}")
print(f"Reading data from: {S3_FILE_PATH}")

# Read either .csv or xlsx file from S3
if S3_FILE_PATH.endswith(".csv"):
    print("Reading CSV file...")
    
    df = spark.read.format("csv").option("header", "true").load(S3_FILE_PATH)
    sample_data = df.head(10).toPandas().fillna("").to_dict(orient="records")
    
    print(f"Successfully read {len(df)} rows from CSV file")
elif S3_FILE_PATH.endswith(".xlsx"):
    print("Reading Excel file...")
    
    try:
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx")
        temp_file_path = temp_file.name
        temp_file.close()
        
        s3_client = boto3.client("s3")
        bucket_name, key = S3_FILE_PATH.replace("s3://", "").split("/", 1)
        s3_client.download_file(bucket_name, key, temp_file_path)

        df = pd.read_excel(temp_file_path)
        df.fillna("", inplace=True)
        sample_data = df.head(10).to_dict(orient="records")

        print(f"Successfully read {len(df)} rows from Excel file")
        
        os.remove(temp_file_path)
    except Exception as e:
        print(f"Error reading Excel file: {e}")
        raise e
else:
    raise ValueError(f"Unsupported file type: {S3_FILE_PATH}")

payload = {
    "data": sample_data,
    "schema": df.columns,
    "file_name": S3_FILE_PATH
}

print("Invoking Lambda function with sample data...")

lambda_client = boto3.client("lambda")

response = lambda_client.invoke(
    FunctionName=LAMBDA_FUNCTION_NAME,
    InvocationType="RequestResponse",
    Payload=json.dumps(payload)
)

response_payload = json.loads(response["Payload"].read())

print(f"Lambda function response: {response_payload}")

# Example response from Lambda function
# {
#   "suggested_categories": ["Age Group", "Region", "Customer Type"],
#   "generated_glue_script": "import sys\nfrom awsglue.utils import ...",
#   "s3_script_path": "s3://{bucket_name}/glue-scripts/segmentation-script-{timestamp}.py"
# }


# Store the generated glue script in S3

script_path = response_payload["s3_script_path"]
key = script_path.split("/")[-1]

s3_client = boto3.client("s3")
s3_client.put_object(
    Bucket=bucket_name,
    Key=key,
    Body=response_payload["generated_glue_script"],
    ContentType="text/x-python"
)

print("Uploaded generated script and suggestions to S3:")
print(f"- Script: s3://{bucket_name}/{script_path}")

job.commit()








