#!/usr/bin/env bash
set -euo pipefail

# Run smoke tests against a deployed Lambda endpoint.
# Usage: ./scripts/smoke-test.sh https://your-api-id.execute-api.us-east-1.amazonaws.com

if [ -z "${1:-}" ]; then
    echo "Usage: $0 <api_endpoint_url>"
    echo "Example: $0 https://abcd1234.execute-api.us-east-1.amazonaws.com"
    exit 1
fi

API_ENDPOINT="$1"
ENDPOINT="${API_ENDPOINT%/}/process"  # Remove trailing slash if present, add /process

echo "==> Running smoke tests against $ENDPOINT"
echo ""

# Test 1: Echo endpoint
echo "Test 1: Echo request"
RESPONSE=$(curl -s -X POST "$ENDPOINT" \
    -H "Content-Type: application/json" \
    -d '{"task_type": "echo", "payload": {"message": "hello"}}')

if echo "$RESPONSE" | jq . > /dev/null 2>&1; then
    SUCCESS=$(echo "$RESPONSE" | jq -r '.success')
    if [ "$SUCCESS" = "true" ]; then
        echo "✓ Echo test passed"
    else
        echo "✗ Echo test failed: success=$SUCCESS"
        echo "Response: $RESPONSE"
        exit 1
    fi
else
    echo "✗ Invalid JSON response"
    echo "Response: $RESPONSE"
    exit 1
fi

# Test 2: Invalid request should return 400
echo "Test 2: Invalid request (missing task_type)"
RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "$ENDPOINT" \
    -H "Content-Type: application/json" \
    -d '{"payload": {}}')

HTTP_CODE=$(echo "$RESPONSE" | tail -1)
BODY=$(echo "$RESPONSE" | head -1)

if [ "$HTTP_CODE" = "400" ]; then
    echo "✓ Invalid request test passed (HTTP 400)"
else
    echo "✗ Invalid request test failed: expected HTTP 400, got $HTTP_CODE"
    exit 1
fi

# Test 3: CORS headers
echo "Test 3: CORS headers"
RESPONSE=$(curl -s -i -X POST "$ENDPOINT" \
    -H "Content-Type: application/json" \
    -d '{"task_type": "echo", "payload": {}}' 2>/dev/null)

if echo "$RESPONSE" | grep -q "Access-Control-Allow-Origin"; then
    echo "✓ CORS headers test passed"
else
    echo "✗ CORS headers test failed"
    exit 1
fi

echo ""
echo "==> All smoke tests passed!"
