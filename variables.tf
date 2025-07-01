variable "region" {
    description = "AWS region"
    default = "eu-west-1"
}

variable "s3_categorize_bucket_name" {
    description = "S3 bucket name for glue scripts"
    default = "data-categorization-scripts"
}

variable "s3_glue_temp_bucket_name" {
    description = "S3 bucket name for glue temp data"
    default = "data-categorization-temp"
}

variable "s3_segemtation_bucket_name" {
    description = "S3 bucket name for segmentation data"
    default = "data-segmentation-scripts"
}

variable "s3_segemtation_temp_bucket_name" {
    description = "S3 bucket name for segmentation temp data"
    default = "data-segmentation-temp"
}
  

