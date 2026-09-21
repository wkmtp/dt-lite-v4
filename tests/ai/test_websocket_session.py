"""Tests for WebSocket session management — auth, heartbeat, queue, reconnect."""

import pytest
import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch, PropertyMock
from datetime import datetime, timezone

from services.ai.api.websocket import (
    websocket_chat,
    WebSocketManager,
    _active_sessions,
    _message_queues,
    _session_metadata,
    _heartbeat_tasks,
    _verify_token,
    _get_session_id,
    _get_tenant_id,
    _get_user_id,
    _send_queued_messages,
    _queue_message,
    _start_heartbeat,
    _stop_heartbeat,
    router,
)


class TestVerifyToken:
    """Test token verification."""

    def test_valid_token(self):
        """Valid token should return payload."""
        payload = _verify_token("valid-test-token-12345")
        assert payload["sub"] == "test-user-valid-test"
        assert payload["tenant_id"] == "test-tenant"

    def test_empty_token_raises(self):
        """Empty token should raise ValueError."""
        with pytest.raises(ValueError):
            _verify_token("")

    def test_none_token_raises(self):
        """None token should raise ValueError."""
        with pytest.raises(ValueError):
            _verify_token(None)

    def test_short_token_raises(self):
        """Short token should raise ValueError."""
        with pytest.raises(ValueError):
            _verify_token("short")


class TestSessionHelpers:
    """Test session helper functions."""

    def test_get_session_id_new(self):
        """Get session ID for new websocket."""
        ws = MagicMock()
        ws.client_state = {}
        session_id = _get_session_id(ws)
        assert session_id is not None
        assert len(session_id) == 32  # hex UUID

    def test_get_tenant_id(self):
        """Get tenant ID from session."""
        ws = MagicMock()
        _active_sessions[ws] = {"tenant_id": "tenant-1"}
        assert _get_tenant_id(ws) == "tenant-1"

    def test_get_user_id(self):
        """Get user ID from session."""
        ws = MagicMock()
        _active_sessions[ws] = {"user_id": "user-1"}
        assert _get_user_id(ws) == "user-1"


class TestMessageQueue:
    """Test message queue functionality."""

    @pytest.mark.asyncio
    async def test_queue_message(self):
        """Test queuing a message."""
        ws = MagicMock()
        msg = {"type": "chat", "data": "test"}
        await _queue_message(ws, msg)
        assert len(_message_queues[ws]) == 1
        assert _message_queues[ws][0] == msg

    @pytest.mark.asyncio
    async def test_send_queued_messages(self):
        """Test sending queued messages."""
        ws = MagicMock()
        ws.send_json = AsyncMock()
        msg1 = {"type": "message", "data": "first"}
        msg2 = {"type": "message", "data": "second"}
        _message_queues[ws] = [msg1, msg2]

        count = await _send_queued_messages(ws)
        assert count == 2
        ws.send_json.assert_any_call(msg1)
        ws.send_json.assert_any_call(msg2)

    @pytest.mark.asyncio
    async def test_queue_max_messages(self):
        """Test max pending messages limit."""
        ws = MagicMock()
        for i in range(150):
            await _queue_message(ws, {"type": "test", "index": i})
        # Should keep only last 100
        assert len(_message_queues[ws]) <= 100


class TestHeartbeat:
    """Test heartbeat functionality."""

    def test_start_heartbeat(self):
        """Start heartbeat for websocket."""
        ws = MagicMock()
        _heartbeat_tasks[ws] = None
        _start_heartbeat(ws)
        assert ws in _heartbeat_tasks
        assert _heartbeat_tasks[ws] is not None

    def test_stop_heartbeat(self):
        """Stop heartbeat for websocket."""
        ws = MagicMock()
        task = MagicMock()
        _heartbeat_tasks[ws] = task
        _stop_heartbeat(ws)
        assert ws not in _heartbeat_tasks
        task.cancel.assert_called_once()


