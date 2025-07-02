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
    # Read the input data
    print(f"Reading data from: {s3_input_path}")
    df = spark.read.csv(s3_input_path, header=True, inferSchema=True)
    
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
    
    print("Segmentation job completed successfully!")
    print(f"Summary: {summary_stats}")
    
except Exception as e:
    print(f"Error in segmentation job: {str(e)}")
    raise e

job.commit()
