"""Unit tests for Test Impact Analyzer agent."""

import pytest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

from src.agents.impact_analyzer import TestImpactAnalyzer
from src.models.interfaces import RiskLevel, WorkflowChange


@pytest.fixture
def mock_db():
    return AsyncMock()


@pytest.fixture
def mock_llm():
    mock = AsyncMock()
    mock.ainvoke.return_value = '{"risk_level": "medium", "additional_tests": []}'
    return mock


@pytest.fixture
def mock_test_cloud():
    return AsyncMock()


@pytest.fixture
def analyzer(mock_db, mock_llm, mock_test_cloud):
    return TestImpactAnalyzer(
        db_session=mock_db,
        llm_client=mock_llm,
        test_cloud_client=mock_test_cloud,
    )


@pytest.fixture
def sample_change():
    return WorkflowChange(
        workflow_id="wf-001",
        workflow_name="InvoiceProcessing",
        changed_files=["Selectors/invoice.xaml", "Main.xaml"],
        diff_summary="Updated invoice parsing logic",
        author="test-user",
    )


class TestImpactAnalyzer:
    def test_validate_input_valid(self, analyzer, sample_change):
        assert analyzer.validate_input(change=sample_change) is True

    def test_validate_input_missing_change(self, analyzer):
        assert analyzer.validate_input() is False

    def test_validate_input_empty_files(self, analyzer):
        change = WorkflowChange(
            workflow_id="wf-001",
            workflow_name="Test",
            changed_files=[],
            diff_summary="",
        )
        assert analyzer.validate_input(change=change) is False

    @pytest.mark.asyncio
    async def test_analyze_impact_returns_test_impact(
        self, analyzer, sample_change
    ):
        result = await analyzer.analyze_impact(sample_change)
        assert result.change == sample_change
        assert isinstance(result.risk_level, RiskLevel)
        assert 0.0 <= result.confidence <= 1.0

    @pytest.mark.asyncio
    async def test_analyze_impact_high_risk_for_many_files(self, analyzer):
        change = WorkflowChange(
            workflow_id="wf-001",
            workflow_name="BigWorkflow",
            changed_files=[f"file_{i}.xaml" for i in range(15)],
            diff_summary="Major refactor",
        )
        result = await analyzer.analyze_impact(change)
        assert result.risk_level == RiskLevel.HIGH

    @pytest.mark.asyncio
    async def test_analyze_impact_escalates_on_low_confidence(
        self, analyzer
    ):
        change = WorkflowChange(
            workflow_id="wf-001",
            workflow_name="Unknown",
            changed_files=["obscure_file.xaml"],
            diff_summary="Unknown changes",
        )
        result = await analyzer.analyze_impact(change)
        assert result.requires_human_review is True

    @pytest.mark.asyncio
    async def test_get_affected_tests_empty(self, analyzer):
        result = await analyzer.get_affected_tests(["file.xaml"])
        assert result == []

    def test_should_escalate_below_threshold(self, analyzer):
        assert analyzer.should_escalate(0.5) is True

    def test_should_not_escalate_above_threshold(self, analyzer):
        assert analyzer.should_escalate(0.9) is False
