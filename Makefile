.PHONY: help lint test build deploy-staging deploy-prod clean

help:
	@echo "CI/CD Pipeline Template — Makefile targets"
	@echo ""
	@echo "Development:"
	@echo "  make lint           — Run ruff format and linting checks"
	@echo "  make test           — Run pytest suite"
	@echo "  make build          — Build Lambda deployment package"
	@echo ""
	@echo "Deployment:"
	@echo "  make deploy-staging — Deploy to staging environment"
	@echo "  make deploy-prod    — Deploy to production environment (requires manual approval)"
	@echo ""
	@echo "Maintenance:"
	@echo "  make clean          — Remove build artifacts"
	@echo ""

lint:
	ruff format src/ tests/
	ruff check src/ tests/

test:
	pytest tests/ -v --tb=short

build:
	./scripts/build-lambda.sh

deploy-staging:
	@echo "Deploying to staging..."
	cd terraform && terraform init -upgrade
	cd terraform && terraform plan -var-file=environments/staging.tfvars -out=tfplan
	cd terraform && terraform apply -auto-approve tfplan
	@echo "✓ Staging deployment complete"
	@API_URL=$$(cd terraform && terraform output -raw invoke_url); \
	./scripts/smoke-test.sh $$API_URL

deploy-prod:
	@echo "⚠ Production deployment requires manual approval"
	cd terraform && terraform init -upgrade
	cd terraform && terraform plan -var-file=environments/prod.tfvars -out=tfplan
	@echo ""
	@echo "Review the plan above and confirm:"
	@read -p "Continue with production deployment? (y/N) " confirm; \
	if [ "$$confirm" = "y" ]; then \
		cd terraform && terraform apply -auto-approve tfplan; \
		API_URL=$$(cd terraform && terraform output -raw invoke_url); \
		./scripts/smoke-test.sh $$API_URL; \
		echo "✓ Production deployment complete"; \
	else \
		echo "Deployment cancelled"; \
		exit 1; \
	fi

clean:
	rm -rf dist/
	rm -rf .pytest_cache/
	rm -rf .ruff_cache/
	rm -rf __pycache__
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
