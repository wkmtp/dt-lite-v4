"""
Tests for ApprovalService: webhook retry, in-app read receipts,
timeout detection, audit trail completeness.
All tests are self-contained — no external HTTP/DB dependencies.
"""
from __future__ import annotations

import asyncio
import pytest
from datetime import datetime, timedelta
from uuid import uuid4

from services.ai.orchestrator.approval import (
    ApprovalService, ApprovalStatus, NotificationChannel,
    MockHTTPClient, MockEmailService, MockInAppService,
    AuditAction,
)
from services.ai.orchestrator.dsl import HumanApprovalNodeConfig


# ── helpers ──────────────────────────────────────────────────────────────────

def _make_approval_node(
    node_id: str = "approve",
    approvers: list[str] | None = None,
    timeout_hours: int = 24,
    channel: str = "in_app",
) -> HumanApprovalNodeConfig:
    return HumanApprovalNodeConfig(
        node_id=node_id,
        node_type=ApprovalStatus.__class__.__mro__[1].__name__.lower(),  # dummy — overridden below
        label="Approve",
        approvers=approvers or ["user-1", "user-2"],
        timeout_hours=timeout_hours,
        notification_channel=channel,
    )


def _make_service(
    channel: str = "in_app",
    http_client: MockHTTPClient | None = None,
    email_service: MockEmailService | None = None,
    in_app_service: MockInAppService | None = None,
) -> ApprovalService:
    return ApprovalService(
        http_client=http_client or MockHTTPClient(),
        email_service=email_service or MockEmailService(),
        in_app_service=in_app_service or MockInAppService(),
    )


# ── 1. Create approval request ───────────────────────────────────────────────

class TestCreateApprovalRequest:
    @pytest.mark.asyncio
    async def test_create_in_app_approval(self):
        service = _make_service(channel="in_app")
        node = _make_approval_node(channel="in_app")
        approval = await service.create_approval_request(
            node, "wf-1", "exec-1", {}
        )
        assert approval.status == ApprovalStatus.PENDING
        assert approval.workflow_id == "wf-1"
        assert approval.execution_id == "exec-1"
        assert "user-1" in approval.approvers
        assert "user-2" in approval.approvers
        assert approval.expires_at > approval.created_at

    @pytest.mark.asyncio
    async def test_create_webhook_approval(self):
        http_client = MockHTTPClient()
        service = _make_service(channel="webhook", http_client=http_client)
        node = _make_approval_node(channel="webhook")
        approval = await service.create_approval_request(
            node, "wf-2", "exec-2", {}
        )
        assert approval.status == ApprovalStatus.PENDING
        assert len(http_client.sent) == 1
        payload = http_client.sent[0]["payload"]
        assert payload["type"] == "approval_request"
        assert payload["request_id"] == approval.request_id

    @pytest.mark.asyncio
    async def test_create_email_approval(self):
        email_service = MockEmailService()
        service = _make_service(channel="email", email_service=email_service)
        node = _make_approval_node(channel="email")
        approval = await service.create_approval_request(
            node, "wf-3", "exec-3", {}
        )
        assert approval.status == ApprovalStatus.PENDING
        assert len(email_service.sent) == 1
        assert "user-1" in email_service.sent[0]["to"]

    @pytest.mark.asyncio
    async def test_get_pending_approvals(self):
        service = _make_service()
        await service.create_approval_request(
            _make_approval_node(channel="in_app"), "wf-1", "exec-1", {}
        )
        pending = service.get_pending_approvals()
        assert len(pending) == 1
        assert pending[0].status == ApprovalStatus.PENDING

    @pytest.mark.asyncio
    async def test_get_approval_by_id(self):
        service = _make_service()
        node = _make_approval_node(channel="in_app")
        approval = await service.create_approval_request(node, "wf-1", "exec-1", {})
        fetched = service.get_approval(approval.request_id)
        assert fetched is not None
        assert fetched.request_id == approval.request_id
        assert fetched.status == ApprovalStatus.PENDING


# ── 2. Approve / Reject / Cancel ────────────────────────────────────────────

