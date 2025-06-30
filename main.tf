terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
    region = var.region
    profile = "dev"
}

resource "aws_s3_bucket" "data_segmentation_scripts" {
    bucket = var.s3_glue_scripts_bucket_name
    force_destroy = true
}

resource "aws_s3_object" "glue_script" {
    bucket = aws_s3_bucket.data_segmentation_scripts.id
    key = "glue_scripts/data-segmentation.py"
    source = "${path.module}/glue_scripts/data-segmentation.py"
    etag = filemd5("${path.module}/glue_scripts/data-segmentation.py")
}

resource "aws_iam_role" "glue_role" {
    name = "data-segmentation-glue-role"
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

resource "aws_glue_job" "data_segmentation_job" {
  name     = "data-segmentation-job"
  role_arn = aws_iam_role.glue_role.arn
  command {
    name            = "glueetl"
    script_location = "s3://${aws_s3_bucket.data_segmentation_scripts.bucket}/glue_scripts/data-segmentation.py"
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

