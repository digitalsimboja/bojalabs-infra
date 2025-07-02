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
  value = "s3://${aws_s3_bucket.data_categorization_script.bucket}/${aws_s3_object.segmentation_script.key}"
}

output "file_metadata_table_name" {
  value = aws_dynamodb_table.data_categorization_file_metadata
}

output "file_metadata_table_arn" {
  value = aws_dynamodb_table.data_categorization_file_metadata.arn
}
