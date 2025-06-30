output "glue_job_name" {
  value = aws_glue_job.data_segmentation_job.name
}

output "glue_script_location" {
  value = "s3://${aws_s3_bucket.data_segmentation_scripts.bucket}/${aws_s3_object.glue_script.key}"
}
