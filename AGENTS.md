# Contributor Guidelines

## Development Workflow

- Use **Python 3.13** as defined in `.python-version`.
- Install dependencies with `uv sync --all-groups`.
- Use **pre-commit** for linting and testing:
  - `uv run pre-commit run --files <changed files>`
  - or `make check` to run `ruff` linting and tests.
- Run **ruff** for linting and formatting (`make lint`, `make format`).
- Run **pytest** for tests (`make test`).
- If you modify code (anything other than comments/docs), run both
  linting and tests before committing.
- Aim for 100% coverage; add tests when adding or modifying code.
- Use `uv run pre-commit install` once to install git hooks.
- Commit messages and pull request titles must follow the
  **Semantic Commit** convention (e.g. `fix:`, `feat:`).
- If Node packages are added, use **yarn** instead of npm.

## Repository Structure

- `aeonview.py` — main application code.
- `aeonview_test.py` — test suite using pytest.
- `projects/` — output directory used by the application.
- `.pre-commit-config.yaml` — hooks for linting and testing.
- `Makefile` — common commands (`format`, `lint`, `test`).
- `pyproject.toml` — project metadata and dependencies (managed by uv).
- `uv.lock` — locked dependency versions.
