"""Unit tests for Flaky Test Detector agent."""

import pytest
from datetime import datetime, timedelta

from src.agents.flaky_detector import FlakyTestDetector, FLAKY_THRESHOLD, MIN_EXECUTIONS
from src.models.interfaces import TestResult, TestStatus


@pytest.fixture
def mock_db():
    from unittest.mock import AsyncMock
    return AsyncMock()


@pytest.fixture
def detector(mock_db):
    return FlakyTestDetector(db_session=mock_db)


def _make_result(test_id: str, status: TestStatus, days_ago: int = 0) -> TestResult:
    return TestResult(
        test_id=test_id,
        test_name=f"Test {test_id}",
        status=status,
        duration_ms=100,
        executed_at=datetime.utcnow() - timedelta(days=days_ago),
    )


class TestFlakyTestDetector:
    def test_validate_input_valid(self, detector):
        results = [_make_result("t1", TestStatus.PASSED)]
        assert detector.validate_input(test_results=results) is True

    def test_validate_input_empty(self, detector):
        assert detector.validate_input(test_results=[]) is False

    def test_validate_input_missing(self, detector):
        assert detector.validate_input() is False

    @pytest.mark.asyncio
    async def test_detect_flaky_flags_high_failure_rate(self, detector):
        results = []
        for i in range(10):
            status = TestStatus.FAILED if i < 3 else TestStatus.PASSED
            results.append(_make_result("flaky-1", status, days_ago=i))
        reports = await detector.detect_flaky(results)
        assert len(reports) == 1
        assert reports[0].test_id == "flaky-1"
        assert reports[0].failure_rate == 0.3

    @pytest.mark.asyncio
    async def test_detect_flaky_ignores_low_failure_rate(self, detector):
        results = []
        for i in range(20):
            status = TestStatus.FAILED if i < 1 else TestStatus.PASSED
            results.append(_make_result("stable-1", status, days_ago=i))
        reports = await detector.detect_flaky(results)
        assert len(reports) == 0

    @pytest.mark.asyncio
    async def test_detect_flaky_ignores_insufficient_data(self, detector):
        results = [
            _make_result("new-1", TestStatus.FAILED, days_ago=0),
            _make_result("new-1", TestStatus.PASSED, days_ago=1),
        ]
        reports = await detector.detect_flaky(results)
        assert len(reports) == 0

    def test_count_consecutive_failures(self):
        results = [
            _make_result("t1", TestStatus.PASSED, days_ago=0),
            _make_result("t1", TestStatus.FAILED, days_ago=1),
            _make_result("t1", TestStatus.FAILED, days_ago=2),
        ]
        assert FlakyTestDetector._count_consecutive_failures(results) == 1

    def test_recommend_action_fix(self):
        assert FlakyTestDetector._recommend_action(0.5, 6) == "fix"

    def test_recommend_action_quarantine(self):
        assert FlakyTestDetector._recommend_action(0.25, 3) == "quarantine"

    def test_recommend_action_investigate(self):
        assert FlakyTestDetector._recommend_action(0.12, 1) == "investigate"
