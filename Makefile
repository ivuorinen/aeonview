.PHONY: install format lint test check clean

install:
	@pip install -r requirements.txt

format:
	@ruff format .

lint:
	@ruff check .

test:
	@pytest --cov=aeonview --cov-report=term-missing

check: lint test

clean:
	@find . -type d -name '__pycache__' -exec rm -r {} +
	@rm -rf .pytest_cache .coverage htmlcov
