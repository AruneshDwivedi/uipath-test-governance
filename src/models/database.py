"""
Database models for test governance data.

Uses SQLAlchemy for ORM. All state lives in PostgreSQL — agents are
stateless and read/write through these models.

[STATED] We use SQLAlchemy 2.0+ with async support (asyncpg driver).
[INFERRED] Timestamps use UTC throughout — no timezone-aware columns needed
since all agents run in the same UiPath Automation Cloud region.
"""

from __future__ import annotations

import enum
from datetime import datetime
from typing import Optional

from sqlalchemy import (
    Boolean, Column, DateTime, Enum, Float, ForeignKey,
    Integer, String, Text, JSON, Index
)
from sqlalchemy.orm import DeclarativeBase, relationship
from sqlalchemy.sql import func


class Base(DeclarativeBase):
    pass


class RiskLevel(enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class TestStatus(enum.Enum):
    PASSED = "passed"
    FAILED = "failed"
    SKIPPED = "skipped"
    FLAKY = "flaky"
    UNKNOWN = "unknown"


class EscalationStatus(enum.Enum):
    PENDING = "pending"
    ACKNOWLEDGED = "acknowledged"
    RESOLVED = "resolved"
    DISMISSED = "dismissed"


class Workflow(Base):
    """A UiPath workflow being tracked for test governance."""
    __tablename__ = "workflows"

    id = Column(String(36), primary_key=True)
    name = Column(String(255), nullable=False)
    project_id = Column(String(36), nullable=False, index=True)
    description = Column(Text, default="")
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())

    # Relationships
    test_mappings = relationship("TestMapping", back_populates="workflow")
    changes = relationship("WorkflowChange", back_populates="workflow")
    coverage_reports = relationship("CoverageReport", back_populates="workflow")


class TestCase(Base):
    """A test case in UiPath Test Cloud."""
    __tablename__ = "test_cases"

    id = Column(String(36), primary_key=True)
    name = Column(String(255), nullable=False)
    test_cloud_id = Column(String(36), unique=True, nullable=False)
    project_id = Column(String(36), nullable=False, index=True)
    description = Column(Text, default="")
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, server_default=func.now())

    # Relationships
    mappings = relationship("TestMapping", back_populates="test_case")
    results = relationship("TestResult", back_populates="test_case")


class TestMapping(Base):
    """Maps workflow files to test cases (which tests cover which files)."""
    __tablename__ = "test_mappings"

    id = Column(Integer, primary_key=True, autoincrement=True)
    workflow_id = Column(String(36), ForeignKey("workflows.id"), nullable=False)
    test_case_id = Column(String(36), ForeignKey("test_cases.id"), nullable=False)
    file_pattern = Column(String(500), nullable=False)  # glob pattern
    confidence = Column(Float, default=1.0)  # how sure is this mapping
    created_at = Column(DateTime, server_default=func.now())

    __table_args__ = (
        Index("idx_workflow_test", "workflow_id", "test_case_id"),
    )

    workflow = relationship("Workflow", back_populates="test_mappings")
    test_case = relationship("TestCase", back_populates="mappings")


class WorkflowChange(Base):
    """A detected change to a workflow (trigger for impact analysis)."""
    __tablename__ = "workflow_changes"

    id = Column(Integer, primary_key=True, autoincrement=True)
    workflow_id = Column(String(36), ForeignKey("workflows.id"), nullable=False)
    changed_files = Column(JSON, nullable=False)  # list of file paths
    diff_summary = Column(Text, default="")
    author = Column(String(255), default="")
    risk_level = Column(Enum(RiskLevel), default=RiskLevel.MEDIUM)
    analyzed = Column(Boolean, default=False)
    created_at = Column(DateTime, server_default=func.now())

    workflow = relationship("Workflow", back_populates="changes")


class TestResultRecord(Base):
    """Historical test execution results."""
    __tablename__ = "test_results"

    id = Column(Integer, primary_key=True, autoincrement=True)
    test_case_id = Column(String(36), ForeignKey("test_cases.id"), nullable=False)
    status = Column(Enum(TestStatus), nullable=False)
    duration_ms = Column(Integer, default=0)
    error_message = Column(Text, default="")
    run_id = Column(String(36), nullable=False, index=True)
    executed_at = Column(DateTime, server_default=func.now())

    __table_args__ = (
        Index("idx_test_date", "test_case_id", "executed_at"),
    )

    test_case = relationship("TestCase", back_populates="results")


class FlakyTestRecord(Base):
    """Tracks tests that have been flagged as flaky."""
    __tablename__ = "flaky_tests"

    id = Column(Integer, primary_key=True, autoincrement=True)
    test_case_id = Column(String(36), ForeignKey("test_cases.id"), nullable=False)
    failure_rate = Column(Float, nullable=False)
    consecutive_failures = Column(Integer, default=0)
    recommended_action = Column(String(50), default="investigate")
    is_quarantined = Column(Boolean, default=False)
    detected_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())


class CoverageReportRecord(Base):
    """Coverage report snapshots over time."""
    __tablename__ = "coverage_reports"

    id = Column(Integer, primary_key=True, autoincrement=True)
    workflow_id = Column(String(36), ForeignKey("workflows.id"), nullable=False)
    total_test_cases = Column(Integer, default=0)
    executed = Column(Integer, default=0)
    covered = Column(Integer, default=0)
    coverage_percentage = Column(Float, default=0.0)
    gaps = Column(JSON, default=[])  # list of uncovered areas
    trend = Column(String(20), default="stable")
    generated_at = Column(DateTime, server_default=func.now())

    workflow = relationship("Workflow", back_populates="coverage_reports")


class EscalationRecord(Base):
    """Human-in-the-loop escalation requests."""
    __tablename__ = "escalations"

    id = Column(String(36), primary_key=True)
    source_agent = Column(String(50), nullable=False)
    reason = Column(Text, nullable=False)
    context = Column(JSON, default={})
    suggested_action = Column(Text, default="")
    urgency = Column(Enum(RiskLevel), default=RiskLevel.MEDIUM)
    status = Column(Enum(EscalationStatus), default=EscalationStatus.PENDING)
    resolved_by = Column(String(255), default="")
    resolution_note = Column(Text, default="")
    created_at = Column(DateTime, server_default=func.now())
    resolved_at = Column(DateTime, nullable=True)

    __table_args__ = (
        Index("idx_escalation_status", "status", "urgency"),
    )
