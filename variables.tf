variable "region" {
    description = "AWS region"
    default = "eu-west-1"
}

variable "s3_glue_scripts_bucket_name" {
    description = "S3 bucket name for glue scripts"
    default = "s3-glue-scripts"
}

variable "s3_glue_temp_bucket_name" {
    description = "S3 bucket name for glue temp data"
    default = "s3-glue-temp"
}
