import sys
import boto3
import json
import os
import logging
from datetime import datetime
from awsglue.utils import getResolvedOptions
from awsglue.context import GlueContext
from awsglue.job import Job
from pyspark.context import SparkContext
import pandas as pd
import tempfile

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Get job arguments
args = getResolvedOptions(sys.argv, ['JOB_NAME', "S3_FILE_PATH", "LAMBDA_FUNCTION_NAME"])

JOB_NAME = args["JOB_NAME"]
S3_FILE_PATH = args["S3_FILE_PATH"]
LAMBDA_FUNCTION_NAME = args["LAMBDA_FUNCTION_NAME"]

logger.info("=" * 80)
logger.info(f"Starting Glue Categorization Job: {JOB_NAME}")
logger.info(f"Job started at: {datetime.now().isoformat()}")
logger.info(f"S3 File Path: {S3_FILE_PATH}")
logger.info(f"Lambda Function Name: {LAMBDA_FUNCTION_NAME}")
logger.info("=" * 80)

try:
    # Initialize Spark and Glue context
    logger.info("Initializing Spark and Glue context...")
    sc = SparkContext()
    glueContext = GlueContext(sc)
    spark = glueContext.spark_session
    job = Job(glueContext)
    job.init(JOB_NAME, args)
    logger.info("Spark and Glue context initialized successfully")

    # Validate input parameters
    logger.info("Validating input parameters...")
    if not S3_FILE_PATH:
        raise ValueError("S3_FILE_PATH parameter is required")
    if not S3_FILE_PATH.startswith("s3://"):
        raise ValueError("S3_FILE_PATH must start with 's3://'")
    if not LAMBDA_FUNCTION_NAME:
        raise ValueError("LAMBDA_FUNCTION_NAME parameter is required")
    logger.info("Input parameters validated successfully")

    # Determine file type and read data
    logger.info(f"Processing file: {S3_FILE_PATH}")
    file_extension = S3_FILE_PATH.lower().split('.')[-1]
    logger.info(f"Detected file extension: {file_extension}")

    if file_extension == "csv":
        logger.info("Reading CSV file from S3...")
        
        # Read CSV with error handling
        try:
            df = spark.read.format("csv").option("header", "true").load(S3_FILE_PATH)
            total_rows = df.count()
            logger.info(f"Successfully read CSV file with {total_rows} rows")
            
            # Get sample data for categorization
            logger.info("Extracting sample data for categorization...")
            sample_data = df.head(10).toPandas().fillna("").to_dict(orient="records")
            logger.info(f"Extracted {len(sample_data)} sample records")
            
            # Log schema information
            schema = df.columns.tolist()
            logger.info(f"Data schema: {schema}")
            logger.info(f"Number of columns: {len(schema)}")
            
        except Exception as e:
            logger.error(f"Error reading CSV file: {str(e)}")
            raise e
            
    elif file_extension in ["xlsx", "xls"]:
        logger.info("Reading Excel file from S3...")
        
        try:
            # Create temporary file for Excel processing
            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=f".{file_extension}")
            temp_file_path = temp_file.name
            temp_file.close()
            logger.info(f"Created temporary file: {temp_file_path}")
            
            # Download file from S3
            s3_client = boto3.client("s3")
            bucket_name, key = S3_FILE_PATH.replace("s3://", "").split("/", 1)
            logger.info(f"Downloading file from S3 bucket: {bucket_name}, key: {key}")
            
            s3_client.download_file(bucket_name, key, temp_file_path)
            logger.info("File downloaded successfully from S3")

            # Read Excel file
            df = pd.read_excel(temp_file_path)
            total_rows = len(df)
            logger.info(f"Successfully read Excel file with {total_rows} rows")
            
            # Clean data
            df.fillna("", inplace=True)
            logger.info("Data cleaned - null values replaced with empty strings")
            
            # Get sample data
            sample_data = df.head(10).to_dict(orient="records")
            logger.info(f"Extracted {len(sample_data)} sample records")
            
            # Log schema information
            schema = df.columns.tolist()
            logger.info(f"Data schema: {schema}")
            logger.info(f"Number of columns: {len(schema)}")
            
            # Clean up temporary file
            os.remove(temp_file_path)
            logger.info("Temporary file cleaned up")
            
        except Exception as e:
            logger.error(f"Error reading Excel file: {str(e)}")
            # Clean up temporary file if it exists
            if 'temp_file_path' in locals() and os.path.exists(temp_file_path):
                os.remove(temp_file_path)
                logger.info("Cleaned up temporary file after error")
            raise e
    else:
        error_msg = f"Unsupported file type: {file_extension}. Supported types: csv, xlsx, xls"
        logger.error(error_msg)
        raise ValueError(error_msg)

    # Prepare payload for Lambda function
    logger.info("Preparing payload for Lambda function...")
    
    # Ensure all data is JSON serializable by converting datetime objects to strings
    def make_json_serializable(obj):
        if isinstance(obj, dict):
            return {k: make_json_serializable(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [make_json_serializable(item) for item in obj]
        elif hasattr(obj, 'isoformat'):  # datetime objects
            return obj.isoformat()
        elif hasattr(obj, 'strftime'):  # date objects
            return obj.strftime('%Y-%m-%d')
        else:
            return obj
    
    # Clean sample data to ensure JSON serialization
    cleaned_sample_data = make_json_serializable(sample_data)
    
    payload = {
        "data": cleaned_sample_data,
        "schema": schema,
        "file_name": S3_FILE_PATH
    }
    logger.info(f"Payload prepared with {len(cleaned_sample_data)} sample records and {len(schema)} columns")

    # Invoke Lambda function
    logger.info(f"Invoking Lambda function: {LAMBDA_FUNCTION_NAME}")
    lambda_client = boto3.client("lambda")
    
    try:
        logger.info("Sending request to Lambda function...")
        response = lambda_client.invoke(
            FunctionName=LAMBDA_FUNCTION_NAME,
            InvocationType="RequestResponse",
            Payload=json.dumps(payload)
        )
        
        # Check Lambda response status
        status_code = response.get('StatusCode')
        logger.info(f"Lambda function invocation completed with status code: {status_code}")
        
        if status_code != 200:
            logger.error(f"Lambda function returned non-200 status code: {status_code}")
            raise Exception(f"Lambda function failed with status code: {status_code}")
        
        # Parse Lambda response
        response_payload = json.loads(response["Payload"].read())
        logger.info("Lambda function response parsed successfully")
        
        # Log response details
        if 'error' in response_payload:
            logger.error(f"Lambda function returned error: {response_payload['error']}")
            raise Exception(f"Lambda function error: {response_payload['error']}")
        
        if 'suggested_categories' in response_payload:
            categories = response_payload['suggested_categories']
            logger.info(f"Received {len(categories)} suggested categories: {categories}")
        
        if 'generated_glue_script' in response_payload:
            script_length = len(response_payload['generated_glue_script'])
            logger.info(f"Generated Glue script length: {script_length} characters")
        
        if 's3_script_path' in response_payload:
            logger.info(f"Generated script saved to: {response_payload['s3_script_path']}")
        
        logger.info("Lambda function processing completed successfully")
        
    except Exception as e:
        logger.error(f"Error invoking Lambda function: {str(e)}")
        raise e

    # Job completion
    logger.info("=" * 80)
    logger.info(f"Glue Categorization Job completed successfully: {JOB_NAME}")
    logger.info(f"Job completed at: {datetime.now().isoformat()}")
    logger.info("=" * 80)

except Exception as e:
    logger.error("=" * 80)
    logger.error(f"Glue Categorization Job failed: {JOB_NAME}")
    logger.error(f"Error: {str(e)}")
    logger.error(f"Job failed at: {datetime.now().isoformat()}")
    logger.error("=" * 80)
    raise e

finally:
    # Commit the job
    logger.info("Committing Glue job...")
    job.commit()
    logger.info("Glue job committed successfully")








