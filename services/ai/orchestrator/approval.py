"""
Approval Service for HumanApproval Nodes.

Handles webhook (with retry), email, and in-app notifications for human approval workflows.
Maintains complete audit trail with read receipts and timeout detection.
"""

from __future__ import annotations

import json
import uuid
import asyncio
import urllib.request
import urllib.error
from typing import Any, Optional
from datetime import datetime, timedelta
from enum import Enum
from dataclasses import dataclass, field


class ApprovalStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    TIMED_OUT = "timed_out"
    CANCELLED = "cancelled"


class NotificationChannel(str, Enum):
    WEBHOOK = "webhook"
    EMAIL = "email"
    IN_APP = "in_app"


class AuditAction(str, Enum):
    APPROVAL_CREATED = "approval_created"
    APPROVAL_APPROVED = "approval_approved"
    APPROVAL_REJECTED = "approval_rejected"
    APPROVAL_CANCELLED = "approval_cancelled"
    APPROVAL_TIMED_OUT = "approval_timed_out"
    WEBHOOK_SENT = "webhook_sent"
    WEBHOOK_FAILED = "webhook_failed"
    WEBHOOK_RETRY = "webhook_retry"
    EMAIL_SENT = "email_sent"
    EMAIL_FAILED = "email_failed"
    IN_APP_SENT = "in_app_sent"
    IN_APP_FAILED = "in_app_failed"
    READ_RECEIVED = "read_received"


@dataclass
class ReadReceipt:
    """Tracks when an approver has seen the notification."""
    approver_id: str
    read_at: str
    notification_id: str


@dataclass
class ApprovalRequest:
    """Represents a pending approval request."""
    request_id: str
    workflow_id: str
    execution_id: str
    node_id: str
    approvers: list[str]
    approval_type: str
    message: str
    timeout_hours: int
    channel: NotificationChannel
    webhook_url: Optional[str]
    created_at: str
    expires_at: str
    status: ApprovalStatus = ApprovalStatus.PENDING
    decision: Optional[str] = None
    comment: Optional[str] = None
    decision_by: Optional[str] = None
    decision_at: Optional[str] = None
    read_receipts: list[ReadReceipt] = field(default_factory=list)
    notification_ids: list[str] = field(default_factory=list)


@dataclass
class AuditEntry:
    """Audit trail entry for approval actions."""
    entry_id: str
    timestamp: str
    action: str
    actor: str
    details: dict[str, Any]
    workflow_id: str
    execution_id: str
    request_id: Optional[str] = None


class MockHTTPClient:
    """Mock HTTP client for testing webhook notifications."""

    def __init__(self) -> None:
        self.sent: list[dict[str, Any]] = []
        self.failed: list[dict[str, Any]] = []
        self.should_fail: bool = False
        self.fail_count: int = 0
        self.max_failures: int = 3

    def send(self, url: str, payload: dict[str, Any]) -> tuple[int, str]:
        """Simulate sending a webhook."""
        entry = {"url": url, "payload": payload}
        if self.should_fail and self.fail_count < self.max_failures:
            self.fail_count += 1
            self.failed.append(entry)
            raise urllib.error.URLError("Mock webhook failure")
        self.sent.append(entry)
        return 200, "OK"

    def reset(self) -> None:
        """Reset mock state."""
        self.sent.clear()
        self.failed.clear()
        self.fail_count = 0
        self.should_fail = False


class MockEmailService:
    """Mock email service for testing."""

    def __init__(self) -> None:
        self.sent: list[dict[str, Any]] = []
        self.failed: list[dict[str, Any]] = []

    async def send(self, to: list[str], subject: str, body: str) -> bool:
        """Simulate sending an email."""
        entry = {"to": to, "subject": subject, "body": body}
        self.sent.append(entry)
        return True

    def reset(self) -> None:
        """Reset mock state."""
        self.sent.clear()
        self.failed.clear()


class MockInAppService:
    """Mock in-app notification service."""

    def __init__(self) -> None:
        self.notifications: list[dict[str, Any]] = []
        self.read: list[dict[str, Any]] = []

    async def notify(
        self,
        user_id: str,
        type_: str,
        message: str,
        metadata: dict[str, Any]
    ) -> str:
        """Simulate sending an in-app notification."""
        notification_id = str(uuid.uuid4())
        self.notifications.append({
            "notification_id": notification_id,
            "user_id": user_id,
            "type": type_,
            "message": message,
            "metadata": metadata,
            "created_at": datetime.utcnow().isoformat()
        })
        return notification_id

    async def mark_read(self, user_id: str, notification_id: str) -> None:
        """Simulate marking a notification as read."""
        self.read.append({
            "user_id": user_id,
            "notification_id": notification_id,
            "read_at": datetime.utcnow().isoformat()
        })

    def reset(self) -> None:
        """Reset mock state."""
        self.notifications.clear()
        self.read.clear()


