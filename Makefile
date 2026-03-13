.PHONY: install format lint test check clean

install:
	@uv sync --all-groups

format:
	@uv run ruff format .

lint:
	@uv run ruff check .

test:
	@uv run pytest --cov=aeonview --cov-report=term-missing

check: lint test

clean:
	@find . -type d -name '__pycache__' -exec rm -r {} +
	@rm -rf .pytest_cache .coverage htmlcov .venv
