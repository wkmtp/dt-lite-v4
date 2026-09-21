"""WorkflowTriggerTool — wraps the Provisioning / Workflow API.

Allows the agent to trigger provisioning workflows and automation
pipelines on behalf of the tenant.

Supports:
- Synchronous execution (wait for result)
- Asynchronous execution (return execution ID)
- Execution status polling
- Workflow listing and inspection
"""
from __future__ import annotations

import asyncio
import logging
from typing import Any, Optional

import httpx
from pydantic import BaseModel, Field

from services.ai.config import AIConfig, get_ai_config

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Pydantic Schemas
# ---------------------------------------------------------------------------

class WorkflowStepResult(BaseModel):
    """Result of a single workflow step."""
    step_id: str = Field(..., description="Step UUID")
    step_type: str = Field(..., description="Step type: llm|tool|condition|branch")
    status: str = Field(..., description="Step status: pending|running|success|failed")
    input: dict[str, Any] = Field(default_factory=dict)
    output: Optional[dict[str, Any]] = Field(None)
    error: Optional[str] = Field(None)
    duration_ms: Optional[int] = Field(None)


class WorkflowExecution(BaseModel):
    """Workflow execution result."""
    execution_id: str = Field(..., description="Execution UUID")
    workflow_id: str = Field(..., description="Workflow UUID")
    workflow_code: str = Field(..., description="Workflow code identifier")
    status: str = Field(..., description="Execution status: running|success|failed|cancelled")
    tenant_id: str = Field(..., description="Tenant ID")
    started_at: str = Field(..., description="ISO-8601 start time")
    completed_at: Optional[str] = Field(None, description="ISO-8601 completion time")
    steps: list[WorkflowStepResult] = Field(default_factory=list)
    inputs: dict[str, Any] = Field(default_factory=dict)
    outputs: dict[str, Any] = Field(default_factory=dict)
    error: Optional[str] = Field(None)
    duration_ms: Optional[int] = Field(None)


class WorkflowInfo(BaseModel):
    """Workflow metadata."""
    workflow_id: str = Field(..., description="Workflow UUID")
    workflow_code: str = Field(..., description="Workflow code identifier")
    name: str = Field(..., description="Workflow name")
    description: Optional[str] = Field(None)
    version: str = Field(..., description="Workflow version")
    input_schema: dict[str, Any] = Field(default_factory=dict)
    output_schema: dict[str, Any] = Field(default_factory=dict)
    steps: list[dict[str, Any]] = Field(default_factory=list)
    is_active: bool = Field(True)


class WorkflowTriggerResult(BaseModel):
    """Result of a workflow trigger operation."""
    success: bool = Field(True, description="Whether the trigger succeeded")
    execution: Optional[WorkflowExecution] = Field(None, description="Execution result")
    workflow_info: Optional[WorkflowInfo] = Field(None, description="Workflow metadata")
    execution_id: Optional[str] = Field(None, description="Execution ID for async mode")
    error: Optional[str] = Field(None, description="Error message if any")
    error_code: Optional[str] = Field(None, description="Structured error code")


# ---------------------------------------------------------------------------
# Tool definition
# ---------------------------------------------------------------------------