class ApprovalService:
    """
    Service for managing human approval workflows.

    Supports webhook (with retry), email, and in-app notifications.
    Maintains complete audit trail with read receipts.
    """

    MAX_WEBHOOK_RETRIES = 3
    WEBHOOK_RETRY_DELAY = 1.0  # seconds

    def __init__(
        self,
        webhook_url: Optional[str] = None,
        email_service: Optional[MockEmailService] = None,
        in_app_service: Optional[MockInAppService] = None,
        http_client: Optional[MockHTTPClient] = None
    ) -> None:
        self._approvals: dict[str, ApprovalRequest] = {}
        self._audit_trail: list[AuditEntry] = []
        self._webhook_url = webhook_url
        self._email_service = email_service or MockEmailService()
        self._in_app_service = in_app_service or MockInAppService()
        self._http_client = http_client or MockHTTPClient()

    async def create_approval_request(
        self,
        node_config: Any,
        workflow_id: str,
        execution_id: str,
        context: dict[str, Any]
    ) -> ApprovalRequest:
        """
        Create a new approval request.

        Sends notifications via configured channels.
        """
        request_id = str(uuid.uuid4())
        now = datetime.utcnow()
        expires = now + timedelta(hours=node_config.timeout_hours)

        channel_str = getattr(node_config, 'notification_channel', 'in_app')
        channel = self._resolve_channel(channel_str)

        approval = ApprovalRequest(
            request_id=request_id,
            workflow_id=workflow_id,
            execution_id=execution_id,
            node_id=node_config.node_id,
            approvers=list(node_config.approvers) if node_config.approvers else [],
            approval_type=getattr(node_config, 'approval_type', 'any'),
            message=context.get("message", f"Approval required for {workflow_id}"),
            timeout_hours=node_config.timeout_hours,
            channel=channel,
            webhook_url=getattr(node_config, 'webhook_url', None) or self._webhook_url,
            created_at=now.isoformat(),
            expires_at=expires.isoformat()
        )

        self._approvals[request_id] = approval
        self._log_audit(AuditAction.APPROVAL_CREATED.value, "system", {
            "request_id": request_id,
            "approvers": list(approval.approvers),
            "channel": channel.value,
            "expires_at": expires.isoformat()
        }, workflow_id, execution_id, request_id)

        # Send notifications with retry
        await self._send_notifications(approval)

        return approval

    async def approve(
        self,
        request_id: str,
        approver_id: str,
        comment: Optional[str] = None
    ) -> ApprovalRequest:
        """Approve a pending request."""
        approval = self._approvals.get(request_id)
        if not approval:
            raise ValueError(f"Approval request not found: {request_id}")
        if approval.status != ApprovalStatus.PENDING:
            raise ValueError(f"Approval is not pending: {approval.status}")
        if approver_id not in approval.approvers:
            raise ValueError(f"User {approver_id} is not an approver")

        approval.status = ApprovalStatus.APPROVED
        approval.decision = "approved"
        approval.comment = comment
        approval.decision_by = approver_id
        approval.decision_at = datetime.utcnow().isoformat()

        self._log_audit(AuditAction.APPROVAL_APPROVED.value, approver_id, {
            "comment": comment,
            "decision": "approved"
        }, approval.workflow_id, approval.execution_id, request_id)

        return approval

    async def reject(
        self,
        request_id: str,
        approver_id: str,
        comment: Optional[str] = None
    ) -> ApprovalRequest:
        """Reject a pending request."""
        approval = self._approvals.get(request_id)
        if not approval:
            raise ValueError(f"Approval request not found: {request_id}")
        if approval.status != ApprovalStatus.PENDING:
            raise ValueError(f"Approval is not pending: {approval.status}")
        if approver_id not in approval.approvers:
            raise ValueError(f"User {approver_id} is not an approver")

        approval.status = ApprovalStatus.REJECTED
        approval.decision = "rejected"
        approval.comment = comment
        approval.decision_by = approver_id
        approval.decision_at = datetime.utcnow().isoformat()

        self._log_audit(AuditAction.APPROVAL_REJECTED.value, approver_id, {
            "comment": comment,
            "decision": "rejected"
        }, approval.workflow_id, approval.execution_id, request_id)

        return approval

    async def cancel(self, request_id: str) -> ApprovalRequest:
        """Cancel a pending approval request."""
        approval = self._approvals.get(request_id)
        if not approval:
            raise ValueError(f"Approval request not found: {request_id}")
        if approval.status != ApprovalStatus.PENDING:
            raise ValueError(f"Approval is not pending: {approval.status}")

        approval.status = ApprovalStatus.CANCELLED
        self._log_audit(AuditAction.APPROVAL_CANCELLED.value, "system", {},
                       approval.workflow_id, approval.execution_id, request_id)

        return approval

    async def mark_read(
        self,
        request_id: str,
        approver_id: str
    ) -> AuditEntry:
        """Mark an approval notification as read by an approver."""
        approval = self._approvals.get(request_id)
        if not approval:
            raise ValueError(f"Approval request not found: {request_id}")

        receipt = ReadReceipt(
            approver_id=approver_id,
            read_at=datetime.utcnow().isoformat(),
            notification_id=str(uuid.uuid4())
        )
        approval.read_receipts.append(receipt)

        entry = self._log_audit(AuditAction.READ_RECEIVED.value, approver_id, {
            "read_at": receipt.read_at,
            "notification_id": receipt.notification_id
        }, approval.workflow_id, approval.execution_id, request_id)

        return entry

    def get_approval(self, request_id: str) -> Optional[ApprovalRequest]:
        """Get approval request by ID."""
        return self._approvals.get(request_id)

    def get_pending_approvals(self, workflow_id: Optional[str] = None) -> list[ApprovalRequest]:
        """Get all pending approvals, optionally filtered by workflow_id."""
        approvals = [
            a for a in self._approvals.values()
            if a.status == ApprovalStatus.PENDING
        ]
        if workflow_id:
            approvals = [a for a in approvals if a.workflow_id == workflow_id]
        return approvals

    def get_audit_trail(
        self,
        workflow_id: Optional[str] = None,
        execution_id: Optional[str] = None,
        request_id: Optional[str] = None
    ) -> list[AuditEntry]:
        """Get audit trail, optionally filtered."""
        entries = self._audit_trail
        if workflow_id:
            entries = [e for e in entries if e.workflow_id == workflow_id]
        if execution_id:
            entries = [e for e in entries if e.execution_id == execution_id]
        if request_id:
            entries = [e for e in entries if e.request_id == request_id]
        return entries

    async def check_timeout(self) -> list[ApprovalRequest]:
        """Check and timeout expired approval requests."""
        now = datetime.utcnow()
        timed_out = []

        for approval in list(self._approvals.values()):
            if approval.status == ApprovalStatus.PENDING:
                expires = datetime.fromisoformat(approval.expires_at)
                if now > expires:
                    approval.status = ApprovalStatus.TIMED_OUT
                    timed_out.append(approval)
                    self._log_audit(AuditAction.APPROVAL_TIMED_OUT.value, "system", {
                        "expires_at": approval.expires_at,
                        "timeout_hours": approval.timeout_hours
                    }, approval.workflow_id, approval.execution_id, approval.request_id)

        return timed_out

    async def _send_notifications(self, approval: ApprovalRequest) -> None:
        """Send notifications via configured channels with retry logic."""
        tasks = []

        if approval.channel == NotificationChannel.WEBHOOK and approval.webhook_url:
            tasks.append(self._send_webhook_with_retry(approval))
        elif approval.channel == NotificationChannel.EMAIL and self._email_service:
            tasks.append(self._send_email(approval))
        elif approval.channel == NotificationChannel.IN_APP and self._in_app_service:
            tasks.append(self._send_in_app(approval))

        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

    async def _send_webhook_with_retry(self, approval: ApprovalRequest) -> None:
        """Send webhook notification with retry logic."""
        payload = {
            "type": "approval_request",
            "request_id": approval.request_id,
            "workflow_id": approval.workflow_id,
            "execution_id": approval.execution_id,
            "message": approval.message,
            "approvers": approval.approvers,
            "expires_at": approval.expires_at,
            "actions": {
                "approve_url": f"/api/approvals/{approval.request_id}/approve",
                "reject_url": f"/api/approvals/{approval.request_id}/reject"
            }
        }

        last_error = None
        for attempt in range(self.MAX_WEBHOOK_RETRIES):
            try:
                status, reason = self._http_client.send(approval.webhook_url, payload)
                if status == 200:
                    self._log_audit(AuditAction.WEBHOOK_SENT.value, "system", {
                        "url": approval.webhook_url,
                        "attempt": attempt + 1,
                        "status": status
                    }, approval.workflow_id, approval.execution_id, approval.request_id)
                    approval.notification_ids.append(f"webhook_{approval.request_id}")
                    return
                else:
                    last_error = f"HTTP {status}: {reason}"
            except Exception as e:
                last_error = str(e)

            if attempt < self.MAX_WEBHOOK_RETRIES - 1:
                self._log_audit(AuditAction.WEBHOOK_RETRY.value, "system", {
                    "attempt": attempt + 1,
                    "error": last_error,
                    "delay": self.WEBHOOK_RETRY_DELAY
                }, approval.workflow_id, approval.execution_id, approval.request_id)
                await asyncio.sleep(self.WEBHOOK_RETRY_DELAY)

        # All retries exhausted
        self._log_audit(AuditAction.WEBHOOK_FAILED.value, "system", {
            "error": last_error,
            "request_id": approval.request_id,
            "attempts": self.MAX_WEBHOOK_RETRIES
        }, approval.workflow_id, approval.execution_id, approval.request_id)

    async def _send_email(self, approval: ApprovalRequest) -> None:
        """Send email notification."""
        if not self._email_service:
            return

        try:
            success = await self._email_service.send(
                to=approval.approvers,
                subject=f"Approval Request: {approval.workflow_id}",
                body=approval.message
            )
            if success:
                self._log_audit(AuditAction.EMAIL_SENT.value, "system", {
                    "to": approval.approvers,
                    "subject": f"Approval Request: {approval.workflow_id}"
                }, approval.workflow_id, approval.execution_id, approval.request_id)
                approval.notification_ids.append(f"email_{approval.request_id}")
            else:
                raise Exception("Email service returned failure")
        except Exception as e:
            self._log_audit(AuditAction.EMAIL_FAILED.value, "system", {
                "error": str(e),
                "request_id": approval.request_id
            }, approval.workflow_id, approval.execution_id, approval.request_id)

    async def _send_in_app(self, approval: ApprovalRequest) -> None:
        """Send in-app notification with read tracking."""
        if not self._in_app_service:
            return

        try:
            notification_ids = []
            for approver in approval.approvers:
                notif_id = await self._in_app_service.notify(
                    user_id=approver,
                    type_="approval_request",
                    message=approval.message,
                    metadata={
                        "request_id": approval.request_id,
                        "workflow_id": approval.workflow_id,
                        "execution_id": approval.execution_id
                    }
                )
                notification_ids.append(notif_id)

            self._log_audit(AuditAction.IN_APP_SENT.value, "system", {
                "approvers": approval.approvers,
                "notification_ids": notification_ids
            }, approval.workflow_id, approval.execution_id, approval.request_id)
            approval.notification_ids.extend(notification_ids)
        except Exception as e:
            self._log_audit(AuditAction.IN_APP_FAILED.value, "system", {
                "error": str(e),
                "request_id": approval.request_id
            }, approval.workflow_id, approval.execution_id, approval.request_id)

    def _resolve_channel(self, channel_str: str) -> NotificationChannel:
        """Resolve channel string to enum."""
        try:
            return NotificationChannel(channel_str)
        except ValueError:
            return NotificationChannel.IN_APP

    def _log_audit(
        self,
        action: str,
        actor: str,
        details: dict[str, Any],
        workflow_id: str,
        execution_id: str,
        request_id: Optional[str] = None
    ) -> AuditEntry:
        """Log an audit trail entry."""
        entry = AuditEntry(
            entry_id=str(uuid.uuid4()),
            timestamp=datetime.utcnow().isoformat(),
            action=action,
            actor=actor,
            details=details,
            workflow_id=workflow_id,
            execution_id=execution_id,
            request_id=request_id
        )
        self._audit_trail.append(entry)
        return entry

    def get_read_receipts(self, request_id: str) -> list[ReadReceipt]:
        """Get read receipts for an approval request."""
        approval = self._approvals.get(request_id)
        if approval:
            return approval.read_receipts
        return []



