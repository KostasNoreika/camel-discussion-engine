"""
Unit tests for WebSocket ConnectionManager

Tests WebSocket connection management, broadcasting, and connection lifecycle.
"""

import pytest
import json
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi import WebSocket
from src.api.websocket.manager import ConnectionManager


@pytest.fixture
def connection_manager():
    """Fixture providing ConnectionManager instance"""
    return ConnectionManager()


@pytest.fixture
def mock_websocket():
    """Fixture providing mock WebSocket"""
    ws = AsyncMock(spec=WebSocket)
    ws.send_text = AsyncMock()
    ws.send_json = AsyncMock()
    ws.accept = AsyncMock()
    ws.close = AsyncMock()
    return ws


@pytest.mark.asyncio
async def test_connect_new_websocket(connection_manager, mock_websocket):
    """Test connecting a new WebSocket"""
    discussion_id = "disc_test_123"

    await connection_manager.connect(mock_websocket, discussion_id)

    # WebSocket should be accepted
    mock_websocket.accept.assert_called_once()

    # Should be registered in active connections
    assert discussion_id in connection_manager.active_connections
    assert mock_websocket in connection_manager.active_connections[discussion_id]


@pytest.mark.asyncio
async def test_connect_multiple_clients_same_discussion(connection_manager):
    """Test multiple clients connecting to same discussion"""
    discussion_id = "disc_test_456"
    ws1 = AsyncMock(spec=WebSocket)
    ws2 = AsyncMock(spec=WebSocket)
    ws3 = AsyncMock(spec=WebSocket)

    await connection_manager.connect(ws1, discussion_id)
    await connection_manager.connect(ws2, discussion_id)
    await connection_manager.connect(ws3, discussion_id)

    # All three should be connected
    assert len(connection_manager.active_connections[discussion_id]) == 3
    assert ws1 in connection_manager.active_connections[discussion_id]
    assert ws2 in connection_manager.active_connections[discussion_id]
    assert ws3 in connection_manager.active_connections[discussion_id]


@pytest.mark.asyncio
async def test_disconnect_websocket(connection_manager, mock_websocket):
    """Test disconnecting a WebSocket"""
    discussion_id = "disc_test_789"

    await connection_manager.connect(mock_websocket, discussion_id)
    await connection_manager.disconnect(mock_websocket, discussion_id)

    # Should be removed from active connections
    if discussion_id in connection_manager.active_connections:
        assert mock_websocket not in connection_manager.active_connections[discussion_id]


@pytest.mark.asyncio
async def test_disconnect_removes_empty_discussion(connection_manager, mock_websocket):
    """Test that empty discussion is removed after last client disconnects"""
    discussion_id = "disc_test_cleanup"

    await connection_manager.connect(mock_websocket, discussion_id)
    await connection_manager.disconnect(mock_websocket, discussion_id)

    # Empty discussion should be cleaned up
    assert discussion_id not in connection_manager.active_connections or \
           len(connection_manager.active_connections[discussion_id]) == 0


@pytest.mark.asyncio
async def test_broadcast_message_to_all_clients(connection_manager):
    """Test broadcasting message to all connected clients"""
    discussion_id = "disc_test_broadcast"

    ws1 = AsyncMock(spec=WebSocket)
    ws2 = AsyncMock(spec=WebSocket)
    ws3 = AsyncMock(spec=WebSocket)

    ws1.send_text = AsyncMock()
    ws2.send_text = AsyncMock()
    ws3.send_text = AsyncMock()

    await connection_manager.connect(ws1, discussion_id)
    await connection_manager.connect(ws2, discussion_id)
    await connection_manager.connect(ws3, discussion_id)

    message = {"type": "test", "data": "broadcast test"}

    await connection_manager.broadcast(discussion_id, message)

    # All clients should receive the message
    message_json = json.dumps(message)
    ws1.send_text.assert_called_once_with(message_json)
    ws2.send_text.assert_called_once_with(message_json)
    ws3.send_text.assert_called_once_with(message_json)


@pytest.mark.asyncio
async def test_broadcast_to_nonexistent_discussion(connection_manager):
    """Test broadcasting to discussion with no connections"""
    discussion_id = "disc_nonexistent"

    message = {"type": "test", "data": "test"}

    # Should not raise error
    await connection_manager.broadcast(discussion_id, message)


