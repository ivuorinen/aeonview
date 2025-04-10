# Contributing to aeonview

Thanks for your interest in contributing to **aeonview**! This guide will help you get started.

## 🛠 Project Setup

1. Clone the repository:
   ```bash
   git clone https://github.com/your-username/aeonview.git
   cd aeonview
   ```

2. Set up your environment:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   pip install -r dev-requirements.txt
   ```

3. Install pre-commit hooks:
   ```bash
   pre-commit install
   ```

## ✅ Development Workflow

- Make sure your changes are **well-tested**.
- Use `make check` to run linting and tests.
- Follow the existing coding style (Ruff will enforce it).
- All new features must include documentation.

## 🧪 Running Tests

```bash
make test
```

## 🧹 Formatting & Linting

```bash
make format   # auto-format code
make lint     # check for lint errors
```

## ✅ Submitting a Pull Request

1. Create a feature branch:
   ```bash
   git checkout -b feature/my-new-feature
   ```

2. Commit your changes:
   ```bash
   git add .
   git commit -m "feat: add support for X"
   ```

3. Push and open a pull request:
   ```bash
   git push origin feature/my-new-feature
   ```

4. Follow the PR template and link any relevant issues.

## 📋 Commit Message Guidelines

Use [Conventional Commits](https://www.conventionalcommits.org/en/v1.0.0/):

Examples:
- `feat: add monthly video generation`
- `fix: handle invalid date error`
- `docs: update usage instructions`

## 🙏 Code of Conduct

We expect contributors to follow our [Code of Conduct](CODE_OF_CONDUCT.md).

## Questions?
Feel free to open an issue or start a discussion!

Thanks for helping make Aeonview better 💜

<!--
vim: ft=md sw=2 ts=2 tw=72 fo=cqt wm=0 et
-->
