# Contributing to UiPath Test Governance

Thanks for your interest. Here's how to get involved.

## Setup

1. Fork the repo
2. Clone your fork: `git clone https://github.com/YOUR_NAME/uipath-test-governance.git`
3. Install: `pip install -e ".[dev]"`
4. Copy `.env.example` to `.env` and fill in your credentials
5. Run tests: `pytest tests/unit -v`

## Making Changes

- Create a feature branch: `git checkout -b feat/your-feature`
- Write tests for new code
- Ensure lint passes: `ruff check src tests`
- Ensure type checks pass: `mypy src`
- Commit with conventional commits: `feat:`, `fix:`, `docs:`, `test:`
- Open a PR with a clear description

## Code Style

- Python 3.11+, type hints required
- Async throughout (no blocking I/O in agents)
- Docstrings on all public methods
- Tests for all agent logic

## Questions?

Open a GitHub Discussion or reach out on the UiPath Community Forum.