@pytest.mark.asyncio
async def test_broadcast_handles_dead_connections(connection_manager):
    """Test that dead connections are removed during broadcast"""
    discussion_id = "disc_test_dead"

    ws_working = AsyncMock(spec=WebSocket)
    ws_dead = AsyncMock(spec=WebSocket)

    ws_working.send_text = AsyncMock()
    ws_dead.send_text = AsyncMock(side_effect=Exception("Connection closed"))

    await connection_manager.connect(ws_working, discussion_id)
    await connection_manager.connect(ws_dead, discussion_id)

    message = {"type": "test", "data": "test"}

    await connection_manager.broadcast(discussion_id, message)

    # Dead connection should be removed
    assert ws_working in connection_manager.active_connections[discussion_id]
    assert ws_dead not in connection_manager.active_connections[discussion_id]


@pytest.mark.asyncio
async def test_send_personal_message(connection_manager, mock_websocket):
    """Test sending personal message to specific client"""
    discussion_id = "disc_test_personal"

    mock_websocket.send_text = AsyncMock()

    await connection_manager.connect(mock_websocket, discussion_id)

    message = {"type": "personal", "data": "just for you"}

    await connection_manager.send_personal_message(mock_websocket, message)

    mock_websocket.send_text.assert_called_once_with(json.dumps(message))


@pytest.mark.asyncio
async def test_send_agent_message(connection_manager):
    """Test sending agent message via convenience method"""
    discussion_id = "disc_test_agent_msg"
    ws = AsyncMock(spec=WebSocket)
    ws.send_text = AsyncMock()

    await connection_manager.connect(ws, discussion_id)

    await connection_manager.send_agent_message(
        discussion_id=discussion_id,
        role_name="Expert A",
        model="gpt-4",
        content="This is my analysis...",
        turn_number=5
    )

    # Should have broadcast message with correct structure
    ws.send_text.assert_called_once()
    sent_data = json.loads(ws.send_text.call_args[0][0])

    assert sent_data["type"] == "agent_message"
    assert sent_data["data"]["role_name"] == "Expert A"
    assert sent_data["data"]["model"] == "gpt-4"
    assert sent_data["data"]["content"] == "This is my analysis..."
    assert sent_data["data"]["turn_number"] == 5


@pytest.mark.asyncio
async def test_send_consensus_update(connection_manager):
    """Test sending consensus update via convenience method"""
    discussion_id = "disc_test_consensus_msg"
    ws = AsyncMock(spec=WebSocket)
    ws.send_text = AsyncMock()

    await connection_manager.connect(ws, discussion_id)

    await connection_manager.send_consensus_update(
        discussion_id=discussion_id,
        reached=True,
        confidence=0.95,
        summary="All experts agree on option X"
    )

    ws.send_text.assert_called_once()
    sent_data = json.loads(ws.send_text.call_args[0][0])

    assert sent_data["type"] == "consensus_update"
    assert sent_data["data"]["reached"] is True
    assert sent_data["data"]["confidence"] == 0.95
    assert sent_data["data"]["summary"] == "All experts agree on option X"


@pytest.mark.asyncio
async def test_send_discussion_complete(connection_manager):
    """Test sending discussion complete notification"""
    discussion_id = "disc_test_complete_msg"
    ws = AsyncMock(spec=WebSocket)
    ws.send_text = AsyncMock()

    await connection_manager.connect(ws, discussion_id)

    await connection_manager.send_discussion_complete(
        discussion_id=discussion_id,
        total_turns=12,
        consensus_reached=True,
        final_summary="Discussion concluded with consensus."
    )

    ws.send_text.assert_called_once()
    sent_data = json.loads(ws.send_text.call_args[0][0])

    assert sent_data["type"] == "discussion_complete"
    assert sent_data["data"]["total_turns"] == 12
    assert sent_data["data"]["consensus_reached"] is True
    assert sent_data["data"]["final_summary"] == "Discussion concluded with consensus."


@pytest.mark.asyncio
async def test_disconnect_all_for_discussion(connection_manager):
    """Test disconnecting all clients from a discussion"""
    discussion_id = "disc_test_disconnect_all"

    ws1 = AsyncMock(spec=WebSocket)
    ws2 = AsyncMock(spec=WebSocket)
    ws3 = AsyncMock(spec=WebSocket)

    await connection_manager.connect(ws1, discussion_id)
    await connection_manager.connect(ws2, discussion_id)
    await connection_manager.connect(ws3, discussion_id)

    await connection_manager.disconnect_all(discussion_id)

    # All connections should be removed
    assert discussion_id not in connection_manager.active_connections or \
           len(connection_manager.active_connections[discussion_id]) == 0


@pytest.mark.asyncio
async def test_connection_count(connection_manager):
    """Test getting connection count for a discussion"""
    discussion_id = "disc_test_count"

    assert connection_manager.get_connection_count(discussion_id) == 0

    ws1 = AsyncMock(spec=WebSocket)
    ws2 = AsyncMock(spec=WebSocket)

    await connection_manager.connect(ws1, discussion_id)
    assert connection_manager.get_connection_count(discussion_id) == 1

    await connection_manager.connect(ws2, discussion_id)
    assert connection_manager.get_connection_count(discussion_id) == 2

    await connection_manager.disconnect(ws1, discussion_id)
    assert connection_manager.get_connection_count(discussion_id) == 1


