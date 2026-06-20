# Changelog

## [Unreleased]

## [0.1.0] — 2026-06-20

### Added

- **Test Impact Analyzer agent** — analyzes workflow changes and determines affected tests using static file mapping + LLM reasoning. Returns risk level, confidence score, and recommended action.
- **Test Orchestrator agent** — executes tests via UiPath Test Cloud API with batching, rate limiting, retry logic, and risk-based prioritization.
- **Flaky Test Detector agent** — identifies unreliable tests from historical data using statistical analysis over a configurable lookback window. Recommends fix/quarantine/investigate actions.
- **Coverage Reporter agent** — tracks test coverage across workflows, identifies gaps, and reports trends over time.
- **Escalation Manager agent** — routes low-confidence decisions to human reviewers with full context, SLA tracking, and urgency-based routing.
- **Test Governance Orchestrator** — coordinates all 5 agents through the full pipeline with human-in-the-loop at every decision point.
- **UiPath Test Cloud API client** — async OAuth2 client with retry, rate limiting, and full test case/execution/results API coverage.
- **Database models** — SQLAlchemy 2.0 models for workflows, test cases, mappings, results, coverage, and escalations.
- **Agent interfaces** — `BaseAgent` ABC with typed input/output contracts for all 5 agents.
- **CI pipeline** — GitHub Actions with lint (ruff), type check (mypy), unit tests (pytest), and coverage gate (70% minimum).
- **Pre-commit hooks** — ruff, format, secrets detection, trailing whitespace.
- **Documentation** — README, ADR-001, CONTRIBUTING, SECURITY, CODE_OF_CONDUCT.
- **GitHub templates** — bug report, feature request, PR template.

### What's NOT included (yet)

- UiPath Maestro BPMN process file (to be created in UiPath Studio)
- Integration tests against live Test Cloud instance
- LangGraph stateful agent orchestration (planned for v0.2.0)
- Web dashboard for coverage visualization

### Known limitations

- LLM-based impact analysis requires a valid API key (OpenAI/Anthropic)
- Database migrations not yet set up (use `alembic` in v0.2.0)
- Test Cloud API client is a wrapper — actual UiPath SDK integration pending

[Unreleased]: https://github.com/AruneshDwivedi/uipath-test-governance/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/AruneshDwivedi/uipath-test-governance/releases/tag/v0.1.0
