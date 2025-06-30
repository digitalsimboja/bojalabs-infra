#!/bin/bash

# === CONFIGURATION ===
AWS_PROFILE="dev"          
AWS_REGION="eu-west-1"
S3_BUCKET_NAME="dev-infra-sandbox-terraform-state" #"Location": "http://dev-infra-sandybox-terraform-state.s3.amazonaws.com/"
DYNAMO_TABLE_NAME="dev-infra-terraform-state-lock"


# === CREATE S3 BUCKET ===
echo "⏳ Checking if S3 bucket '$S3_BUCKET_NAME' exists..."
if aws s3api head-bucket --bucket "$S3_BUCKET_NAME" --profile "$AWS_PROFILE" 2>/dev/null; then
    echo "✅ S3 bucket already exists: $S3_BUCKET_NAME"
else
    echo "📦 Creating S3 bucket: $S3_BUCKET_NAME"
    aws s3api create-bucket \
        --bucket "$S3_BUCKET_NAME" \
        --region "$AWS_REGION" \
        --create-bucket-configuration LocationConstraint="$AWS_REGION" \
        --profile "$AWS_PROFILE"

    echo "🔐 Enabling versioning on bucket..."
    aws s3api put-bucket-versioning \
        --bucket "$S3_BUCKET_NAME" \
        --versioning-configuration Status=Enabled \
        --profile "$AWS_PROFILE"
fi

# === CREATE DYNAMODB TABLE ===
echo "⏳ Checking if DynamoDB table '$DYNAMO_TABLE_NAME' exists..."
if aws dynamodb describe-table --table-name "$DYNAMO_TABLE_NAME" --profile "$AWS_PROFILE" 2>/dev/null; then
    echo "✅ DynamoDB table already exists: $DYNAMO_TABLE_NAME"
else
    echo "📊 Creating DynamoDB table: $DYNAMO_TABLE_NAME"
    aws dynamodb create-table \
        --table-name "$DYNAMO_TABLE_NAME" \
        --attribute-definitions AttributeName=LockID,AttributeType=S \
        --key-schema AttributeName=LockID,KeyType=HASH \
        --billing-mode PAY_PER_REQUEST \
        --region "$AWS_REGION" \
        --profile "$AWS_PROFILE"

    echo "⏱️ Waiting for DynamoDB table to be active..."
    aws dynamodb wait table-exists \
        --table-name "$DYNAMO_TABLE_NAME" \
        --profile "$AWS_PROFILE"
fi

echo "✅ Bootstrap complete. You can now run: terraform init"