class WorkflowTriggerTool:
    """Trigger a provisioning or automation workflow.

    Tool name: ``workflow_trigger``

    Input schema::

        {
            "workflow_code": "provision_device",
            "workflow_id": "<uuid>",
            "params": {"asset_id": "...", "template_id": "..."},
            "async_mode": false,
            "timeout_seconds": 60,
            "poll_interval_seconds": 5
        }
    """

    tool_name = "workflow_trigger"
    description = (
        "Trigger a provisioning or automation workflow in DT-Lite. "
        "Use this to start device provisioning, entity activation, "
        "or custom template-driven workflows. Supports both synchronous "
        "(blocking) and asynchronous execution modes. All workflows are "
        "scoped to the current tenant."
    )

    # Workflow codes the agent can trigger
    KNOWN_WORKFLOWS = {
        "provision_device": "Provision a new IoT device",
        "activate_entity": "Activate a digital twin entity",
        "bind_asset": "Bind asset to entity",
        "deactivate_entity": "Deactivate an entity",
        "delete_device": "Delete a device and clean up",
        "sync_telemetry": "Trigger telemetry sync",
        "run_diagnostic": "Run device diagnostic",
    }

    def __init__(self, tenant_id: str, config: Optional[AIConfig] = None) -> None:
        self.tenant_id = tenant_id
        self.config = config or get_ai_config()
        self._client = httpx.AsyncClient(
            base_url=self.config.GATEWAY_URL,
            timeout=60.0,
        )

    async def execute(
        self,
        tenant_id: str,
        workflow_code: Optional[str] = None,
        workflow_id: Optional[str] = None,
        params: Optional[dict[str, Any]] = None,
        async_mode: bool = False,
        timeout_seconds: int = 60,
        poll_interval_seconds: int = 5,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Execute a workflow trigger.

        Args:
            tenant_id: Caller's tenant (validated against self.tenant_id).
            workflow_code: Unique code identifying the workflow to run.
            workflow_id: Optional workflow UUID (alternative to workflow_code).
            params: Optional workflow parameters.
            async_mode: If True, run the workflow asynchronously.
            timeout_seconds: Max wait time for sync execution (default 60).
            poll_interval_seconds: Polling interval for async status checks (default 5).
            **kwargs: Ignored extra parameters.

        Returns:
            Dict with workflow execution result or an error.
        """
        # Tenant validation
        if tenant_id != self.tenant_id:
            return WorkflowTriggerResult(
                success=False,
                error="tenant_mismatch",
                error_code="ACCESS_DENIED",
            ).model_dump()

        # Validate workflow identifier
        if not workflow_code and not workflow_id:
            return WorkflowTriggerResult(
                success=False,
                error="missing_workflow_identifier",
                error_code="MISSING_PARAMS",
                message="Must provide either workflow_code or workflow_id",
            ).model_dump()

        # Validate timeout
        if timeout_seconds < 1 or timeout_seconds > 300:
            return WorkflowTriggerResult(
                success=False,
                error="invalid_timeout",
                error_code="INVALID_PARAMS",
                message="timeout_seconds must be between 1 and 300",
            ).model_dump()

        try:
            # Look up workflow if code is provided
            wf_id = workflow_id
            wf_info: Optional[WorkflowInfo] = None

            if workflow_code and not workflow_id:
                wf_info = await self._get_workflow_info(workflow_code)
                if wf_info:
                    wf_id = wf_info.workflow_id
                else:
                    # Try to find by code
                    wf_id = await self._find_workflow_by_code(workflow_code)

            if not wf_id:
                return WorkflowTriggerResult(
                    success=False,
                    error="workflow_not_found",
                    error_code="NOT_FOUND",
                    message=f"Workflow not found: {workflow_code or workflow_id}",
                ).model_dump()

            # Build execution payload
            payload: dict[str, Any] = {
                "workflow_id": wf_id,
                "inputs": params or {},
            }

            if async_mode:
                # Async mode: trigger and return immediately
                result = await self._trigger_async(payload)
                return WorkflowTriggerResult(
                    success=True,
                    execution=result,
                    workflow_info=wf_info,
                    execution_id=result.execution_id if result else None,
                ).model_dump()
            else:
                # Sync mode: trigger and wait for completion
                result = await self._trigger_sync(payload, timeout_seconds, poll_interval_seconds)
                return WorkflowTriggerResult(
                    success=True,
                    execution=result,
                    workflow_info=wf_info,
                ).model_dump()

        except httpx.HTTPStatusError as exc:
            status_code = exc.response.status_code
            error_detail = exc.response.text if exc.response.text else str(exc)

            if status_code == 404:
                logger.warning("Workflow trigger 404: %s", error_detail)
                return WorkflowTriggerResult(
                    success=False,
                    error="workflow_not_found",
                    error_code="NOT_FOUND",
                    message="Workflow not found or not accessible",
                ).model_dump()
            elif status_code == 400:
                logger.warning("Workflow trigger 400: %s", error_detail)
                return WorkflowTriggerResult(
                    success=False,
                    error="bad_request",
                    error_code="BAD_REQUEST",
                    message=f"Invalid workflow trigger request: {error_detail}",
                ).model_dump()
            elif status_code == 422:
                logger.warning("Workflow trigger 422: %s", error_detail)
                return WorkflowTriggerResult(
                    success=False,
                    error="validation_error",
                    error_code="VALIDATION_ERROR",
                    message=f"Workflow parameter validation failed: {error_detail}",
                ).model_dump()
            elif status_code == 500:
                logger.error("Workflow trigger 500: %s", error_detail)
                return WorkflowTriggerResult(
                    success=False,
                    error="internal_error",
                    error_code="INTERNAL_ERROR",
                    message="Workflow service internal error",
                ).model_dump()
            else:
                logger.warning("Workflow trigger HTTP error %d: %s", status_code, error_detail)
                return WorkflowTriggerResult(
                    success=False,
                    error=f"http_{status_code}",
                    error_code=f"HTTP_{status_code}",
                    message=f"Workflow trigger failed with status {status_code}",
                ).model_dump()
        except httpx.TimeoutException:
            logger.error("Workflow trigger timeout after 60s")
            return WorkflowTriggerResult(
                success=False,
                error="timeout",
                error_code="TIMEOUT",
                message="Workflow trigger timed out after 60 seconds",
            ).model_dump()
        except httpx.ConnectError as exc:
            logger.error("Workflow trigger connection error: %s", exc)
            return WorkflowTriggerResult(
                success=False,
                error="connection_error",
                error_code="CONNECTION_ERROR",
                message=f"Failed to connect to workflow service: {exc}",
            ).model_dump()
        except Exception as exc:
            logger.error("Workflow trigger unexpected error: %s", exc, exc_info=True)
            return WorkflowTriggerResult(
                success=False,
                error="unexpected_error",
                error_code="UNEXPECTED_ERROR",
                message=f"Unexpected error during workflow trigger: {exc}",
            ).model_dump()

    async def _trigger_async(
        self,
        payload: dict[str, Any],
    ) -> Optional[WorkflowExecution]:
        """Trigger workflow asynchronously and return execution ID."""
        try:
            resp = await self._client.post(
                "/api/v1/workflows/execute",
                json=payload,
                headers={
                    "X-Tenant-ID": self.tenant_id,
                    "Content-Type": "application/json",
                },
            )
            resp.raise_for_status()
            data = resp.json()

            execution_data = data.get("data", data)
            return WorkflowExecution(
                execution_id=execution_data.get("execution_id", execution_data.get("id", "")),
                workflow_id=execution_data.get("workflow_id", payload.get("workflow_id", "")),
                workflow_code=execution_data.get("workflow_code", ""),
                status=execution_data.get("status", "running"),
                tenant_id=self.tenant_id,
                started_at=execution_data.get("started_at", ""),
                steps=[
                    WorkflowStepResult(**s) if isinstance(s, dict) else s
                    for s in execution_data.get("steps", [])
                ],
                inputs=execution_data.get("inputs", payload.get("inputs", {})),
                outputs=execution_data.get("outputs", {}),
                error=execution_data.get("error"),
            )
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == 409:
                # Workflow already running
                logger.info("Workflow already running, returning existing execution")
                return None
            raise

    async def _trigger_sync(
        self,
        payload: dict[str, Any],
        timeout_seconds: int,
        poll_interval_seconds: int,
    ) -> Optional[WorkflowExecution]:
        """Trigger workflow synchronously and wait for completion."""
        # First trigger the workflow
        execution = await self._trigger_async(payload)
        if not execution:
            return None

        execution_id = execution.execution_id
        if not execution_id:
            return execution

        # Poll for completion
        deadline = asyncio.get_event_loop().time() + timeout_seconds
        while asyncio.get_event_loop().time() < deadline:
            try:
                resp = await self._client.get(
                    f"/api/v1/workflows/executions/{execution_id}",
                    headers={"X-Tenant-ID": self.tenant_id},
                )
                resp.raise_for_status()
                data = resp.json()
                exec_data = data.get("data", data)

                # Update execution with latest status
                execution.status = exec_data.get("status", execution.status)
                if exec_data.get("completed_at"):
                    execution.completed_at = exec_data["completed_at"]
                if exec_data.get("error"):
                    execution.error = exec_data["error"]
                if exec_data.get("outputs"):
                    execution.outputs = exec_data["outputs"]
                if exec_data.get("steps"):
                    execution.steps = [
                        WorkflowStepResult(**s) if isinstance(s, dict) else s
                        for s in exec_data["steps"]
                    ]

                # Check if completed
                if execution.status in ("success", "failed", "cancelled"):
                    return execution

                # Wait before next poll
                await asyncio.sleep(poll_interval_seconds)

            except httpx.HTTPStatusError as exc:
                if exc.response.status_code == 404:
                    execution.status = "failed"
                    execution.error = "Execution not found"
                    return execution
                raise
            except asyncio.TimeoutError:
                execution.status = "failed"
                execution.error = "Status polling timeout"
                return execution

        # Timeout reached
        execution.status = "timeout"
        execution.error = f"Workflow execution timed out after {timeout_seconds} seconds"
        return execution

    async def _get_workflow_info(
        self,
        workflow_code: str,
    ) -> Optional[WorkflowInfo]:
        """Get workflow metadata by code."""
        try:
            resp = await self._client.get(
                "/api/v1/workflows/list",
                headers={"X-Tenant-ID": self.tenant_id},
            )
            resp.raise_for_status()
            data = resp.json()
            workflows = data.get("data", data.get("results", []))

            for wf in workflows:
                if wf.get("workflow_code") == workflow_code or wf.get("code") == workflow_code:
                    return WorkflowInfo(
                        workflow_id=wf.get("id", wf.get("workflow_id", "")),
                        workflow_code=wf.get("workflow_code", wf.get("code", "")),
                        name=wf.get("name", ""),
                        description=wf.get("description"),
                        version=wf.get("version", "1.0"),
                        input_schema=wf.get("input_schema", {}),
                        output_schema=wf.get("output_schema", {}),
                        steps=wf.get("steps", []),
                        is_active=wf.get("is_active", wf.get("active", True)),
                    )
            return None
        except Exception as exc:
            logger.warning("Failed to get workflow info: %s", exc)
            return None

    async def _find_workflow_by_code(
        self,
        workflow_code: str,
    ) -> Optional[str]:
        """Find workflow ID by code."""
        info = await self._get_workflow_info(workflow_code)
        return info.workflow_id if info else None

    async def list_workflows(
        self,
        tenant_id: str,
        active_only: bool = False,
    ) -> dict[str, Any]:
        """List available workflows for the tenant.

        Args:
            tenant_id: Caller's tenant.
            active_only: Only return active workflows.

        Returns:
            Dict with list of workflows.
        """
        if tenant_id != self.tenant_id:
            return {"success": False, "error": "tenant_mismatch"}

        try:
            resp = await self._client.get(
                "/api/v1/workflows/list",
                headers={"X-Tenant-ID": self.tenant_id},
                params={"active_only": str(active_only).lower()},
            )
            resp.raise_for_status()
            data = resp.json()
            workflows = data.get("data", data.get("results", []))
            return {"success": True, "data": workflows, "count": len(workflows)}
        except httpx.HTTPStatusError as exc:
            return {"success": False, "error": str(exc)}
        except Exception as exc:
            logger.error("List workflows error: %s", exc, exc_info=True)
            return {"success": False, "error": str(exc)}

    async def get_execution_status(
        self,
        tenant_id: str,
        execution_id: str,
    ) -> dict[str, Any]:
        """Get the status of a workflow execution.

        Args:
            tenant_id: Caller's tenant.
            execution_id: Execution UUID.

        Returns:
            Dict with execution status.
        """
        if tenant_id != self.tenant_id:
            return {"success": False, "error": "tenant_mismatch"}

        try:
            resp = await self._client.get(
                f"/api/v1/workflows/executions/{execution_id}",
                headers={"X-Tenant-ID": self.tenant_id},
            )
            resp.raise_for_status()
            data = resp.json()
            return {"success": True, "data": data.get("data", data)}
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == 404:
                return {"success": False, "error": "execution_not_found"}
            return {"success": False, "error": str(exc)}
        except Exception as exc:
            logger.error("Get execution status error: %s", exc, exc_info=True)
            return {"success": False, "error": str(exc)}

    async def cancel_execution(
        self,
        tenant_id: str,
        execution_id: str,
    ) -> dict[str, Any]:
        """Cancel a running workflow execution.

        Args:
            tenant_id: Caller's tenant.
            execution_id: Execution UUID.

        Returns:
            Dict with cancellation result.
        """
        if tenant_id != self.tenant_id:
            return {"success": False, "error": "tenant_mismatch"}

        try:
            resp = await self._client.post(
                f"/api/v1/workflows/executions/{execution_id}/cancel",
                headers={"X-Tenant-ID": self.tenant_id},
            )
            resp.raise_for_status()
            data = resp.json()
            return {"success": True, "data": data.get("data", data)}
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == 404:
                return {"success": False, "error": "execution_not_found"}
            if exc.response.status_code == 409:
                return {"success": False, "error": "execution_not_running"}
            return {"success": False, "error": str(exc)}
        except Exception as exc:
            logger.error("Cancel execution error: %s", exc, exc_info=True)
            return {"success": False, "error": str(exc)}

    async def close(self) -> None:
        """Close the underlying HTTP client."""
        await self._client.aclose()

    async def __aenter__(self) -> "WorkflowTriggerTool":
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        await self.close()
