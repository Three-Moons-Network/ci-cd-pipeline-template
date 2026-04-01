#!/usr/bin/env bash
set -euo pipefail

# Rollback Lambda to the previous version.
# Usage: ./rollback.sh <function_name> [aws_region] [aws_profile]

if [ -z "${1:-}" ]; then
    echo "Usage: $0 <function_name> [aws_region] [aws_profile]"
    echo "Example: $0 my-function us-east-1 default"
    exit 1
fi

FUNCTION_NAME="$1"
AWS_REGION="${2:-us-east-1}"
AWS_PROFILE="${3:-default}"

echo "==> Rolling back Lambda function: $FUNCTION_NAME"
echo "    Region: $AWS_REGION"
echo "    Profile: $AWS_PROFILE"
echo ""

# Get all versions sorted by creation date (most recent first)
VERSIONS=$(aws lambda list-versions-by-function \
    --function-name "$FUNCTION_NAME" \
    --region "$AWS_REGION" \
    --profile "$AWS_PROFILE" \
    --query 'Versions[?Version != `$LATEST`] | sort_by(@, &LastModified) | reverse(@) | [0:2].[Version]' \
    --output text)

read -r CURRENT_VERSION PREVIOUS_VERSION <<< "$VERSIONS"

if [ -z "$PREVIOUS_VERSION" ]; then
    echo "✗ No previous version found. Cannot rollback."
    exit 1
fi

echo "Current version: $CURRENT_VERSION"
echo "Rolling back to: $PREVIOUS_VERSION"
echo ""

# Update function alias to point to previous version
ALIAS_NAME="live"
aws lambda update-alias \
    --function-name "$FUNCTION_NAME" \
    --name "$ALIAS_NAME" \
    --function-version "$PREVIOUS_VERSION" \
    --region "$AWS_REGION" \
    --profile "$AWS_PROFILE" \
    > /dev/null

echo "✓ Rollback successful"
echo "  Function: $FUNCTION_NAME"
echo "  Alias: $ALIAS_NAME"
echo "  Version: $PREVIOUS_VERSION"
