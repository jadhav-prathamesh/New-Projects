# Contributing to DevOps Incident Analyzer

We're thrilled that you want to contribute! This project is built for the community, and every contribution — whether it's a bug fix, a new detection rule, a documentation improvement, or a feature — is genuinely appreciated.

## Code of Conduct

By participating, you agree to uphold our [Code of Conduct](CODE_OF_CONDUCT.md). Please be respectful, inclusive, and constructive.

## How to Contribute

### 1. Reporting Bugs

Open an [issue](https://github.com/jadhav-prathamesh/New-Projects/issues/new/choose) and include:

- A clear description of the problem
- Steps to reproduce
- Expected vs actual behavior
- Python version and OS
- Sample log data (if applicable, sanitized)

### 2. Suggesting Features

Open a [feature request](https://github.com/jadhav-prathamesh/New-Projects/issues/new/choose) and describe:

- What problem the feature solves
- How you envision it working
- Any alternative approaches you've considered

### 3. Adding Detection Rules

The most common contribution! See [rules.py](rules.py) for the pattern, then:

1. Add a new `DetectionRule` entry
2. Update the docs in [README.md](README.md) with the new rule
3. Submit a PR

### 4. Adding Parser Adapters

See [adapters.py](adapters.py) for existing implementations. To add a new format:

1. Create a parser function (e.g., `parse_nginx_line`)
2. Register it in `resolve_adapter` and `parse_with_adapter`
3. Add sample data and update documentation

### 5. Code Contributions

#### Getting Started

```bash
# Fork the repo, then clone
git clone https://github.com/your-username/New-Projects.git
cd New-Projects

# Create a branch
git checkout -b feature/my-awesome-contribution

# Make your changes, then verify
python log_analyzer.py sample_logs.txt
```

#### Development Guidelines

- **Keep it dependency-free** — no external packages unless absolutely necessary
- **Follow the existing style** — readable, well-commented Python
- **Test your changes** — run the analyzer against sample data
- **Update documentation** — README, docstrings, and comments

### 6. Pull Request Process

1. Ensure your branch is up to date with `main`
2. Run the analyzer against sample files to verify nothing is broken
3. Update the README and documentation if needed
4. Open a PR with a clear title and description
5. A maintainer will review and provide feedback

## Development Setup

```bash
# No setup needed! Pure Python, zero dependencies.
python log_analyzer.py sample_logs.txt
```

## Style Guide

- **Python**: Follow PEP 8, use type hints, keep functions focused
- **Documentation**: Markdown, clear language, code examples where helpful
- **Commit messages**: Use conventional commits (`feat:`, `fix:`, `docs:`, etc.)

## Questions?

Open a [discussion](https://github.com/jadhav-prathamesh/New-Projects/discussions) or reach out in the issues.

Thank you for making this project better! 🚀

