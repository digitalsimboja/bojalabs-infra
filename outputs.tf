output "glue_job_name" {
    value = aws_glue_job.data_segmentation_job.name
}

output "script_location" {
    value = aws_glue_job.data_segmentation_job.script_location
}