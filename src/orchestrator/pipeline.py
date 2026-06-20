"""
Maestro BPMN orchestration layer.

Coordinates the 5 agents through a BPMN process:
  1. Workflow Change Detected → Impact Analyzer
  2. Impact Analyzer → Test Orchestrator (if confidence high)
  3. Test Orchestrator → Flaky Test Detector + Coverage Reporter
  4. Any agent below confidence → Escalation Manager
  5. Results aggregated → Report generated

[STATED] This module defines the BPMN process structure. The actual
BPMN XML is in config/test_governance.bpmn and is deployed to
UiPath Maestro separately.

[STATED] The orchestration logic here is the code-behind that runs
inside UiPath API Workflows, triggered by Maestro BPMN service tasks.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from src.models.interfaces import (
    AgentType, EscalationRequest, RiskLevel, TestImpact, TestRunReport,
    WorkflowChange, FlakyTestReport, CoverageReport,
)
from src.agents.impact_analyzer import TestImpactAnalyzer
from src.agents.orchestrator import TestOrchestrator
from src.agents.flaky_detector import FlakyTestDetector
from src.agents.coverage_reporter import CoverageReporter
from src.agents.escalation import EscalationManager

logger = logging.getLogger(__name__)


class TestGovernanceOrchestrator:
    """Orchestrates the full test governance pipeline."""

    def __init__(
        self,
        impact_analyzer: TestImpactAnalyzer,
        test_orchestrator: TestOrchestrator,
        flaky_detector: FlakyTestDetector,
        coverage_reporter: CoverageReporter,
        escalation_manager: EscalationManager,
    ):
        self.impact_analyzer = impact_analyzer
        self.test_orchestrator = test_orchestrator
        self.flaky_detector = flaky_detector
        self.coverage_reporter = coverage_reporter
        self.escalation_manager = escalation_manager

    async def run_pipeline(
        self, change: WorkflowChange
    ) -> dict[str, Any]:
        """Execute the full governance pipeline for a workflow change."""
        logger.info(
            "Starting governance pipeline for workflow %s",
            change.workflow_id,
        )
        pipeline_start = datetime.utcnow()
        results: dict[str, Any] = {
            "workflow_id": change.workflow_id,
            "started_at": pipeline_start.isoformat(),
        }

        # ── Step 1: Impact Analysis ──
        impact = await self.impact_analyzer.analyze_impact(change)
        results["impact"] = {
            "affected_tests": len(impact.affected_test_ids),
            "risk_level": impact.risk_level.value,
            "confidence": impact.confidence,
            "reasoning": impact.reasoning,
            "requires_human_review": impact.requires_human_review,
        }

        if impact.requires_human_review:
            escalation = EscalationRequest(
                source_agent=AgentType.IMPACT_ANALYZER,
                reason=f"Low confidence ({impact.confidence}) or high risk ({impact.risk_level.value})",
                context={
                    "workflow_id": change.workflow_id,
                    "changed_files": change.changed_files,
                    "affected_tests": impact.affected_test_ids,
                },
                suggested_action="Manual review of impact assessment",
                urgency=impact.risk_level,
            )
            await self.escalation_manager.escalate(escalation)
            results["status"] = "escalated"
            results["escalation_reason"] = "impact_analysis_low_confidence"
            return results

        if not impact.affected_test_ids:
            results["status"] = "no_tests_affected"
            results["message"] = "No tests mapped to changed files"
            return results

        # ── Step 2: Test Execution ──
        test_report = await self.test_orchestrator.run_tests(
            impact.affected_test_ids, impact.risk_level
        )
        results["test_run"] = {
            "total": test_report.total_tests,
            "passed": test_report.passed,
            "failed": test_report.failed,
            "skipped": test_report.skipped,
            "duration_ms": test_report.duration_ms,
            "summary": test_report.summary,
        }

        if test_report.failed > 0:
            escalation = EscalationRequest(
                source_agent=AgentType.ORCHESTRATOR,
                reason=f"{test_report.failed} tests failed",
                context={
                    "failed_tests": [
                        r.test_id for r in test_report.test_results
                        if r.status.value == "failed"
                    ],
                },
                suggested_action="Review failed test results",
                urgency=RiskLevel.HIGH if test_report.failed > 2 else RiskLevel.MEDIUM,
            )
            await self.escalation_manager.escalate(escalation)

        # ── Step 3: Flaky Test Detection ──
        if test_report.test_results:
            flaky_reports = await self.flaky_detector.detect_flaky(
                test_report.test_results
            )
            results["flaky_tests"] = [
                {
                    "test_id": r.test_id,
                    "failure_rate": r.failure_rate,
                    "action": r.recommended_action,
                }
                for r in flaky_reports
            ]
            if flaky_reports:
                escalation = EscalationRequest(
                    source_agent=AgentType.FLAKY_DETECTOR,
                    reason=f"{len(flaky_reports)} tests flagged as flaky",
                    context={
                        "flaky_tests": [
                            {"id": r.test_id, "rate": r.failure_rate}
                            for r in flaky_reports
                        ],
                    },
                    suggested_action="Review and fix or quarantine flaky tests",
                    urgency=RiskLevel.MEDIUM,
                )
                await self.escalation_manager.escalate(escalation)

        # ── Step 4: Coverage Report ──
        coverage = await self.coverage_reporter.generate_report(
            change.workflow_id
        )
        results["coverage"] = {
            "percentage": coverage.coverage_percentage,
            "total_tests": coverage.total_test_cases,
            "gaps": coverage.gaps,
            "trend": coverage.trend,
        }

        if coverage.coverage_percentage < 60:
            escalation = EscalationRequest(
                source_agent=AgentType.COVERAGE_REPORTER,
                reason=f"Low coverage: {coverage.coverage_percentage}%",
                context={
                    "gaps": coverage.gaps,
                    "trend": coverage.trend,
                },
                suggested_action="Add tests for uncovered areas",
                urgency=RiskLevel.MEDIUM,
            )
            await self.escalation_manager.escalate(escalation)

        # ── Done ──
        results["status"] = "completed"
        results["duration_ms"] = int(
            (datetime.utcnow() - pipeline_start).total_seconds() * 1000
        )
        logger.info(
            "Pipeline completed in %dms", results["duration_ms"]
        )
        return results
