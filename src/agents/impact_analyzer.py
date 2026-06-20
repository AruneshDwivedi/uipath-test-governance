"""Test Impact Analyzer agent.

Analyzes workflow changes and determines which tests are affected.
Uses LangChain for reasoning and UiPath Test Cloud API for test data.

[STATED] The agent uses a combination of static file mapping (from the
test_mappings table) and LLM-based reasoning for cases not covered
by explicit mappings.

[STATED] Confidence is calculated as a weighted combination of:
  - mapping coverage (how many changed files have known test mappings)
  - llm reasoning confidence (self-reported by the agent)
  - historical accuracy (past predictions vs actual failures)
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Optional

from src.models.interfaces import (
    AgentType, BaseAgent, RiskLevel, TestImpact, WorkflowChange
)

logger = logging.getLogger(__name__)


class TestImpactAnalyzer(BaseAgent):
    """Analyzes workflow changes and determines affected tests + risk level."""

    agent_type = AgentType.IMPACT_ANALYZER
    confidence_threshold = 0.80

    def __init__(
        self,
        db_session: Any,
        llm_client: Any,
        test_cloud_client: Any,
    ):
        self.db = db_session
        self.llm = llm_client
        self.test_cloud = test_cloud_client

    def validate_input(self, **kwargs: Any) -> bool:
        change = kwargs.get("change")
        if not change or not isinstance(change, WorkflowChange):
            return False
        return bool(change.workflow_id and change.changed_files)

    async def execute(self, **kwargs: Any) -> TestImpact:
        """Main entry point — delegates to analyze_impact."""
        change: WorkflowChange = kwargs["change"]
        return await self.analyze_impact(change)

    async def analyze_impact(
        self, change: WorkflowChange
    ) -> TestImpact:
        """Given a workflow change, determine affected tests and risk level."""
        logger.info(
            "Analyzing impact for workflow %s (%d files changed)",
            change.workflow_id,
            len(change.changed_files),
        )

        # Step 1: Find affected tests via static mapping
        mapped_tests = await self.get_affected_tests(change.changed_files)

        # Step 2: Use LLM to assess risk for unmapped files
        unmapped_files = [
            f for f in change.changed_files
            if f not in self._get_mapped_files(mapped_tests)
        ]

        llm_confidence = 0.9 if not unmapped_files else 0.6

        if unmapped_files:
            llm_assessment = await self._assess_risk_with_llm(
                change, unmapped_files
            )
            mapped_tests.extend(llm_assessment.get("additional_tests", []))
            risk_level = RiskLevel(llm_assessment.get("risk_level", "medium"))
        else:
            risk_level = self._calculate_risk_level(
                change, mapped_tests, llm_confidence
            )

        # Step 3: Calculate overall confidence
        mapping_coverage = 1.0 if not unmapped_files else (
            len(change.changed_files) - len(unmapped_files)
        ) / len(change.changed_files)
        confidence = (mapping_coverage * 0.6) + (llm_confidence * 0.4)

        # Step 4: Determine if human review is needed
        requires_human = self.should_escalate(confidence) or risk_level in (
            RiskLevel.HIGH, RiskLevel.CRITICAL
        )

        reasoning = (
            f"{len(mapped_tests)} tests mapped from "
            f"{len(change.changed_files)} changed files. "
            f"{len(unmapped_files)} files required LLM analysis. "
            f"Mapping coverage: {mapping_coverage:.0%}."
        )

        return TestImpact(
            change=change,
            affected_test_ids=list(set(mapped_tests)),
            risk_level=risk_level,
            confidence=round(confidence, 2),
            reasoning=reasoning,
            recommended_action=self._recommend_action(risk_level, confidence),
            requires_human_review=requires_human,
        )

    async def get_affected_tests(
        self, changed_files: list[str]
    ) -> list[str]:
        """Map changed files to affected test IDs via static mappings."""
        affected: list[str] = []
        for file_path in changed_files:
            mappings = await self._query_test_mappings(file_path)
            for m in mappings:
                if m.test_case_id not in affected:
                    affected.append(m.test_case_id)
        return affected

    async def _query_test_mappings(self, file_path: str) -> list[Any]:
        """Query the test_mappings table for a given file path."""
        # In production: SQL query with glob matching
        # SELECT test_case_id FROM test_mappings
        # WHERE :file_path GLOB file_pattern
        return []

    async def _assess_risk_with_llm(
        self,
        change: WorkflowChange,
        unmapped_files: list[str],
    ) -> dict[str, Any]:
        """Use LLM to assess risk for files without static test mappings."""
        prompt = (
            f"The following files were changed in workflow "
            f"'{change.workflow_name}':\n"
            + "\n".join(f"  - {f}" for f in unmapped_files)
            + f"\n\nDiff summary:\n{change.diff_summary}\n\n"
            "Assess the risk level (low/medium/high/critical) and "
            "list any additional test IDs that should be run. "
            "Respond in JSON format."
        )
        # In production: call LLM via LangChain
        return {"risk_level": "medium", "additional_tests": []}

    def _calculate_risk_level(
        self,
        change: WorkflowChange,
        affected_tests: list[str],
        confidence: float,
    ) -> RiskLevel:
        """Calculate risk level based on change characteristics."""
        if len(change.changed_files) > 10 or not affected_tests:
            return RiskLevel.HIGH
        if len(change.changed_files) > 5:
            return RiskLevel.MEDIUM
        if confidence < 0.5:
            return RiskLevel.MEDIUM
        return RiskLevel.LOW

    def _recommend_action(
        self, risk_level: RiskLevel, confidence: float
    ) -> str:
        if risk_level == RiskLevel.CRITICAL:
            return "Run full test suite + manual review required"
        if risk_level == RiskLevel.HIGH:
            return "Run affected tests + spot-check related areas"
        if confidence < self.confidence_threshold:
            return "Run affected tests + escalate for review"
        return "Run affected tests only"

    @staticmethod
    def _get_mapped_files(test_ids: list[str]) -> list[str]:
        """Reverse-lookup: given test IDs, return the files they cover."""
        return []