class TestApproveRejectCancel:
    @pytest.mark.asyncio
    async def test_approve(self):
        service = _make_service()
        node = _make_approval_node(channel="in_app")
        approval = await service.create_approval_request(node, "wf-1", "exec-1", {})
        result = await service.approve(approval.request_id, "user-1", "Looks good")
        assert result.status == ApprovalStatus.APPROVED
        assert result.decision_by == "user-1"
        assert result.comment == "Looks good"
        assert result.decision_at is not None

    @pytest.mark.asyncio
    async def test_reject(self):
        service = _make_service()
        node = _make_approval_node(channel="in_app")
        approval = await service.create_approval_request(node, "wf-1", "exec-1", {})
        result = await service.reject(approval.request_id, "user-2", "Not approved")
        assert result.status == ApprovalStatus.REJECTED
        assert result.decision == "rejected"

    @pytest.mark.asyncio
    async def test_cancel(self):
        service = _make_service()
        node = _make_approval_node(channel="in_app")
        approval = await service.create_approval_request(node, "wf-1", "exec-1", {})
        result = await service.cancel(approval.request_id)
        assert result.status == ApprovalStatus.CANCELLED

    @pytest.mark.asyncio
    async def test_approve_nonexistent_raises(self):
        service = _make_service()
        with pytest.raises(ValueError, match="not found"):
            await service.approve("nonexistent", "user-1")

    @pytest.mark.asyncio
    async def test_double_approve_raises(self):
        service = _make_service()
        node = _make_approval_node(channel="in_app")
        approval = await service.create_approval_request(node, "wf-1", "exec-1", {})
        await service.approve(approval.request_id, "user-1")
        with pytest.raises(ValueError, match="not pending"):
            await service.approve(approval.request_id, "user-1")

    @pytest.mark.asyncio
    async def test_unauthorized_approver_raises(self):
        service = _make_service()
        node = _make_approval_node(channel="in_app", approvers=["user-1"])
        approval = await service.create_approval_request(node, "wf-1", "exec-1", {})
        with pytest.raises(ValueError, match="not an approver"):
            await service.approve(approval.request_id, "user-99")


# ── 3. Timeout detection ────────────────────────────────────────────────────

class TestTimeoutDetection:
    @pytest.mark.asyncio
    async def test_timeout_check_identifies_expired(self):
        service = _make_service()
        # Create an approval with 0-hour timeout (already expired)
        node = _make_approval_node(channel="in_app", timeout_hours=0)
        approval = await service.create_approval_request(node, "wf-1", "exec-1", {})
        # Manually set expires_at to the past
        approval.expires_at = (
            datetime.utcnow() - timedelta(hours=1)
        ).isoformat()
        timed_out = await service.check_timeout()
        assert len(timed_out) == 1
        assert timed_out[0].status == ApprovalStatus.TIMED_OUT

    @pytest.mark.asyncio
    async def test_timeout_check_passes_valid(self):
        service = _make_service()
        node = _make_approval_node(channel="in_app", timeout_hours=24)
        await service.create_approval_request(node, "wf-1", "exec-1", {})
        timed_out = await service.check_timeout()
        assert len(timed_out) == 0

    @pytest.mark.asyncio
    async def test_already_decided_not_timed_out(self):
        service = _make_service()
        node = _make_approval_node(channel="in_app", timeout_hours=0)
        approval = await service.create_approval_request(node, "wf-1", "exec-1", {})
        approval.expires_at = (datetime.utcnow() - timedelta(hours=1)).isoformat()
        await service.approve(approval.request_id, "user-1")
        timed_out = await service.check_timeout()
        assert len(timed_out) == 0


# ── 4. Audit trail completeness ─────────────────────────────────────────────

