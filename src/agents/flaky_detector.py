"""Flaky Test Detector agent.

Identifies flaky or unreliable tests from historical execution data.
Uses statistical analysis over a configurable lookback window.

[STATED] A test is flagged as flaky when its failure rate exceeds
the threshold (default 15%) over the lookback period, AND it has
at least 3 executions (to avoid flagging tests with 1 failure out of 2 runs).

[STATED] The agent recommends one of three actions:
  - "fix": failure rate > 40%, test is clearly broken
  - "quarantine": failure rate 15-40%, test is unreliable
  - "investigate": failure rate 10-15%, needs human review
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Optional

from src.models.interfaces import (
    AgentType, BaseAgent, FlakyTestReport, TestResult, TestStatus
)

logger = logging.getLogger(__name__)

FLAKY_THRESHOLD = 0.15  # 15% failure rate
MIN_EXECUTIONS = 3


class FlakyTestDetector(BaseAgent):
    """Identifies flaky tests from historical execution data."""

    agent_type = AgentType.FLAKY_DETECTOR
    confidence_threshold = 0.85

    def __init__(self, db_session: Any):
        self.db = db_session

    def validate_input(self, **kwargs: Any) -> bool:
        results = kwargs.get("test_results")
        return bool(results and isinstance(results, list))

    async def execute(self, **kwargs: Any) -> list[FlakyTestReport]:
        """Main entry point — delegates to detect_flaky."""
        results: list[TestResult] = kwargs["test_results"]
        lookback_days: int = kwargs.get("lookback_days", 30)
        return await self.detect_flaky(results, lookback_days)

    async def detect_flaky(
        self,
        test_results: list[TestResult],
        lookback_days: int = 30,
    ) -> list[FlakyTestReport]:
        """Analyze test history and flag flaky tests."""
        logger.info(
            "Analyzing %d test results over %d days",
            len(test_results), lookback_days,
        )

        # Group results by test_id
        by_test: dict[str, list[TestResult]] = {}
        for r in test_results:
            by_test.setdefault(r.test_id, []).append(r)

        reports: list[FlakyTestReport] = []
        cutoff = datetime.utcnow() - timedelta(days=lookback_days)

        for test_id, results in by_test.items():
            # Filter to lookback window
            recent = [r for r in results if r.executed_at >= cutoff]

            if len(recent) < MIN_EXECUTIONS:
                continue

            failures = sum(1 for r in recent if r.status == TestStatus.FAILED)
            failure_rate = failures / len(recent)

            if failure_rate < FLAKY_THRESHOLD:
                continue

            consecutive = self._count_consecutive_failures(recent)
            last_failure = max(
                (r.executed_at for r in recent if r.status == TestStatus.FAILED),
                default=datetime.utcnow(),
            )

            action = self._recommend_action(failure_rate, consecutive)
            confidence = min(1.0, len(recent) / 20.0)  # more data = more confident

            reports.append(
                FlakyTestReport(
                    test_id=test_id,
                    test_name=recent[0].test_name,
                    failure_rate=round(failure_rate, 3),
                    consecutive_failures=consecutive,
                    last_failure=last_failure,
                    recommended_action=action,
                    confidence=round(confidence, 2),
                )
            )

        logger.info("Flagged %d tests as flaky", len(reports))
        return reports

    async def get_test_history(
        self, test_id: str, days: int
    ) -> list[TestResult]:
        """Retrieve historical test results from the database."""
        # In production: query test_results table
        # SELECT * FROM test_results
        # WHERE test_case_id = :test_id AND executed_at >= :cutoff
        return []

    @staticmethod
    def _count_consecutive_failures(results: list[TestResult]) -> int:
        """Count the most recent consecutive failures."""
        count = 0
        for r in reversed(results):
            if r.status == TestStatus.FAILED:
                count += 1
            else:
                break
        return count

    @staticmethod
    def _recommend_action(failure_rate: float, consecutive: int) -> str:
        if failure_rate > 0.4 or consecutive >= 5:
            return "fix"
        if failure_rate > 0.15 or consecutive >= 3:
            return "quarantine"
        return "investigate"
