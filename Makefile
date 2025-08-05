# TrailBuster Makefile
# Comprehensive development utilities for Salesforce Trailhead automation

.PHONY: help install install-dev setup test test-unit test-integration test-cov lint format check clean run run-module run-trail run-batch run-stats install-playwright

# Default target
help: ## Show this help message
	@echo "TrailBuster - Salesforce Trailhead Automation Tool"
	@echo ""
	@echo "Available commands:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

# Installation and Setup
install: ## Install production dependencies with Poetry
	poetry install --only main

install-dev: ## Install all dependencies (including dev) with Poetry
	poetry install

setup: install-dev install-playwright ## Complete development setup
	@echo "Development environment setup complete!"

install-playwright: ## Install Playwright browsers
	poetry run python -m playwright install

# Testing
test: ## Run all tests with Poetry
	poetry run pytest

test-unit: ## Run unit tests only
	poetry run pytest tests/unit/ -v

test-integration: ## Run integration tests only
	poetry run pytest tests/integration/ -v

test-cov: ## Run tests with coverage report
	poetry run pytest --cov=. --cov-report=html --cov-report=term-missing

# Code Quality
lint: ## Run all linting checks with Poetry
	@echo "Running flake8..."
	poetry run flake8 . --count --select=E9,F63,F7,F82 --show-source --statistics
	poetry run flake8 . --count --exit-zero --max-complexity=10 --max-line-length=88 --statistics
	@echo "Running mypy..."
	poetry run mypy . --ignore-missing-imports
	@echo "Running ruff..."
	poetry run ruff check .

format: ## Format code with black and isort using Poetry
	@echo "Formatting with black..."
	poetry run black . --line-length=88
	@echo "Sorting imports with isort..."
	poetry run isort . --profile=black

format-check: ## Check code formatting without making changes
	@echo "Checking black formatting..."
	poetry run black . --check --line-length=88
	@echo "Checking isort..."
	poetry run isort . --check-only --profile=black

check: format-check lint test ## Run all quality checks (format, lint, test)

# Application Commands
run: ## Run default module crawl
	poetry run python main.py

run-module: ## Run module crawl (usage: make run-module URL=<module_url>)
	@if [ -z "$(URL)" ]; then \
		echo "Error: URL parameter required. Usage: make run-module URL=<module_url>"; \
		exit 1; \
	fi
	poetry run python main.py $(URL)

run-trail: ## Run trail crawl (usage: make run-trail URL=<trail_url>)
	@if [ -z "$(URL)" ]; then \
		echo "Error: URL parameter required. Usage: make run-trail URL=<trail_url>"; \
		exit 1; \
	fi
	poetry run python main.py trail $(URL)

run-batch: ## Run batch crawl (usage: make run-batch FILE=<urls_file>)
	@if [ -z "$(FILE)" ]; then \
		echo "Error: FILE parameter required. Usage: make run-batch FILE=<urls_file>"; \
		exit 1; \
	fi
	poetry run python main.py batch $(FILE)

run-stats: ## Show crawling statistics
	poetry run python main.py stats

run-clear: ## Clear saved session
	poetry run python main.py --clear-session

run-no-session: ## Force new login (no session)
	poetry run python main.py --no-session

run-help: ## Show detailed help
	poetry run python main.py --help

# Development Utilities
clean: ## Clean up generated files and caches
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} +
	find . -type d -name ".pytest_cache" -exec rm -rf {} +
	find . -type d -name ".mypy_cache" -exec rm -rf {} +
	find . -type d -name ".ruff_cache" -exec rm -rf {} +
	rm -rf htmlcov/
	rm -rf .coverage
	rm -f trailhead_session.json
	rm -f token.json
	poetry run python -m playwright install --force

# Examples (for quick testing)
example-module: ## Run example module crawl
	poetry run python main.py https://trailhead.salesforce.com/content/learn/modules/starting_force_com

example-trail: ## Run example trail crawl
	poetry run python main.py trail https://trailhead.salesforce.com/trails/force_com_admin_beginner

example-batch: ## Run example batch crawl
	poetry run python main.py batch sample_urls.txt

# Pre-commit hook (can be used with pre-commit framework)
pre-commit: format lint test ## Run all checks for pre-commit

# Development workflow
dev-setup: setup ## Complete development environment setup
	@echo "Setting up pre-commit hooks..."
	@if command -v pre-commit >/dev/null 2>&1; then \
		poetry run pre-commit install; \
	else \
		echo "pre-commit not found. Install with: poetry add --group dev pre-commit"; \
	fi

# Quick development cycle
dev: format lint test ## Quick development cycle (format, lint, test)

# Poetry specific commands
poetry-add: ## Add a dependency (usage: make poetry-add PKG=<package_name>)
	@if [ -z "$(PKG)" ]; then \
		echo "Error: PKG parameter required. Usage: make poetry-add PKG=<package_name>"; \
		exit 1; \
	fi
	poetry add $(PKG)

poetry-add-dev: ## Add a development dependency (usage: make poetry-add-dev PKG=<package_name>)
	@if [ -z "$(PKG)" ]; then \
		echo "Error: PKG parameter required. Usage: make poetry-add-dev PKG=<package_name>"; \
		exit 1; \
	fi
	poetry add --group dev $(PKG)

poetry-update: ## Update all dependencies
	poetry update

poetry-lock: ## Update poetry.lock file
	poetry lock

poetry-show: ## Show dependency tree
	poetry show --tree

# Environment setup
env-create: ## Create .env file template
	@if [ ! -f .env ]; then \
		echo "Creating .env template..."; \
		echo "SALESFORCE_EMAIL=your-email@example.com" > .env; \
		echo ".env template created. Please edit with your actual credentials."; \
	else \
		echo ".env file already exists."; \
	fi

# Security check
security-check: ## Check for sensitive files in git
	@echo "Checking for sensitive files..."
	@if git ls-files | grep -E "\.(env|json|key|pem)$" | grep -v "package.json\|pyproject.toml"; then \
		echo "Warning: Potential sensitive files found in git:"; \
		git ls-files | grep -E "\.(env|json|key|pem)$" | grep -v "package.json\|pyproject.toml"; \
	else \
		echo "No obvious sensitive files found in git."; \
	fi

# Documentation
docs: ## Generate documentation
	@echo "Generating documentation..."
	@if poetry run pdoc --version >/dev/null 2>&1; then \
		poetry run pdoc --html --output-dir docs/ .; \
		echo "Documentation generated in docs/"; \
	else \
		echo "pdoc not found. Install with: poetry add --group dev pdoc"; \
	fi

# Performance profiling
profile: ## Run performance profiling
	@echo "Running performance profiling..."
	@if poetry run py-spy --version >/dev/null 2>&1; then \
		poetry run py-spy record --output profile.svg -- poetry run python main.py; \
		echo "Profile saved as profile.svg"; \
	else \
		echo "py-spy not found. Install with: poetry add --group dev py-spy"; \
	fi

# Build and publish
build: ## Build the package
	poetry build

publish: ## Publish to PyPI (dry run)
	poetry publish --dry-run

publish-real: ## Publish to PyPI (real)
	poetry publish

# Shell access
shell: ## Open Poetry shell
	poetry shell

# Dependency management
deps-tree: ## Show dependency tree
	poetry show --tree

deps-outdated: ## Show outdated dependencies
	poetry show --outdated 
