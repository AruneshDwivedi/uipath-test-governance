# UiPath Test Governance Pipeline

Agentic test governance for UiPath Test Cloud. Analyzes workflow changes,
orchestrates test execution, detects flaky tests, tracks coverage, and
keeps humans in the loop at key decision points.

**Track:** UiPath AgentHack 2024 — Track 3: UiPath Test Cloud

## What It Does

When a UiPath workflow changes, this pipeline:

1. **Impact Analyzer** — determines which tests are affected and the risk level
2. **Test Orchestrator** — runs the right tests at the right time via Test Cloud
3. **Flaky Test Detector** — flags unreliable tests before they slow down releases
4. **Coverage Reporter** — tracks coverage trends and identifies gaps
5. **Escalation Manager** — routes low-confidence decisions to human reviewers

All orchestrated by **UiPath Maestro BPMN** with agents built using
**LangChain** and **UiPath Test Cloud API**.

## UiPath Components Used

| Component | Purpose |
|---|---|
| UiPath Test Cloud | Test case management, execution, results |
| UiPath Maestro BPMN | Agent orchestration and process flow |
| UiPath API Workflows | External API integrations (LangChain, PostgreSQL) |
| UiPath Agent Builder | Low-code agent actions |
| UiPath for Coding Agents | Claude Code used during development (bonus criteria) |

## Architecture

```
Workflow Change Detected
        │
        ▼
┌─────────────────────┐
│  Impact Analyzer    │ ← LangChain + static file mapping
│  (confidence: 0.8+) │
└────────┬────────────┘
         │ low confidence → Escalation Manager → Human
         ▼
┌─────────────────────┐
│  Test Orchestrator  │ ← UiPath Test Cloud API
│  (risk-based order) │
└────────┬────────────┘
         │
    ┌────┴────┐
    ▼         ▼
┌────────┐ ┌──────────────┐
│ Flaky  │ │  Coverage    │
│Detector│ │  Reporter    │
└────────┘ └──────────────┘
    │         │
    └────┬────┘
         ▼
   Results + Escalations
```

## Quickstart

### Prerequisites

- Python 3.11+
- UiPath Automation Cloud account with Test Cloud access
- PostgreSQL 14+

### Setup

```bash
# Clone
git clone https://github.com/AruneshDwivedi/uipath-test-governance.git
cd uipath-test-governance

# Install
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"

# Configure
cp .env.example .env
# Edit .env with your UiPath and database credentials

# Run tests
pytest tests/unit -v

# Run pre-commit
pre-commit install
pre-commit run --all-files
```

### Environment Variables

| Variable | Description |
|---|---|
| `UIPATH_BASE_URL` | UiPath Automation Cloud URL |
| `UIPATH_ORG_ID` | Organization ID |
| `UIPATH_TENANT_ID` | Tenant ID |
| `UIPATH_CLIENT_ID` | OAuth2 client ID |
| `UIPATH_CLIENT_SECRET` | OAuth2 client secret |
| `UIPATH_FOLDER_ID` | Modern folder ID |
| `DB_HOST` | PostgreSQL host |
| `DB_PORT` | PostgreSQL port |
| `DB_NAME` | Database name |
| `DB_USER` | Database user |
| `DB_PASSWORD` | Database password |
| `LLM_PROVIDER` | LLM provider (openai/anthropic) |
| `LLM_MODEL` | Model name |
| `LLM_API_KEY` | LLM API key |

## Project Structure

```
src/
  agents/           # 5 agent implementations
    impact_analyzer.py
    orchestrator.py
    flaky_detector.py
    coverage_reporter.py
    escalation.py
  orchestrator/     # Pipeline orchestration
    pipeline.py
  uipath/           # UiPath API clients
    test_cloud_client.py
  models/           # Data models and interfaces
    interfaces.py
    database.py
  config/           # Settings
    settings.py
tests/
  unit/             # Unit tests
  integration/      # Integration tests
docs/
  decisions/        # Architecture Decision Records
.github/            # CI, templates, workflows
```

## Development

This project was built using Claude Code through UiPath for Coding Agents.
See `docs/decisions/` for architecture decisions.

## License

MIT