class TestAuditTrail:
    @pytest.mark.asyncio
    async def test_audit_entry_on_create(self):
        service = _make_service()
        node = _make_approval_node(channel="in_app")
        await service.create_approval_request(node, "wf-1", "exec-1", {})
        entries = service.get_audit_trail(workflow_id="wf-1")
        assert len(entries) >= 1
        assert entries[0].action == AuditAction.APPROVAL_CREATED.value
        assert entries[0].workflow_id == "wf-1"
        assert entries[0].execution_id == "exec-1"

    @pytest.mark.asyncio
    async def test_audit_entry_on_approve(self):
        service = _make_service()
        node = _make_approval_node(channel="in_app")
        approval = await service.create_approval_request(node, "wf-1", "exec-1", {})
        await service.approve(approval.request_id, "user-1")
        entries = service.get_audit_trail(request_id=approval.request_id)
        actions = [e.action for e in entries]
        assert AuditAction.APPROVAL_CREATED.value in actions
        assert AuditAction.APPROVAL_APPROVED.value in actions

    @pytest.mark.asyncio
    async def test_audit_entry_on_reject(self):
        service = _make_service()
        node = _make_approval_node(channel="in_app")
        approval = await service.create_approval_request(node, "wf-1", "exec-1", {})
        await service.reject(approval.request_id, "user-2")
        entries = service.get_audit_trail(request_id=approval.request_id)
        actions = [e.action for e in entries]
        assert AuditAction.APPROVAL_REJECTED.value in actions

    @pytest.mark.asyncio
    async def test_audit_entry_on_cancel(self):
        service = _make_service()
        node = _make_approval_node(channel="in_app")
        approval = await service.create_approval_request(node, "wf-1", "exec-1", {})
        await service.cancel(approval.request_id)
        entries = service.get_audit_trail(request_id=approval.request_id)
        actions = [e.action for e in entries]
        assert AuditAction.APPROVAL_CANCELLED.value in actions

    @pytest.mark.asyncio
    async def test_audit_entry_on_timeout(self):
        service = _make_service()
        node = _make_approval_node(channel="in_app", timeout_hours=0)
        approval = await service.create_approval_request(node, "wf-1", "exec-1", {})
        approval.expires_at = (datetime.utcnow() - timedelta(hours=1)).isoformat()
        await service.check_timeout()
        entries = service.get_audit_trail(request_id=approval.request_id)
        actions = [e.action for e in entries]
        assert AuditAction.APPROVAL_TIMED_OUT.value in actions

    @pytest.mark.asyncio
    async def test_audit_trail_filtered_by_execution(self):
        service = _make_service()
        node = _make_approval_node(channel="in_app")
        await service.create_approval_request(node, "wf-1", "exec-1", {})
        await service.create_approval_request(node, "wf-2", "exec-2", {})
        entries_exec1 = service.get_audit_trail(execution_id="exec-1")
        assert all(e.execution_id == "exec-1" for e in entries_exec1)

    @pytest.mark.asyncio
    async def test_audit_entry_has_required_fields(self):
        service = _make_service()
        node = _make_approval_node(channel="in_app")
        await service.create_approval_request(node, "wf-1", "exec-1", {})
        entries = service.get_audit_trail()
        for entry in entries:
            assert entry.entry_id
            assert entry.timestamp
            assert entry.action
            assert entry.actor
            assert entry.workflow_id
            assert entry.execution_id


# ── 5. Webhook retry ────────────────────────────────────────────────────────

class TestWebhookRetry:
    @pytest.mark.asyncio
    async def test_webhook_retry_on_failure(self):
        http_client = MockHTTPClient()
        http_client.should_fail = True
        http_client.max_failures = 2
        service = _make_service(channel="webhook", http_client=http_client)
        node = _make_approval_node(channel="webhook")
        await service.create_approval_request(node, "wf-1", "exec-1", {})
        # Should have attempted MAX_WEBHOOK_RETRIES times
        assert len(http_client.failed) == ApprovalService.MAX_WEBHOOK_RETRIES

    @pytest.mark.asyncio
    async def test_webhook_success_after_retry(self):
        http_client = MockHTTPClient()
        http_client.should_fail = True
        http_client.max_failures = 1
        service = _make_service(channel="webhook", http_client=http_client)
        node = _make_approval_node(channel="webhook")
        await service.create_approval_request(node, "wf-1", "exec-1", {})
        # First attempt fails, second succeeds
        assert len(http_client.sent) == 1
        assert len(http_client.failed) == 1


# ── 6. Read receipts ────────────────────────────────────────────────────────

class TestReadReceipts:
    @pytest.mark.asyncio
    async def test_mark_read(self):
        service = _make_service()
        node = _make_approval_node(channel="in_app")
        approval = await service.create_approval_request(node, "wf-1", "exec-1", {})
        entry = await service.mark_read(approval.request_id, "user-1")
        assert entry.action == AuditAction.READ_RECEIVED.value
        receipts = service.get_read_receipts(approval.request_id)
        assert len(receipts) == 1
        assert receipts[0].approver_id == "user-1"
        assert receipts[0].read_at is not None

    @pytest.mark.asyncio
    async def test_read_receipts_empty_for_nonexistent(self):
        service = _make_service()
        receipts = service.get_read_receipts("nonexistent")
        assert receipts == []


# ── 7. Multiple approvers ───────────────────────────────────────────────────

class TestMultipleApprovers:
    @pytest.mark.asyncio
    async def test_either_approver_can_approve(self):
        service = _make_service()
        node = _make_approval_node(channel="in_app", approvers=["user-1", "user-2"])
        approval = await service.create_approval_request(node, "wf-1", "exec-1", {})
        result = await service.approve(approval.request_id, "user-2")
        assert result.status == ApprovalStatus.APPROVED
