# ADR-001: Agent Architecture and Orchestration Model

## Status: Accepted

## Context

We need to coordinate 5 distinct agents (Impact Analyzer, Test Orchestrator,
Flaky Detector, Coverage Reporter, Escalation Manager) that operate on
UiPath Test Cloud data. The hackathon requires the solution to run on
UiPath Automation Cloud with Maestro as the orchestration layer.

## Decision

**Architecture:** Each agent is a stateless Python class implementing a
common `BaseAgent` interface. State lives in PostgreSQL. Agents are
orchestrated by a `TestGovernanceOrchestrator` that implements the
BPMN process flow.

**Orchestration:** UiPath Maestro BPMN coordinates the high-level flow:
trigger → impact analysis → test execution → reporting. Each BPMN
service task calls into the Python agent code via UiPath API Workflows.

**Human-in-the-loop:** Every agent has a confidence threshold. Below the
threshold, an `EscalationRequest` is created and routed to a human
reviewer via the Escalation Manager. This is a first-class feature, not
an afterthought.

**Why LangChain + LangGraph over pure UiPath Agent Builder:**
- LangChain provides better LLM orchestration for the Impact Analyzer
  (reasoning over code diffs)
- UiPath Agent Builder is used for the low-level test execution actions
- The hybrid approach scores bonus points in the hackathon

## Consequences

- (+) Clean separation of concerns — each agent is independently testable
- (+) Human escalation is built into every agent's interface
- (+) BPMN process is visible and auditable in UiPath Maestro
- (-) Requires both Python infrastructure and UiPath platform setup
- (-) More moving parts than a pure low-code solution

## Labels

[STATED] Agents are stateless — state in PostgreSQL
[STATED] Human-in-the-loop via EscalationRequest on low confidence
[INFERRED] LangChain for LLM reasoning based on hackathon's coding agent bonus criteria
[INFERRED] Maestro BPMN for orchestration based on Track 3 requirements
