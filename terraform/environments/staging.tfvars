# Staging environment configuration

environment = "staging"
aws_region  = "us-east-1"

lambda_memory         = 256
lambda_timeout        = 30
log_retention_days    = 7
throttle_rate_limit   = 10
throttle_burst_limit  = 20

# Secrets are supplied via GitHub Actions CI/CD pipeline
# anthropic_api_key = "sk-ant-..." (from GitHub secrets)
