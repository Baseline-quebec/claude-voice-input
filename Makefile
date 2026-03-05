.PHONY: install dev lint format typecheck test test-cov clean

install:
	pip install -e .

dev:
	pip install -e ".[dev]"
	pre-commit install

lint:
	ruff check .

format:
	ruff format .

typecheck:
	mypy src/

test:
	pytest

test-cov:
	pytest --cov=claude_voice_input --cov-report=term-missing

clean:
	rm -rf build/ dist/ *.egg-info .mypy_cache .pytest_cache .ruff_cache .coverage coverage.xml
	find . -type d -name __pycache__ -exec rm -rf {} +
