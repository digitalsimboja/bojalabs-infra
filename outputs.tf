output "categorize_glue_job_name" {
  value = aws_glue_job.categorize_data_job.name
}

output "categorize_glue_script_location" {
  value = "s3://${aws_s3_bucket.data_categorization_script.bucket}/${aws_s3_object.categorization_script.key}"
}

output "segmentation_glue_job_name" {
  value = aws_glue_job.segment_data_job.name
}

output "segmentation_glue_script_location" {
  value = "s3://${aws_s3_bucket.data_segmentation_script.bucket}/${aws_s3_object.segmentation_script.key}"
}


# categorize_glue_job_name = "data-categorization-job"
# categorize_glue_script_location = "s3://data-categorization-scripts/glue_scripts/categorize.py"
# segmentation_glue_job_name = "data-segmentation-job"
# segmentation_glue_script_location = "s3://data-segmentation-scripts/glue_scripts/segment.py"