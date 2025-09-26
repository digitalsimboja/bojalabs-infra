import sys
from awsglue.transforms import *
from awsglue.utils import getResolvedOptions
from pyspark.context import SparkContext
from awsglue.context import GlueContext
from awsglue.job import Job
from pyspark.sql.functions import *
from pyspark.sql.types import *
import boto3
import json
import uuid
import pandas as pd
import tempfile
import os
from datetime import datetime

# Initialize Glue context
args = getResolvedOptions(sys.argv, ['JOB_NAME', 's3_input_path', 's3_output_path', 'segmentation_criteria'])
sc = SparkContext()
glueContext = GlueContext(sc)
spark = glueContext.spark_session
job = Job(glueContext)
job.init(args['JOB_NAME'], args)

# Get job parameters
s3_input_path = args['s3_input_path']
s3_output_path = args['s3_output_path']
segmentation_criteria = json.loads(args['segmentation_criteria'])

print(f"Starting segmentation job with criteria: {segmentation_criteria}")

try:
    # Determine file type and read data with header detection
    print(f"Reading data from: {s3_input_path}")
    file_extension = s3_input_path.lower().split('.')[-1]
    print(f"Detected file extension: {file_extension}")
    
    if file_extension == "csv":
        # Handle CSV files
        print("Reading CSV file to detect proper header row...")
        df_raw = spark.read.format("csv").option("header", "false").load(s3_input_path)
        
        # Get first few rows to find the header
        sample_rows = df_raw.head(10)
        print(f"Inspecting first {len(sample_rows)} rows for proper headers...")
        
        # Find the row with proper column names (not "Unnamed" or empty)
        header_row_index = None
        for i, row in enumerate(sample_rows):
            row_values = [str(val) if val is not None else "" for val in row]
            print(f"Row {i}: {row_values}")
            
            # Check if this row has proper column names
            has_proper_headers = True
            for val in row_values:
                if val.strip() == "" or val.startswith("Unnamed:") or val.lower() in ["", "nan", "null", "none"]:
                    has_proper_headers = False
                    break
            
            if has_proper_headers and len([v for v in row_values if v.strip()]) > 0:
                header_row_index = i
                print(f"Found proper header at row {i}: {row_values}")
                break
        
        if header_row_index is None:
            print("No proper header row found, using first row as header")
            header_row_index = 0
        
        # Read CSV with the detected header row
        print(f"Reading CSV with header at row {header_row_index}")
        df = spark.read.format("csv").option("header", "false").option("skip", header_row_index).load(s3_input_path)
        
        # Rename columns based on the detected header row
        header_row = sample_rows[header_row_index]
        column_names = [str(val) if val is not None else f"column_{i}" for i, val in enumerate(header_row)]
        print(f"Column names: {column_names}")
        
        # Apply column names
        for i, col_name in enumerate(column_names):
            df = df.withColumnRenamed(f"_c{i}", col_name)
    
    elif file_extension in ["xlsx", "xls"]:
        # Handle Excel files
        print("Reading Excel file to detect proper header row...")
        
        # Create temporary file for Excel processing
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=f".{file_extension}")
        temp_file_path = temp_file.name
        temp_file.close()
        print(f"Created temporary file: {temp_file_path}")
        
        try:
            # Download file from S3
            s3_client = boto3.client("s3")
            bucket_name, key = s3_input_path.replace("s3://", "").split("/", 1)
            print(f"Downloading file from S3 bucket: {bucket_name}, key: {key}")
            
            s3_client.download_file(bucket_name, key, temp_file_path)
            print("File downloaded successfully from S3")
            
            # First, read without headers to inspect rows
            df_raw = pd.read_excel(temp_file_path, header=None)
            print(f"Raw Excel data shape: {df_raw.shape}")
            
            # Get first few rows to find the header
            sample_rows = df_raw.head(10)
            print(f"Inspecting first {len(sample_rows)} rows for proper headers...")
            
            # Find the row with proper column names (not "Unnamed" or empty)
            header_row_index = None
            for i, row in sample_rows.iterrows():
                row_values = [str(val) if pd.notna(val) else "" for val in row.values]
                print(f"Row {i}: {row_values}")
                
                # Check if this row has proper column names
                has_proper_headers = True
                for val in row_values:
                    if val.strip() == "" or val.startswith("Unnamed:") or val.lower() in ["", "nan", "null", "none"]:
                        has_proper_headers = False
                        break
                
                if has_proper_headers and len([v for v in row_values if v.strip()]) > 0:
                    header_row_index = i
                    print(f"Found proper header at row {i}: {row_values}")
                    break
            
            if header_row_index is None:
                print("No proper header row found, using first row as header")
                header_row_index = 0
            
            # Read Excel with the detected header row
            print(f"Reading Excel with header at row {header_row_index}")
            df_pandas = pd.read_excel(temp_file_path, header=header_row_index)
            
            # Clean data
            df_pandas.fillna("", inplace=True)
            print("Data cleaned - null values replaced with empty strings")
            
            # Convert pandas DataFrame to Spark DataFrame
            df = spark.createDataFrame(df_pandas)
            print(f"Converted pandas DataFrame to Spark DataFrame")
            
        finally:
            # Clean up temporary file
            if os.path.exists(temp_file_path):
                os.remove(temp_file_path)
                print("Temporary file cleaned up")
    
    else:
        error_msg = f"Unsupported file type: {file_extension}. Supported types: csv, xlsx, xls"
        print(error_msg)
        raise ValueError(error_msg)
    
    print(f"Data schema: {df.schema}")
    print(f"Data count: {df.count()}")
    
    # Apply segmentation based on criteria
    if 'segments' in segmentation_criteria:
        for segment_name, segment_config in segmentation_criteria['segments'].items():
            print(f"Creating segment: {segment_name}")
            
            # Apply filters for this segment
            segment_df = df
            if 'filters' in segment_config:
                for filter_condition in segment_config['filters']:
                    column = filter_condition['column']
                    operator = filter_condition['operator']
                    value = filter_condition['value']
                    
                    if operator == 'equals':
                        segment_df = segment_df.filter(col(column) == value)
                    elif operator == 'greater_than':
                        segment_df = segment_df.filter(col(column) > value)
                    elif operator == 'less_than':
                        segment_df = segment_df.filter(col(column) < value)
                    elif operator == 'contains':
                        segment_df = segment_df.filter(col(column).contains(value))
                    elif operator == 'in':
                        segment_df = segment_df.filter(col(column).isin(value))
            
            # Save segment to S3
            segment_output_path = f"{s3_output_path}/segments/{segment_name}"
            print(f"Saving segment to: {segment_output_path}")
            
            segment_df.write.mode("overwrite").csv(segment_output_path, header=True)
            
            print(f"Segment '{segment_name}' created with {segment_df.count()} records")
    
    # Save summary statistics
    summary_stats = {
        "total_records": df.count(),
        "segments_created": list(segmentation_criteria.get('segments', {}).keys()),
        "timestamp": datetime.now().isoformat(),
        "job_id": args['JOB_NAME']
    }
    
    # Write summary to S3
    summary_df = spark.createDataFrame([summary_stats])
    summary_output_path = f"{s3_output_path}/summary"
    summary_df.write.mode("overwrite").json(summary_output_path)
    
    # Store results in DynamoDB
    try:
        import boto3
        from boto3.dynamodb.conditions import Key
        
        # Create DynamoDB client
        dynamodb = boto3.resource('dynamodb', region_name='eu-west-1')
        table = dynamodb.Table('data-categorization-file-metadata')
        
        # Extract file name from S3 path
        file_name = s3_input_path.split('/')[-1]
        
        # Store segmentation results
        table.put_item(Item={
            'file_id': f"{file_name}_{datetime.now().isoformat()}",
            'file_name': file_name,
            'timestamp': datetime.now().isoformat(),
            'job_name': args['JOB_NAME'],
            'segmentation_criteria': segmentation_criteria,
            'output_path': s3_output_path,
            'total_records': df.count(),
            'segments_created': list(segmentation_criteria.get('segments', {}).keys()),
            'schema': [field.name for field in df.schema.fields],
            'segmented_rows': []  # This would be populated with actual segmented data if needed
        })
        
        print("Segmentation results stored in DynamoDB successfully!")
        
    except Exception as e:
        print(f"Warning: Failed to store results in DynamoDB: {str(e)}")
    
    print("Segmentation job completed successfully!")
    print(f"Summary: {summary_stats}")
    
except Exception as e:
    print(f"Error in segmentation job: {str(e)}")
    raise e

job.commit()
