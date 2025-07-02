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

resource "aws_s3_bucket" "data_categorization_temp" {
  bucket        = var.s3_glue_temp_bucket_name
  force_destroy = true
}

resource "aws_s3_object" "categorization_script" {
  bucket = aws_s3_bucket.data_categorization_script.id
  key    = "glue_scripts/categorize.py"
  source = "${path.module}/glue_scripts/categorize.py"
  etag   = filemd5("${path.module}/glue_scripts/categorize.py")
}


resource "aws_s3_object" "segmentation_script" {
  bucket = aws_s3_bucket.data_categorization_script.id
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

# IAM policy for DynamoDB access
resource "aws_iam_policy" "dynamodb_access" {
  name        = "data-categorization-dynamodb-access"
  description = "Policy for accessing DynamoDB file metadata table"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "dynamodb:GetItem",
          "dynamodb:PutItem",
          "dynamodb:UpdateItem",
          "dynamodb:DeleteItem",
          "dynamodb:Query",
          "dynamodb:Scan"
        ]
        Resource = aws_dynamodb_table.data_categorization_file_metadata.arn
      }
    ]
  })
}

# IAM policy for S3 access
resource "aws_iam_policy" "s3_access" {
  name        = "data-categorization-s3-access"
  description = "Policy for accessing S3 buckets for Glue scripts and temp data"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:GetObjectVersion",
          "s3:ListBucket"
        ]
        Resource = [
          aws_s3_bucket.data_categorization_script.arn,
          "${aws_s3_bucket.data_categorization_script.arn}/*"
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:PutObject",
          "s3:DeleteObject",
          "s3:ListBucket"
        ]
        Resource = [
          "arn:aws:s3:::data-categorization-temp",
          "arn:aws:s3:::data-categorization-temp/*"
        ]
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "dynamodb_access" {
  role       = aws_iam_role.glue_role.name
  policy_arn = aws_iam_policy.dynamodb_access.arn
}

resource "aws_iam_role_policy_attachment" "s3_access" {
  role       = aws_iam_role.glue_role.name
  policy_arn = aws_iam_policy.s3_access.arn
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
  
  default_arguments = {
    "--additional-python-modules" = "openpyxl==3.1.2,pandas==2.0.3,boto3==1.34.0"
    "--job-bookmark-option"       = "job-bookmark-disable"
    "--job-language"              = "python"
  }
  
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
    script_location = "s3://${aws_s3_bucket.data_categorization_script.bucket}/glue_scripts/segment.py"
    python_version  = "3"
  }
  glue_version      = "4.0"
  number_of_workers = 2
  worker_type       = "G.1X"
  
  default_arguments = {
    "--additional-python-modules" = "openpyxl==3.1.2,pandas==2.0.3,boto3==1.34.0"
    "--job-bookmark-option"       = "job-bookmark-disable"
    "--job-language"              = "python"
  }
  
  execution_property {
    max_concurrent_runs = 1
  }
  tags = {
    Environment = "dev"
  }
}

# DynamoDB table for storing file metadata
resource "aws_dynamodb_table" "data_categorization_file_metadata" {
  name           = "data-categorization-file-metadata"
  billing_mode   = "PAY_PER_REQUEST"
  hash_key       = "file_id"

  attribute {
    name = "file_id"
    type = "S"
  }

  tags = {
    Environment = "dev"
    Purpose     = "file-metadata-storage"
  }
}