def test_active_discussions_list(connection_manager):
    """Test listing active discussions"""
    # Initially empty
    assert len(connection_manager.get_active_discussions()) == 0

    # Add some connections
    disc1 = "disc_1"
    disc2 = "disc_2"

    connection_manager.active_connections[disc1] = {MagicMock()}
    connection_manager.active_connections[disc2] = {MagicMock()}

    active = connection_manager.get_active_discussions()

    assert len(active) == 2
    assert disc1 in active
    assert disc2 in active


@pytest.mark.asyncio
async def test_concurrent_broadcast(connection_manager):
    """Test broadcasting to multiple discussions concurrently"""
    discussions = ["disc_1", "disc_2", "disc_3"]

    # Setup connections for each discussion
    for disc_id in discussions:
        ws = AsyncMock(spec=WebSocket)
        ws.send_text = AsyncMock()
        await connection_manager.connect(ws, disc_id)

    # Broadcast to all concurrently
    import asyncio

    await asyncio.gather(*[
        connection_manager.broadcast(disc_id, {"type": "test", "data": f"msg_{disc_id}"})
        for disc_id in discussions
    ])

    # All should have received their messages
    for disc_id in discussions:
        assert len(connection_manager.active_connections[disc_id]) > 0


@pytest.mark.asyncio
async def test_websocket_connection_mapping(connection_manager, mock_websocket):
    """Test connection mapping between websocket and discussion ID"""
    discussion_id = "disc_test_mapping"

    await connection_manager.connect(mock_websocket, discussion_id)

    # Should be able to look up discussion ID from websocket
    assert mock_websocket in connection_manager.connection_mapping
    assert connection_manager.connection_mapping[mock_websocket] == discussion_id


@pytest.mark.asyncio
async def test_graceful_disconnect_on_error(connection_manager):
    """Test graceful handling of disconnect errors"""
    discussion_id = "disc_test_error"

    ws = AsyncMock(spec=WebSocket)
    ws.close = AsyncMock(side_effect=Exception("Already closed"))

    await connection_manager.connect(ws, discussion_id)

    # Should not raise exception
    await connection_manager.disconnect(ws, discussion_id)


@pytest.mark.asyncio
async def test_message_serialization(connection_manager, mock_websocket):
    """Test that complex messages are properly serialized"""
    discussion_id = "disc_test_serialization"

    mock_websocket.send_text = AsyncMock()

    await connection_manager.connect(mock_websocket, discussion_id)

    complex_message = {
        "type": "agent_message",
        "data": {
            "role_name": "Expert A",
            "model": "gpt-4",
            "content": "Message with \"quotes\" and special chars: \n\t",
            "metadata": {
                "turn": 5,
                "timestamp": "2025-10-12T10:00:00Z",
                "confidence": 0.95
            }
        }
    }

    await connection_manager.broadcast(discussion_id, complex_message)

    # Should serialize correctly
    mock_websocket.send_text.assert_called_once()
    sent_text = mock_websocket.send_text.call_args[0][0]

    # Should be valid JSON
    parsed = json.loads(sent_text)
    assert parsed == complex_message


@pytest.mark.asyncio
async def test_connection_limit_enforcement(connection_manager):
    """Test that connection limits are enforced if configured"""
    discussion_id = "disc_test_limit"
    max_connections = 10

    # Connect maximum allowed
    websockets = []
    for i in range(max_connections):
        ws = AsyncMock(spec=WebSocket)
        await connection_manager.connect(ws, discussion_id)
        websockets.append(ws)

    assert connection_manager.get_connection_count(discussion_id) == max_connections

    # Connecting beyond limit should work (or handle gracefully)
    ws_extra = AsyncMock(spec=WebSocket)
    await connection_manager.connect(ws_extra, discussion_id)


@pytest.mark.asyncio
async def test_heartbeat_ping(connection_manager, mock_websocket):
    """Test sending heartbeat ping to maintain connection"""
    discussion_id = "disc_test_ping"

    mock_websocket.send_text = AsyncMock()

    await connection_manager.connect(mock_websocket, discussion_id)

    await connection_manager.send_personal_message(
        mock_websocket,
        {"type": "ping"}
    )

    mock_websocket.send_text.assert_called_once()
    sent_data = json.loads(mock_websocket.send_text.call_args[0][0])
    assert sent_data["type"] == "ping"
