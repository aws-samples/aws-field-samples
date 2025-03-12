# Configuration
PYTHON := python3
POETRY := poetry
PYTEST := $(POETRY) run pytest
RUFF := $(POETRY) run ruff
BANDIT := $(POETRY) run bandit

# Directories
SRC_DIR := src
TEST_DIR := tests
WEBUI_DIR := webui
DIST_DIR := dist
BUILD_DIR := build

# Add more specific cleanup patterns
CLEANUP_PATTERNS := __pycache__ *.egg-info .pytest_cache .coverage .mypy_cache .ruff_cache

.PHONY: all clean install uninstall reinstall test test-verbose lint lint-fix scan build run-ui

# Default target
all: clean install test

# Development setup
install:
	$(POETRY) install

reinstall: uninstall install

uninstall:
	pip uninstall -y converseagent

# Building and running
build:
	$(POETRY) build

run-ui:
	cd $(WEBUI_DIR) && python run-webui-dev.py

# Testing and quality checks
test:
	$(PYTEST) $(TEST_DIR)

test-verbose:
	$(PYTEST) -v $(TEST_DIR)

# Linting and formatting
lint:
	$(RUFF) check $(SRC_DIR) $(TEST_DIR)

lint-fix:
	$(RUFF) check --fix $(SRC_DIR) $(TEST_DIR)

format:
	$(RUFF) format $(SRC_DIR) $(TEST_DIR)

scan:
	$(BANDIT) -r . -c pyproject.toml

# Enhanced clean target with better error handling
clean:
	@for pattern in $(CLEANUP_PATTERNS); do \
		find . -type d -name "$$pattern" -exec rm -rf {} + 2>/dev/null || true; \
	done
	rm -rf $(DIST_DIR) $(BUILD_DIR)
	@echo "Cleanup completed"

# Help target
help:
	@echo "Available targets:"
	@echo "  install      - Install project dependencies"
	@echo "  reinstall    - Reinstall project dependencies"
	@echo "  uninstall    - Remove project installation"
	@echo "  build        - Build the project"
	@echo "  run-ui       - Start the web UI"
	@echo "  test         - Run tests"
	@echo "  test-verbose - Run tests with verbose output"
	@echo "  lint         - Check code with Ruff"
	@echo "  lint-fix     - Auto-fix linting issues with Ruff"
	@echo "  format       - Format code using Ruff"
	@echo "  scan         - Run security scan with bandit"
	@echo "  clean        - Clean up temporary files"
