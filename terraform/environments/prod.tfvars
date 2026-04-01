# Production environment configuration

environment = "prod"
aws_region  = "us-east-1"

lambda_memory         = 512
lambda_timeout        = 60
log_retention_days    = 30
throttle_rate_limit   = 100
throttle_burst_limit  = 200

# Secrets are supplied via GitHub Actions CI/CD pipeline
# anthropic_api_key = "sk-ant-..." (from GitHub secrets)
