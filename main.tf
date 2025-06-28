provider "aws" {
    region = var.region
}

resource "aws_s3_bucket" "data_segmentation_scripts" {
    bucket = var.s3_glue_scripts_bucket_name
    force_destroy = true
}

resource "aws_s3_object" "glue_script" {
    bucket = aws_s3_bucket.data_segmentation_scripts.id
    key = "glue_scripts/data-segmentation.py"
    source = "${path.module}/glue_script/data-segmentation.py}"
    etag = filemd5("${path.module}/glue_script/data-segmentation.py")
}

resource "aws_iam_role" "glue_role" {
    name = "data-segmentation-glue-role"
    assume_role_policy = jsonencode({
        Version = "2012-10-17"
        Statement = [
            {
                Action = "sts:AssumeRole"
                Effect = "Allow"
                Sid    = ""
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
    name = "data-segmentation-job"
    role = aws_iam_role.glue_role.arn
    command {
        name = "glueetl"
        script_location = "s3://${aws_s3_bucket.data_segmentation_scripts.bucket}/${aws_s3_object.glue_script.key}"
        python_version  = "3"
    }

    default_arguments = {
        "--job-language"   = "python"
        "--TempDir"        = "s3://${var.s3_glue_temp_bucket_name}/glue-temp/"
        "--enable-metrics" = "true"
    }

    glue_version = "4.0"
    number_of_workers = 1
    worker_type = "G.1X"
    excecution_class = "STANDARD"
    max_retries = 1
    timeout = 120
}
