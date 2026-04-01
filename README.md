# CI/CD Pipeline Template

Production-ready GitHub Actions + Terraform setup for Python Lambda deployments on AWS. Complete environment promotion strategy with staging and production workflows, automated testing, security scanning, and rollback capability.

Built as a reference implementation by [Three Moons Network](https://threemoonsnetwork.net) — an AI consulting practice helping small businesses automate with production-grade systems.

## What It Does

This template provides a fully-configured CI/CD pipeline that:

- **Runs tests and lint checks** on every PR
- **Validates Terraform** infrastructure code
- **Deploys to staging** automatically on main branch merge
- **Provides manual workflow** for production deployments with approval gates
- **Runs smoke tests** after each deployment
- **Supports rollback** to previous Lambda version on failure
- **Scans for security issues** weekly (dependency vulnerabilities, Terraform misconfigurations)
- **Manages two environments** (staging and prod) with separate configuration

## Architecture

```
GitHub PR/Push
    │
    ├─► CI Pipeline (ruff lint, pytest, terraform fmt/validate)
    │
    ├─► (on main merge) Deploy to Staging
    │       ├─ Build Lambda package
    │       ├─ Terraform plan + apply
    │       ├─ Run smoke tests
    │       └─ Auto-promote if tests pass
    │
    └─► (manual trigger) Deploy to Production
            ├─ Validate all tests pass
            ├─ Terraform plan (requires approval)
            ├─ Terraform apply (requires approval)
            ├─ Run smoke tests
            └─ Rollback on failure (automatic)
```

## Workflows

### ci.yml — Continuous Integration
Runs on every push to main and all PRs. Contains:
- **test**: pytest on Python 3.11 with mocked APIs
- **lint**: ruff format check and linting
- **terraform-validate**: fmt -check, init, validate
- **package**: Build lambda.zip artifact on main merges only

### deploy-staging.yml — Automated Staging Deployment
Triggers on main branch merge (when src/, terraform/, requirements.txt, or this workflow changes):
- Builds Lambda package
- Plans and applies Terraform for staging environment
- Runs smoke tests against the deployed endpoint
- No manual approval needed

### deploy-prod.yml — Manual Production Deployment
Triggers on workflow_dispatch (manual button in GitHub UI):
- Validates that all tests pass on the target version
- Plans Terraform for prod
- **Requires environment approval** (protection rule)
- Applies Terraform
- Runs smoke tests
- **Rolls back automatically** on smoke test failure

### security-scan.yml — Weekly Security Audit
Runs every Monday at 2 AM UTC (configurable):
- Audits runtime and dev dependencies with pip-audit
- Scans Terraform with Checkov
- Runs security linter (bandit) on Python code

## Project Structure

```
├── src/
│   ├── __init__.py
│   └── handler.py                 # Lambda handler — customize your business logic
├── tests/
│   ├── __init__.py
│   └── test_handler.py            # Unit tests (mocked APIs)
├── terraform/
│   ├── main.tf                    # All infrastructure definition
│   ├── outputs.tf                 # Output values for CI/CD
│   ├── backend.tf                 # Remote state config (commented for local use)
│   └── environments/
│       ├── staging.tfvars         # Staging environment config
│       └── prod.tfvars            # Production environment config
├── .github/workflows/
│   ├── ci.yml                     # Pull request and main branch validation
│   ├── deploy-staging.yml         # Auto-deploy to staging on main merge
│   ├── deploy-prod.yml            # Manual production deployment with approval
│   └── security-scan.yml          # Weekly security audit
├── scripts/
│   ├── build-lambda.sh            # Build Lambda deployment package
│   ├── smoke-test.sh              # Integration tests against deployed endpoint
│   └── rollback.sh                # Rollback Lambda to previous version
├── requirements.txt               # Runtime dependencies (anthropic, boto3)
├── requirements-dev.txt           # Development dependencies (pytest, ruff)
├── Makefile                       # Common developer tasks
└── README.md                      # This file
```

## Quick Start

### Prerequisites

- AWS account with CLI configured (`aws configure`)
- GitHub repository with Actions enabled
- Terraform >= 1.5
- Python 3.11+

### 1. Clone and initialize

```bash
git clone git@github.com:Three-Moons-Network/ci-cd-pipeline-template.git
cd ci-cd-pipeline-template
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt -r requirements-dev.txt
```

### 2. Set up local testing

```bash
# Run tests
pytest tests/ -v

# Run linting
ruff check src/ tests/
ruff format src/ tests/

# Test handler locally
export ANTHROPIC_API_KEY="sk-ant-..."
python -c "
from src.handler import lambda_handler
import json
event = {'body': json.dumps({'task_type': 'echo', 'payload': {'msg': 'test'}})}
print(json.dumps(json.loads(lambda_handler(event, None)['body']), indent=2))
"
```

### 3. Configure GitHub Actions secrets

In your GitHub repository settings (Settings → Secrets and variables → Actions), add:

```
AWS_ACCESS_KEY_ID         # IAM user with Lambda, API Gateway, SSM, CloudWatch permissions
AWS_SECRET_ACCESS_KEY
ANTHROPIC_API_KEY         # Claude API key (see console.anthropic.com)
```

### 4. Set up environment protection (recommended for prod)

Go to Settings → Environments → production:
- Check "Require approval before deploying"
- Add reviewers who must approve production deployments

### 5. Build and deploy locally (for testing)

```bash
# Build Lambda package
make build

# Deploy to staging
make deploy-staging

# Deploy to production (requires AWS credentials, uses prod.tfvars)
make deploy-prod
```

### 6. Trigger production deployment via GitHub UI

1. Go to Actions → Deploy to Production
2. Click "Run workflow"
3. Enter a version tag (or main branch)
4. Wait for CI to pass, environment approval, and smoke tests

## Environment Promotion Strategy

### Staging
- **Triggers**: Automatic on main branch merge
- **Approval**: None (continuous deployment)
- **Retention**: Build artifacts kept 7 days
- **Specs**: 256 MB Lambda, 30s timeout, 10 req/s throttle

### Production
- **Triggers**: Manual via workflow_dispatch only
- **Approval**: Required (GitHub environment protection)
- **Retention**: Build artifacts kept 30 days
- **Specs**: 512 MB Lambda, 60s timeout, 100 req/s throttle
- **Rollback**: Automatic if smoke tests fail

## CI/CD Features

### Testing Strategy

1. **Unit Tests** (pytest with mocking)
   - No real API calls in CI
   - Tests run against mocked Anthropic SDK
   - Validates request validation, routing, error handling

2. **Smoke Tests** (curl against deployed endpoint)
   - Verify endpoint responds to requests
   - Check for CORS headers
   - Validate error responses (400 for bad input)

3. **Code Quality** (ruff)
   - Format checking
   - Linting rules
   - Must pass before merging to main

### Infrastructure Validation

- Terraform format check
- Terraform plan and validate
- No destructive changes without approval

### Security Scanning

- **pip-audit**: Check for known vulnerabilities in dependencies
- **Checkov**: Scan Terraform for security misconfigurations
- **bandit**: Static analysis of Python code for security issues

### Artifacts and Retention

| Artifact | Staging | Prod | Format |
|----------|---------|------|--------|
| lambda.zip | 7 days | 30 days | GitHub Actions |
| TF plan | 7 days | 1 day | GitHub Actions |
| Logs | 7 days | 30 days | CloudWatch |

## Customization Guide

### Add a New Lambda Function

1. Create `src/my_function.py` with a `lambda_handler(event, context)` function
2. Update `terraform/main.tf` to create a new Lambda resource and API Gateway route
3. Add tests in `tests/test_my_function.py`
4. Workflows will automatically test and package

### Change Deployment Frequency

Edit `.github/workflows/deploy-staging.yml`:
- Remove or modify the `on.push.paths` condition
- Or change to manual trigger by replacing `push` with `workflow_dispatch`

### Disable Auto-Rollback

Edit `.github/workflows/deploy-prod.yml`:
- Remove the `rollback` job
- Or change `if: failure()` to `if: never`

### Add Custom Monitoring

In `terraform/main.tf`, add more CloudWatch alarms:
```hcl
resource "aws_cloudwatch_metric_alarm" "custom_metric" {
  alarm_name          = "${local.prefix}-custom"
  metric_name         = "CustomMetric"
  # ... configure as needed
}
```

### Change Slack/Email Notifications

Create a simple Lambda function to parse CloudWatch alarms and post to Slack, then add an SNS topic to the alarms. Or use AWS Chatbot for direct Slack integration.

## Troubleshooting

### Smoke tests fail after deployment

1. Check Lambda logs: `aws logs tail /aws/lambda/cicd-pipeline-staging --follow`
2. Verify API Gateway: `terraform output -raw invoke_url` in staging workspace
3. Manually test: `curl -X POST <url> -H "Content-Type: application/json" -d '{...}'`

### Terraform plan shows unexpected changes

1. Run `terraform fmt -recursive` to fix formatting
2. Check if state is out of sync: `terraform refresh`
3. Verify `terraform.tfvars` is correct for the environment

### GitHub Actions job cancelled

1. Check secret values are set: Settings → Secrets and variables → Actions
2. Verify AWS IAM user has required permissions
3. Check if environment protection rule is blocking the job

### Lambda times out in production but works in staging

1. Check prod.tfvars: `lambda_timeout` may be too low
2. Review Lambda logs for long-running operations
3. Increase memory (can improve CPU): prod.tfvars `lambda_memory`

## Cost Estimate

For low-volume usage (< 1,000 requests/month) and staging + prod:

| Component | Staging | Prod | Total |
|-----------|---------|------|-------|
| Lambda | Free (free tier) | Free (free tier) | ~$0 |
| API Gateway | Free (free tier) | Free (free tier) | ~$0 |
| CloudWatch | ~$0.50 | ~$0.50 | ~$1 |
| SSM Parameter Store | Free | Free | Free |
| **Total Infrastructure** | | | **~$1/month** |
| **Claude API** (variable) | | | ~$5-50/month |

Your largest cost is Claude API usage — infrastructure is nearly free.

## Best Practices

1. **Never commit API keys** — use GitHub secrets exclusively
2. **Test before production** — staging deployment is automatic, prod is manual
3. **Review Terraform plans** — approve manually before production changes
4. **Monitor alarms** — set up CloudWatch alarm notifications to email/Slack
5. **Version releases** — use git tags for production deployments (e.g., `v1.0.0`)
6. **Keep dependencies updated** — security scan runs weekly
7. **Maintain test coverage** — aim for >80% coverage in unit tests

## License

MIT

## Author

Charles Harvey ([linuxlsr](https://github.com/linuxlsr)) — [Three Moons Network LLC](https://threemoonsnetwork.net)