class TestWebSocketManager:
    """Test WebSocketManager class."""

    @pytest.mark.asyncio
    async def test_broadcast(self):
        """Broadcast message to all sessions."""
        ws1 = MagicMock()
        ws2 = MagicMock()
        ws1.send_json = AsyncMock()
        ws2.send_json = AsyncMock()
        _active_sessions[ws1] = {"tenant_id": "tenant-1"}
        _active_sessions[ws2] = {"tenant_id": "tenant-1"}

        manager = WebSocketManager()
        count = await manager.broadcast({"type": "test"})
        assert count == 2
        ws1.send_json.assert_called_once()
        ws2.send_json.assert_called_once()

    @pytest.mark.asyncio
    async def test_broadcast_to_tenant(self):
        """Broadcast to specific tenant."""
        ws1 = MagicMock()
        ws2 = MagicMock()
        ws1.send_json = AsyncMock()
        ws2.send_json = AsyncMock()
        _active_sessions[ws1] = {"tenant_id": "tenant-1"}
        _active_sessions[ws2] = {"tenant_id": "tenant-2"}

        manager = WebSocketManager()
        count = await manager.broadcast_to_tenant("tenant-1", {"type": "test"})
        assert count == 1
        ws1.send_json.assert_called_once()
        ws2.send_json.assert_not_called()

    @pytest.mark.asyncio
    async def test_send_to_session(self):
        """Send message to specific session."""
        ws = MagicMock()
        ws.send_json = AsyncMock()
        _active_sessions[ws] = {"session_id": "session-1"}

        manager = WebSocketManager()
        result = await manager.send_to_session("session-1", {"type": "test"})
        assert result is True
        ws.send_json.assert_called_once()

    @pytest.mark.asyncio
    async def test_send_to_session_not_found(self):
        """Send to non-existent session returns False."""
        manager = WebSocketManager()
        result = await manager.send_to_session("nonexistent", {"type": "test"})
        assert result is False

    @pytest.mark.asyncio
    async def test_get_session_count(self):
        """Get active session count."""
        ws1 = MagicMock()
        ws2 = MagicMock()
        _active_sessions[ws1] = {"tenant_id": "tenant-1"}
        _active_sessions[ws2] = {"tenant_id": "tenant-2"}

        manager = WebSocketManager()
        count = await manager.get_session_count()
        assert count == 2

    @pytest.mark.asyncio
    async def test_get_tenant_session_count(self):
        """Get session count for specific tenant."""
        ws1 = MagicMock()
        ws2 = MagicMock()
        ws3 = MagicMock()
        _active_sessions[ws1] = {"tenant_id": "tenant-1"}
        _active_sessions[ws2] = {"tenant_id": "tenant-1"}
        _active_sessions[ws3] = {"tenant_id": "tenant-2"}

        manager = WebSocketManager()
        count = await manager.get_tenant_session_count("tenant-1")
        assert count == 2

    @pytest.mark.asyncio
    async def test_get_active_sessions(self):
        """Get list of active sessions."""
        ws = MagicMock()
        _active_sessions[ws] = {
            "session_id": "session-1",
            "tenant_id": "tenant-1",
            "user_id": "user-1",
            "created_at": datetime.now(tz=timezone.utc),
            "last_active": datetime.now(tz=timezone.utc),
        }

        manager = WebSocketManager()
        sessions = await manager.get_active_sessions()
        assert len(sessions) == 1
        assert sessions[0]["tenant_id"] == "tenant-1"

    @pytest.mark.asyncio
    async def test_disconnect_session(self):
        """Disconnect a specific session."""
        ws = MagicMock()
        _active_sessions[ws] = {"tenant_id": "tenant-1"}
        _heartbeat_tasks[ws] = MagicMock()

        manager = WebSocketManager()
        await manager.disconnect_session(ws)
        assert ws not in _active_sessions

    @pytest.mark.asyncio
    async def test_disconnect_tenant(self):
        """Disconnect all sessions for a tenant."""
        ws1 = MagicMock()
        ws2 = MagicMock()
        ws1.close = AsyncMock()
        ws2.close = AsyncMock()
        _active_sessions[ws1] = {"tenant_id": "tenant-1"}
        _active_sessions[ws2] = {"tenant_id": "tenant-1"}

        manager = WebSocketManager()
        count = await manager.disconnect_tenant("tenant-1")
        assert count == 2


