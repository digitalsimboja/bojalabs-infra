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


## Manual Flow – Breakdown of What Needs to Be Implemented
### Step 1: Glue Job A – categorize.py
- Trigger: Invoked manually via API (/segment).

- Action:

    - Reads uploaded file from S3.

    - Converts it to a small sample (e.g. first 10 rows).

    - Prepares a prompt to be passed to a Lambda function for Bedrock.

    - (Optional) Stores the sample in S3 (optional if Bedrock doesn’t need a file).

    - Invokes Lambda A synchronously.

### Step 2: Lambda A – suggest_categories.py
- Trigger: Called by Glue Job A.

- Action:

    - Uses the input schema or rows from Glue.

    - Constructs a prompt.

    - Calls Bedrock model (e.g. Claude or Titan) with this prompt.

    - Returns:

        - Suggested categories (array or JSON).

        - Suggested categorization logic (or Glue-compatible pseudocode).

        - Stores generated categorization script in S3.


### Step 3: Glue Job A returns response
- Suggested categories and the Glue script S3 location are sent back to the frontend.

### Step 4: Frontend Displays Suggested Categories
- User reviews and accepts them.

### Step 5: Upon confirmation – call Glue Job B (segmenter)
- Use the returned script to run Glue segmentation on the same input file.

- Output the segmented data to a new S3 folder.


## File/Function Breakdown
| Component    | File Name                  | Description                                |
| ------------ | -------------------------- | ------------------------------------------ |
| Glue Job A   | `categorize.py`            | Reads file, samples, calls Lambda A        |
| Lambda A     | `suggest_categories.py`    | Uses Bedrock to suggest categories & logic |
| Glue Job B   | `segment.py` (future step) | Applies confirmed segmentation             |
| API Endpoint | `/segment` (Next.js)       | Triggers Glue Job A                        |
| S3 Paths     | `/uploads/`, `/scripts/`   | For input and output organization          |
