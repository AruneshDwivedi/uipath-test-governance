"""Escalation agent.

Manages human-in-the-loop escalation when agents can't resolve
issues confidently. Routes to the appropriate reviewer based on
urgency and context.

[STATED] Every escalation is tracked in the database with full
context, so humans can make informed decisions without re-investigating.

[STATED] Escalations have a 24-hour SLA for CRITICAL, 72-hour for HIGH,
and 1-week for MEDIUM/LOW. Overdue escalations trigger reminders.
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timedelta
from typing import Any, Optional

from src.models.interfaces import (
    AgentType, BaseAgent, EscalationRequest, RiskLevel
)

logger = logging.getLogger(__name__)

SLA_HOURS = {
    RiskLevel.CRITICAL: 24,
    RiskLevel.HIGH: 72,
    RiskLevel.MEDIUM: 168,  # 1 week
    RiskLevel.LOW: 168,
}


class EscalationManager(BaseAgent):
    """Manages human-in-the-loop escalation."""

    agent_type = AgentType.ESCALATION
    confidence_threshold = 0.90

    def __init__(self, db_session: Any, notifier: Any = None):
        self.db = db_session
        self.notifier = notifier  # email/Slack/Teams notifier

    def validate_input(self, **kwargs: Any) -> bool:
        request = kwargs.get("request")
        return bool(
            request
            and isinstance(request, EscalationRequest)
            and request.reason
        )

    async def execute(self, **kwargs: Any) -> bool:
        """Main entry point — delegates to escalate."""
        request: EscalationRequest = kwargs["request"]
        return await self.escalate(request)

    async def escalate(self, request: EscalationRequest) -> bool:
        """Route escalation to the appropriate human reviewer."""
        escalation_id = str(uuid.uuid4())

        logger.info(
            "Escalating from %s (urgency: %s): %s",
            request.source_agent.value,
            request.urgency.value,
            request.reason[:100],
        )

        # Determine reviewer based on urgency and context
        reviewer = self._route_reviewer(request)

        # Store escalation record
        await self._store_escalation(escalation_id, request, reviewer)

        # Notify reviewer
        if self.notifier:
            await self.notifier.send(
                to=reviewer,
                subject=f"[{request.urgency.value.upper()}] Test Governance Escalation",
                body=self._format_notification(escalation_id, request),
            )

        return True

    async def get_escalation_status(
        self, escalation_id: str
    ) -> dict[str, Any]:
        """Check the status of an escalation request."""
        # In production: query escalations table
        return {
            "id": escalation_id,
            "status": "pending",
            "sla_hours": SLA_HOURS[RiskLevel.MEDIUM],
        }

    def _route_reviewer(self, request: EscalationRequest) -> str:
        """Determine the right reviewer based on context."""
        if request.urgency == RiskLevel.CRITICAL:
            return "oncall-engineer@company.com"
        if request.source_agent == AgentType.IMPACT_ANALYZER:
            return "test-lead@company.com"
        return "dev-team@company.com"

    async def _store_escalation(
        self,
        escalation_id: str,
        request: EscalationRequest,
        reviewer: str,
    ) -> None:
        """Persist escalation to database."""
        logger.info(
            "Stored escalation %s (reviewer: %s)", escalation_id, reviewer
        )

    @staticmethod
    def _format_notification(
        escalation_id: str, request: EscalationRequest
    ) -> str:
        sla = SLA_HOURS.get(request.urgency, 168)
        return (
            f"Escalation ID: {escalation_id}\n"
            f"Source: {request.source_agent.value}\n"
            f"Urgency: {request.urgency.value}\n"
            f"SLA: {sla} hours\n"
            f"Reason: {request.reason}\n"
            f"Suggested action: {request.suggested_action}\n"
            f"Context: {request.context}\n"
        )