class TestWebSocketEndpoint:
    """Test WebSocket endpoint behavior."""

    @pytest.mark.asyncio
    async def test_missing_token(self):
        """Connection without token should be rejected."""
        websocket = MagicMock()
        websocket.query_params.get.return_value = None
        websocket.close = AsyncMock()

        await websocket_chat(websocket)
        websocket.close.assert_called_once()
        call_args = websocket.close.call_args
        assert call_args[1]["code"] == 4001

    @pytest.mark.asyncio
    async def test_invalid_token(self):
        """Connection with invalid token should be rejected."""
        websocket = MagicMock()
        websocket.query_params.get.return_value = "invalid"
        websocket.close = AsyncMock()

        await websocket_chat(websocket)
        websocket.close.assert_called_once()
        call_args = websocket.close.call_args
        assert call_args[1]["code"] == 4001

    @pytest.mark.asyncio
    async def test_valid_connection(self):
        """Valid connection should be accepted."""
        websocket = MagicMock()
        websocket.query_params.get.return_value = "valid-test-token-12345"
        websocket.accept = AsyncMock()
        websocket.send_json = AsyncMock()
        websocket.receive_text = AsyncMock(side_effect=[
            json.dumps({"type": "ping"}),
            asyncio.TimeoutError(),
        ])

        await websocket_chat(websocket)
        websocket.accept.assert_called_once()

    @pytest.mark.asyncio
    async def test_ping_pong(self):
        """Ping should receive pong response."""
        websocket = MagicMock()
        websocket.query_params.get.return_value = "valid-test-token-12345"
        websocket.accept = AsyncMock()
        websocket.send_json = AsyncMock()
        websocket.receive_text = AsyncMock(side_effect=[
            json.dumps({"type": "ping"}),
            asyncio.TimeoutError(),
        ])

        await websocket_chat(websocket)

        # Check that pong was sent
        pong_sent = False
        for call in websocket.send_json.call_args_list:
            if call[0][0].get("type") == "pong":
                pong_sent = True
                break
        assert pong_sent is True

    @pytest.mark.asyncio
    async def test_chat_message(self):
        """Chat message should receive response."""
        websocket = MagicMock()
        websocket.query_params.get.return_value = "valid-test-token-12345"
        websocket.accept = AsyncMock()
        websocket.send_json = AsyncMock()
        websocket.receive_text = AsyncMock(side_effect=[
            json.dumps({
                "type": "chat",
                "model": "gpt-4o-mini",
                "messages": [{"role": "user", "content": "Hello"}],
            }),
            asyncio.TimeoutError(),
        ])

        await websocket_chat(websocket)

        # Check that chat_start was sent
        chat_start_sent = False
        for call in websocket.send_json.call_args_list:
            if call[0][0].get("type") == "chat_start":
                chat_start_sent = True
                break
        assert chat_start_sent is True

    @pytest.mark.asyncio
    async def test_reconnect_message(self):
        """Reconnect message should receive acknowledgment."""
        websocket = MagicMock()
        websocket.query_params.get.return_value = "valid-test-token-12345"
        websocket.accept = AsyncMock()
        websocket.send_json = AsyncMock()
        websocket.receive_text = AsyncMock(side_effect=[
            json.dumps({
                "type": "reconnect",
                "session_id": "previous-session-id",
            }),
            asyncio.TimeoutError(),
        ])

        # Add session metadata for reconnect
        _session_metadata["previous-session-id"] = {
            "tenant_id": "test-tenant",
            "user_id": "test-user",
            "created_at": datetime.now(tz=timezone.utc),
            "last_active": datetime.now(tz=timezone.utc),
            "message_count": 0,
        }

        await websocket_chat(websocket)

        # Check that reconnect_ack was sent
        reconnect_ack_sent = False
        for call in websocket.send_json.call_args_list:
            if call[0][0].get("type") == "reconnect_ack":
                reconnect_ack_sent = True
                break
        assert reconnect_ack_sent is True

    @pytest.mark.asyncio
    async def test_invalid_json(self):
        """Invalid JSON should receive error response."""
        websocket = MagicMock()
        websocket.query_params.get.return_value = "valid-test-token-12345"
        websocket.accept = AsyncMock()
        websocket.send_json = AsyncMock()
        websocket.receive_text = AsyncMock(side_effect=[
            "not valid json",
            asyncio.TimeoutError(),
        ])

        await websocket_chat(websocket)

        # Check that error was sent
        error_sent = False
        for call in websocket.send_json.call_args_list:
            if call[0][0].get("type") == "error":
                error_sent = True
                break
        assert error_sent is True

    @pytest.mark.asyncio
    async def test_unknown_message_type(self):
        """Unknown message type should receive error response."""
        websocket = MagicMock()
        websocket.query_params.get.return_value = "valid-test-token-12345"
        websocket.accept = AsyncMock()
        websocket.send_json = AsyncMock()
        websocket.receive_text = AsyncMock(side_effect=[
            json.dumps({"type": "unknown_type"}),
            asyncio.TimeoutError(),
        ])

        await websocket_chat(websocket)

        # Check that error was sent
        error_sent = False
        for call in websocket.send_json.call_args_list:
            if call[0][0].get("type") == "error":
                error_sent = True
                break
        assert error_sent is True

    @pytest.mark.asyncio
    async def test_disconnect_cleanup(self):
        """Disconnected websocket should be cleaned up."""
        websocket = MagicMock()
        websocket.query_params.get.return_value = "valid-test-token-12345"
        websocket.accept = AsyncMock()
        websocket.send_json = AsyncMock()
        websocket.receive_text = AsyncMock(side_effect=Exception("Connection lost"))

        await websocket_chat(websocket)

        # Websocket should be removed from active sessions
        assert websocket not in _active_sessions


class TestRouter:
    """Test router registration."""

    def test_router_exists(self):
        """Router should be defined."""
        assert router is not None

    def test_router_has_websocket_endpoint(self):
        """Router should have websocket endpoint."""
        routes = [r for r in router.routes if hasattr(r, 'path') and r.path == "/ws/ai/chat"]
        assert len(routes) == 1
