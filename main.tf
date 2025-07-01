terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region  = var.region
  profile = "dev"
}

resource "aws_s3_bucket" "data_categorization_script" {
  bucket        = var.s3_categorize_bucket_name
  force_destroy = true
}

resource "aws_s3_object" "categorization_script" {
  bucket = aws_s3_bucket.data_categorization_script.id
  key    = "glue_scripts/categorize.py"
  source = "${path.module}/glue_scripts/categorize.py"
  etag   = filemd5("${path.module}/glue_scripts/categorize.py")
}

resource "aws_s3_bucket" "data_segmentation_script" {
  bucket        = var.s3_segemtation_bucket_name
  force_destroy = true
}

resource "aws_s3_object" "segmentation_script" {
  bucket = aws_s3_bucket.data_segmentation_script.id
  key    = "glue_scripts/segment.py"
  source = "${path.module}/glue_scripts/segment.py"
  etag   = filemd5("${path.module}/glue_scripts/segment.py")
}

resource "aws_iam_role" "glue_role" {
  name = "data-categorization-segmentation-glue-role"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Sid    = "AssumeGlueRole"
        Principal = {
          Service = "glue.amazonaws.com"
        }
      },
    ]
  })
}

resource "aws_iam_role_policy_attachment" "glue_service" {
  role       = aws_iam_role.glue_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSGlueServiceRole"
}

resource "aws_glue_job" "categorize_data_job" {
  name     = "data-categorization-job"
  role_arn = aws_iam_role.glue_role.arn
  command {
    name            = "glueetl"
    script_location = "s3://${aws_s3_bucket.data_categorization_script.bucket}/glue_scripts/categorize.py"
    python_version  = "3"
  }
  glue_version      = "4.0"
  number_of_workers = 2
  worker_type       = "G.1X"
  execution_property {
    max_concurrent_runs = 1
  }
  tags = {
    Environment = "dev"
  }

}

resource "aws_glue_job" "segment_data_job" {
  name     = "data-segmentation-job"
  role_arn = aws_iam_role.glue_role.arn
  command {
    name            = "glueetl"
    script_location = "s3://${aws_s3_bucket.data_segmentation_script.bucket}/glue_scripts/segment.py"
    python_version  = "3"
  }
  glue_version      = "4.0"
  number_of_workers = 2
  worker_type       = "G.1X"
  execution_property {
    max_concurrent_runs = 1
  }
  tags = {
    Environment = "dev"
  }
}

