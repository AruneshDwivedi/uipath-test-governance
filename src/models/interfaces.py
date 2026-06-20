"""
Agent interfaces and public contracts for the Test Governance Pipeline.

All agents implement the BaseAgent interface. Each agent has a single
responsibility and communicates through well-defined data structures.

[STATED] All agents are stateless functions wrapped in a class for
dependency injection. State lives in PostgreSQL, not in memory.

[STATED] Human-in-the-loop is implemented as an explicit escalation
path, not an afterthought. Every agent has a confidence threshold
below which it escalates to a human.
"""

from __future__ import annotations

import abc
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional
from datetime import datetime


# ─── Data Models ───────────────────────────────────────────────────────────────

class AgentType(Enum):
    IMPACT_ANALYZER = "impact_analyzer"
    ORCHESTRATOR = "orchestrator"
    FLAKY_DETECTOR = "flaky_detector"
    COVERAGE_REPORTER = "coverage_reporter"
    ESCALATION = "escalation"


class RiskLevel(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class TestStatus(Enum):
    PASSED = "passed"
    FAILED = "failed"
    SKIPPED = "skipped"
    FLAKY = "flaky"
    UNKNOWN = "unknown"


@dataclass
class WorkflowChange:
    """Represents a change to a UiPath workflow."""
    workflow_id: str
    workflow_name: str
    changed_files: list[str]
    diff_summary: str
    changed_at: datetime = field(default_factory=datetime.utcnow)
    author: str = ""


@dataclass
class TestImpact:
    """Output of the Impact Analyzer agent."""
    change: WorkflowChange
    affected_test_ids: list[str]
    risk_level: RiskLevel
    confidence: float  # 0.0 to 1.0
    reasoning: str
    recommended_action: str
    requires_human_review: bool = False


@dataclass
class TestResult:
    """A single test execution result."""
    test_id: str
    test_name: str
    status: TestStatus
    duration_ms: int
    error_message: str = ""
    executed_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class TestRunReport:
    """Output of the Test Orchestrator agent."""
    test_results: list[TestResult]
    total_tests: int
    passed: int
    failed: int
    skipped: int
    flaky_detected: list[str]  # test IDs flagged as flaky
    duration_ms: int
    summary: str


@dataclass
class FlakyTestReport:
    """Output of the Flaky Test Detector agent."""
    test_id: str
    test_name: str
    failure_rate: float  # 0.0 to 1.0
    consecutive_failures: int
    last_failure: datetime
    recommended_action: str  # "fix", "quarantine", "investigate"
    confidence: float


@dataclass
class CoverageReport:
    """Output of the Coverage Reporter agent."""
    workflow_id: str
    total_test_cases: int
    executed: int
    covered: int
    coverage_percentage: float
    gaps: list[str]  # areas with low coverage
    trend: str  # "improving", "declining", "stable"
    generated_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class EscalationRequest:
    """Output of any agent when confidence is too low for auto-action."""
    source_agent: AgentType
    reason: str
    context: dict[str, Any]
    suggested_action: str
    urgency: RiskLevel
    created_at: datetime = field(default_factory=datetime.utcnow)


# ─── Base Agent Interface ──────────────────────────────────────────────────────

class BaseAgent(abc.ABC):
    """Every agent in the governance pipeline implements this."""

    agent_type: AgentType
    confidence_threshold: float = 0.75

    @abc.abstractmethod
    async def execute(self, **kwargs: Any) -> Any:
        """Run the agent's primary logic. Returns agent-specific output."""
        ...

    @abc.abstractmethod
    def validate_input(self, **kwargs: Any) -> bool:
        """Validate input before execution. Returns True if valid."""
        ...

    def should_escalate(self, confidence: float) -> bool:
        """Check if confidence is below threshold and human review is needed."""
        return confidence < self.confidence_threshold


# ─── Agent-Specific Interfaces ─────────────────────────────────────────────────

class ImpactAnalyzerAgent(BaseAgent):
    """Analyzes workflow changes and determines which tests are affected."""

    agent_type = AgentType.IMPACT_ANALYZER
    confidence_threshold = 0.80

    @abc.abstractmethod
    async def analyze_impact(
        self, change: WorkflowChange
    ) -> TestImpact:
        """Given a workflow change, determine affected tests and risk level."""
        ...

    @abc.abstractmethod
    async def get_affected_tests(
        self, changed_files: list[str]
    ) -> list[str]:
        """Map changed files to affected test IDs."""
        ...


class TestOrchestratorAgent(BaseAgent):
    """Orchestrates test execution through UiPath Test Cloud."""

    agent_type = AgentType.ORCHESTRATOR
    confidence_threshold = 0.70

    @abc.abstractmethod
    async def run_tests(
        self, test_ids: list[str], risk_level: RiskLevel
    ) -> TestRunReport:
        """Execute the specified tests and return results."""
        ...

    @abc.abstractmethod
    async def schedule_tests(
        self, test_ids: list[str], priority: int
    ) -> bool:
        """Schedule tests for execution with given priority."""
        ...


class FlakyTestDetectorAgent(BaseAgent):
    """Identifies flaky or unreliable tests from historical data."""

    agent_type = AgentType.FLAKY_DETECTOR
    confidence_threshold = 0.85

    @abc.abstractmethod
    async def detect_flaky(
        self, test_results: list[TestResult], lookback_days: int = 30
    ) -> list[FlakyTestReport]:
        """Analyze test history and flag flaky tests."""
        ...

    @abc.abstractmethod
    async def get_test_history(
        self, test_id: str, days: int
    ) -> list[TestResult]:
        """Retrieve historical test results for a given test."""
        ...


class CoverageReporterAgent(BaseAgent):
    """Tracks and reports test coverage across workflows."""

    agent_type = AgentType.COVERAGE_REPORTER
    confidence_threshold = 0.75

    @abc.abstractmethod
    async def generate_report(
        self, workflow_id: str
    ) -> CoverageReport:
        """Generate a coverage report for the given workflow."""
        ...

    @abc.abstractmethod
    async def identify_gaps(
        self, workflow_id: str
    ) -> list[str]:
        """Identify areas with insufficient test coverage."""
        ...


class EscalationAgent(BaseAgent):
    """Manages human-in-the-loop escalation."""

    agent_type = AgentType.ESCALATION
    confidence_threshold = 0.90

    @abc.abstractmethod
    async def escalate(
        self, request: EscalationRequest
    ) -> bool:
        """Route escalation to the appropriate human reviewer."""
        ...

    @abc.abstractmethod
    async def get_escalation_status(
        self, escalation_id: str
    ) -> dict[str, Any]:
        """Check the status of an escalation request."""
        ...
