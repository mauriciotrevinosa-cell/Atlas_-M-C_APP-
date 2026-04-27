# ============================================
# PROJECT ATLAS — Build & Development Targets
# ============================================
# Usage: make <target>
# Run 'make help' for all available targets

.PHONY: help install dev test lint format run server aria demo clean docs check

# Default target
help: ## Show this help message
	@echo ""
	@echo "  Project Atlas — Available Targets"
	@echo "  =================================="
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}'
	@echo ""

# ---- Installation ----

install: ## Install Atlas (production dependencies)
	pip install -e . --break-system-packages

dev: ## Install Atlas with all dev dependencies
	pip install -e ".[dev,web,memory,signals]" --break-system-packages

install-all: ## Install Atlas with ALL optional dependencies
	pip install -e ".[dev,web,memory,signals,voice-basic,image,integrations,code,api]" --break-system-packages

# ---- Running ----

run: ## Run Atlas in browser mode (default)
	python run_atlas.py

server: ## Start the FastAPI server only
	python run_server.py

aria: ## Start ARIA interactive terminal
	python run_aria.py

demo: ## Run Phase 1 demo pipeline
	python run_atlas.py --demo

demo-symbols: ## Run demo with custom symbols (usage: make demo-symbols SYMBOLS="AAPL MSFT SPY")
	python scripts/run_phase1_demo.py --symbols $(SYMBOLS)

# ---- Testing ----

test: ## Run all tests
	python -m pytest tests/ -ra -q

test-unit: ## Run unit tests only
	python -m pytest tests/unit/ -ra -q

test-agents: ## Run agent tests only
	python -m pytest tests/agents/ -ra -q

test-cov: ## Run tests with coverage report
	python -m pytest tests/ -ra --cov=python/src/atlas --cov-report=term-missing

# ---- Code Quality ----

lint: ## Run linting (ruff + mypy)
	ruff check python/src/atlas/
	mypy python/src/atlas/ --ignore-missing-imports || true

format: ## Format code with black
	black python/src/atlas/ tests/

check: ## Run all quality checks (lint + test)
	$(MAKE) lint
	$(MAKE) test

# ---- Documentation ----

docs: ## List all documentation files
	@echo "Documentation Index:"
	@find docs/ -name "*.md" | sort
	@echo ""
	@echo "Governance:"
	@find project_governance/ -name "*.md" | sort

# ---- Maintenance ----

clean: ## Clean build artifacts and caches
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	rm -rf build/ dist/ *.egg-info/ 2>/dev/null || true
	@echo "Cleaned build artifacts"

clean-logs: ## Archive and clean log files
	@mkdir -p logs/archive
	@mv logs/*.log logs/archive/ 2>/dev/null || true
	@echo "Logs archived to logs/archive/"

# ---- Data & APIs ----

check-apis: ## Check which API keys are configured
	@echo "API Key Status:"
	@echo "==============="
	@test -f .env && (grep -c "FRED_API_KEY=" .env > /dev/null 2>&1 && echo "  FRED:           configured" || echo "  FRED:           not set") || echo "  .env file not found - copy .env.example to .env"
	@test -f .env && (grep -c "ALPHA_VANTAGE_KEY=" .env > /dev/null 2>&1 && echo "  Alpha Vantage:  configured" || echo "  Alpha Vantage:  not set") || true
	@test -f .env && (grep -c "FINNHUB_API_KEY=" .env > /dev/null 2>&1 && echo "  Finnhub:        configured" || echo "  Finnhub:        not set") || true
	@test -f .env && (grep -c "POLYGON_API_KEY=" .env > /dev/null 2>&1 && echo "  Polygon:        configured" || echo "  Polygon:        not set") || true
	@test -f .env && (grep -c "NEWSAPI_KEY=" .env > /dev/null 2>&1 && echo "  NewsAPI:        configured" || echo "  NewsAPI:        not set") || true
	@test -f .env && (grep -c "GROQ_API_KEY=" .env > /dev/null 2>&1 && echo "  Groq:           configured" || echo "  Groq:           not set") || true
