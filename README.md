# Terraform for AWS

## Prerequisites

- Install [Terraform](https://www.terraform.io/downloads.html)
- Install [AWS CLI](https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html)
- Configure AWS CLI with your credentials
Go to [AWS Console](https://console.aws.amazon.com/) and navigate to your user profile. Click on the Security credentials link on the left side of the page. Create a new access key or use an existing access key. Make sure you copy the access key ID and secret access key now.

- Create an S3 bucket to store the terraform state file
- Create DynamoDB table to store the terraform state lock

## Usage

### Create infrastructure

```bash
terraform init
teraform plan
terraform apply
```

### Destroy infrastructure

```bash
terraform destroy
```
