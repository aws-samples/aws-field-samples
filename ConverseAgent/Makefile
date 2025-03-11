.PHONY: build install reinstall test format clean 

scan:
	bandit -r ./src

build:
	poetry build

install:
	poetry install

reinstall:
	pip uninstall -y converseagent
	make install

uninstall:
	pip uninstall -y converseagent

run-ui:
	cd webui && ./start_webui.sh

# Test commands
test:
	poetry run pytest tests/

test-verbose:
	poetry run pytest -v tests/

# Development commands
format:
	poetry run black src/ tests/

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type d -name "*.egg-info" -exec rm -rf {} +
	find . -type d -name ".pytest_cache" -exec rm -rf {} +
	find . -type d -name ".coverage" -exec rm -rf {} +
	find . -type d -name ".mypy_cache" -exec rm -rf {} +
	rm -rf dist/ build/