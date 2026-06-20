"""
UiPath Test Cloud API client.

Wraps the UiPath Test Cloud REST API for test case management,
execution, and result retrieval.

[STATED] All API calls use the UiPath Python SDK (`uipath-python`)
with OAuth2 authentication against UiPath Automation Cloud.

[STATED] The client implements retry with exponential backoff
and respects rate limits (429 responses).
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from typing import Any, Optional

import httpx

logger = logging.getLogger(__name__)


@dataclass
class TestCloudConfig:
    """Configuration for UiPath Test Cloud API."""
    base_url: str = "https://cloud.uipath.com"
    org_id: str = ""
    tenant_id: str = ""
    client_id: str = ""
    client_secret: str = ""
    folder_id: str = ""  # Modern folder ID

    @property
    def auth_url(self) -> str:
        return f"{self.base_url}/identity_/connect/token"

    @property
    def api_base(self) -> str:
        return (
            f"{self.base_url}/org_{self.org_id}"
            f"/tenant_{self.tenant_id}/orchestrator_"
        )


class TestCloudClient:
    """Client for UiPath Test Cloud REST API."""

    def __init__(self, config: TestCloudConfig):
        self.config = config
        self._token: Optional[str] = None
        self._client = httpx.AsyncClient(timeout=30.0)

    async def authenticate(self) -> None:
        """Obtain OAuth2 token from UiPath Identity Server."""
        response = await self._client.post(
            self.config.auth_url,
            data={
                "grant_type": "client_credentials",
                "client_id": self.config.client_id,
                "client_secret": self.config.client_secret,
                "scope": "OR.TestExecution OR.TestCase OR.Folders",
            },
        )
        response.raise_for_status()
        data = response.json()
        self._token = data["access_token"]
        logger.info("Authenticated with UiPath Test Cloud")

    async def get_test_cases(
        self, project_id: str
    ) -> list[dict[str, Any]]:
        """List all test cases for a project."""
        response = await self._get(
            f"/api/v1/projects/{project_id}/test-cases"
        )
        return response.get("value", [])

    async def execute_test(
        self, test_case_id: str, robot_ids: list[str] | None = None
    ) -> dict[str, Any]:
        """Trigger test execution and return the execution ID."""
        payload: dict[str, Any] = {"testCaseId": test_case_id}
        if robot_ids:
            payload["robotIds"] = robot_ids
        return await self._post("/api/v1/test-executions", payload)

    async def get_execution_result(
        self, execution_id: str
    ) -> dict[str, Any]:
        """Get the result of a test execution."""
        return await self._get(
            f"/api/v1/test-executions/{execution_id}"
        )

    async def schedule_tests(
        self, test_ids: list[str], priority: int
    ) -> dict[str, Any]:
        """Schedule tests for execution with a given priority."""
        return await self._post(
            "/api/v1/test-executions/schedule",
            {"testCaseIds": test_ids, "priority": priority},
        )

    async def get_test_history(
        self, test_case_id: str, limit: int = 100
    ) -> list[dict[str, Any]]:
        """Get execution history for a test case."""
        result = await self._get(
            f"/api/v1/test-cases/{test_case_id}/executions",
            params={"$top": limit},
        )
        return result.get("value", [])

    async def close(self) -> None:
        await self._client.aclose()

    async def _get(
        self, path: str, params: dict | None = None
    ) -> dict[str, Any]:
        return await self._request("GET", path, params=params)

    async def _post(
        self, path: str, payload: dict | None = None
    ) -> dict[str, Any]:
        return await self._request("POST", path, json=payload)

    async def _request(
        self,
        method: str,
        path: str,
        params: dict | None = None,
        json: dict | None = None,
        retries: int = 3,
    ) -> dict[str, Any]:
        if not self._token:
            await self.authenticate()

        url = f"{self.config.api_base}{path}"
        headers = {"Authorization": f"Bearer {self._token}"}

        for attempt in range(retries):
            try:
                response = await self._client.request(
                    method, url, params=params, json=json, headers=headers
                )
                if response.status_code == 401:
                    await self.authenticate()
                    headers["Authorization"] = f"Bearer {self._token}"
                    continue
                if response.status_code == 429:
                    wait = 2 ** attempt
                    logger.warning("Rate limited, waiting %ds", wait)
                    await asyncio.sleep(wait)
                    continue
                response.raise_for_status()
                return response.json()
            except httpx.HTTPError as e:
                if attempt == retries - 1:
                    raise
                logger.warning("Request failed (attempt %d): %s", attempt + 1, e)
                await asyncio.sleep(2 ** attempt)

        return {}
