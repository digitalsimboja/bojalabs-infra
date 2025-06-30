terraform {
  backend "s3" {
    bucket         = "dev-infra-sandbox-terraform-state"
    key            = "dev/terraform.tfstate"
    region         = "eu-west-1"
    dynamodb_table = "dev-infra-terraform-state-lock"
    profile        = "dev"
  }
}
