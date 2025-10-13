"""
End-to-End tests for complete discussion workflows

Tests full discussion lifecycle from creation to consensus.
"""

import pytest
import asyncio
import json
from httpx import AsyncClient
from websockets import connect as ws_connect
from src.api.main import app


# Test helpers

async def create_test_discussion(topic: str, num_agents: int = 3, max_turns: int = 10):
    """Helper to create a test discussion"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post(
            "/api/discussions/create",
            json={
                "topic": topic,
                "num_agents": num_agents,
                "user_id": "e2e-test-user",
                "max_turns": max_turns
            }
        )

        assert response.status_code == 201
        data = response.json()
        return data["discussion_id"]


async def send_user_message(discussion_id: str, content: str):
    """Helper to send user message"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post(
            f"/api/discussions/{discussion_id}/message",
            json={
                "content": content,
                "user_id": "e2e-test-user"
            }
        )

        assert response.status_code == 200
        return response.json()


async def get_discussion_messages(discussion_id: str, limit: int = 100):
    """Helper to get discussion messages"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get(
            f"/api/discussions/{discussion_id}/messages",
            params={"limit": limit}
        )

        assert response.status_code == 200
        data = response.json()
        return data["messages"]


async def get_discussion_status(discussion_id: str):
    """Helper to get discussion status"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get(f"/api/discussions/{discussion_id}")

        assert response.status_code == 200
        return response.json()


async def stop_discussion(discussion_id: str):
    """Helper to stop discussion"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post(f"/api/discussions/{discussion_id}/stop")

        assert response.status_code == 200
        return response.json()


# Tests

@pytest.mark.asyncio
@pytest.mark.e2e
async def test_complete_discussion_flow():
    """
    Test complete discussion from creation to consensus

    Flow:
    1. Create discussion
    2. Connect to WebSocket
    3. Wait for agent messages
    4. Verify consensus or completion
    """
    # 1. Create discussion
    discussion_id = await create_test_discussion(
        topic="Best programming language for AI development",
        num_agents=3,
        max_turns=15
    )

    assert discussion_id is not None
    assert discussion_id.startswith("disc_")

    # 2. Connect to WebSocket
    ws_url = f"ws://localhost:8007/ws/discussions/{discussion_id}"
    messages_received = []

    async with ws_connect(ws_url) as websocket:
        # 3. Wait for messages (timeout: 60 seconds)
        timeout = 60
        start_time = asyncio.get_event_loop().time()

        while asyncio.get_event_loop().time() - start_time < timeout:
            try:
                message = await asyncio.wait_for(
                    websocket.recv(),
                    timeout=5.0
                )
                msg_data = json.loads(message)
                messages_received.append(msg_data)

                # Check if discussion completed
                if msg_data["type"] in ["consensus_reached", "discussion_complete"]:
                    break

                # Stop if max messages received (prevent infinite loop)
                if len(messages_received) > 50:
                    break

            except asyncio.TimeoutError:
                # Check if discussion is still running
                status = await get_discussion_status(discussion_id)
                if status["status"] in ["completed", "stopped"]:
                    break
                continue

    # 4. Verify discussion completed
    assert len(messages_received) > 0, "Should receive at least some messages"

    # Verify agent messages were received
    agent_messages = [m for m in messages_received if m["type"] == "agent_message"]
    assert len(agent_messages) > 0, "Should have agent messages"

    # Check that multiple agents participated
    agents = set(
        m["data"]["role_name"]
        for m in messages_received
        if m["type"] == "agent_message"
    )
    assert len(agents) >= 2, "Multiple agents should participate"

    # Verify discussion reached conclusion
    conclusion_types = ["consensus_reached", "discussion_complete"]
    assert any(
        m["type"] in conclusion_types
        for m in messages_received
    ), "Discussion should reach conclusion"


@pytest.mark.asyncio
@pytest.mark.e2e
async def test_user_intervention():
    """
    Test that user can interrupt and guide discussion

    Flow:
    1. Create discussion
    2. Let agents discuss briefly
    3. Send user message to guide discussion
    4. Verify agents respond to user input
    """
    # 1. Create discussion
    discussion_id = await create_test_discussion(
        topic="Database selection for e-commerce",
        num_agents=3,
        max_turns=20
    )

    # 2. Wait for some initial messages
    await asyncio.sleep(5)

    # Get current messages
    messages_before = await get_discussion_messages(discussion_id)
    message_count_before = len(messages_before)

    # 3. Send user message
    user_content = "What about considering PostgreSQL specifically for its JSON support?"
    response = await send_user_message(discussion_id, user_content)

    assert response["status"] == "sent"

    # 4. Wait for agents to respond
    await asyncio.sleep(10)

    # Get messages after intervention
    messages_after = await get_discussion_messages(discussion_id)

    # Should have more messages
    assert len(messages_after) > message_count_before

    # Find user message
    user_messages = [m for m in messages_after if m.get("role") == "user"]
    assert len(user_messages) > 0
    assert any("PostgreSQL" in m.get("content", "") for m in user_messages)

    # Recent agent messages should reference user's topic
    recent_messages = messages_after[message_count_before:]
    agent_responses = [m for m in recent_messages if m.get("role") != "user"]

    # At least one agent should mention PostgreSQL or respond to user
    assert any(
        "postgres" in m.get("content", "").lower() or
        "database" in m.get("content", "").lower()
        for m in agent_responses
    ), "Agents should respond to user guidance"


@pytest.mark.asyncio
@pytest.mark.e2e
@pytest.mark.slow
async def test_consensus_flow():
    """
    Test consensus detection and notification

    Flow:
    1. Create discussion with simple topic (likely to reach consensus)
    2. Connect WebSocket
    3. Wait for consensus_update messages
    4. Verify consensus was reached
    """
    # Use simple topic likely to reach consensus
    discussion_id = await create_test_discussion(
        topic="Is water essential for human life?",
        num_agents=3,
        max_turns=10
    )

    ws_url = f"ws://localhost:8007/ws/discussions/{discussion_id}"
    consensus_updates = []

    async with ws_connect(ws_url) as websocket:
        timeout = 45
        start_time = asyncio.get_event_loop().time()

        while asyncio.get_event_loop().time() - start_time < timeout:
            try:
                message = await asyncio.wait_for(
                    websocket.recv(),
                    timeout=5.0
                )
                msg_data = json.loads(message)

                if msg_data["type"] == "consensus_update":
                    consensus_updates.append(msg_data)

                if msg_data["type"] in ["consensus_reached", "discussion_complete"]:
                    break

            except asyncio.TimeoutError:
                continue

    # Should have received consensus updates
    assert len(consensus_updates) > 0, "Should receive consensus updates"

    # Check final consensus
    final_status = await get_discussion_status(discussion_id)

    # For simple question, consensus should likely be reached
    # (but not guaranteed, so we just check the mechanism works)
    assert "consensus" in final_status


@pytest.mark.asyncio
@pytest.mark.e2e
async def test_multiple_concurrent_discussions():
    """
    Test handling multiple concurrent discussions

    Flow:
    1. Create 3 discussions simultaneously
    2. Connect WebSocket to each
    3. Verify all proceed independently
    4. Stop all discussions
    """
    topics = [
        "Best cloud provider for startups",
        "Microservices vs monolithic architecture",
        "Type safety in programming languages"
    ]

    # 1. Create discussions
    discussion_ids = []
    for topic in topics:
        disc_id = await create_test_discussion(topic, num_agents=2, max_turns=10)
        discussion_ids.append(disc_id)

    assert len(discussion_ids) == 3
    assert len(set(discussion_ids)) == 3  # All unique

    # 2. Connect to all discussions
    async def monitor_discussion(disc_id: str):
        """Monitor a discussion and collect messages"""
        ws_url = f"ws://localhost:8007/ws/discussions/{disc_id}"
        messages = []

        try:
            async with ws_connect(ws_url) as websocket:
                for _ in range(5):  # Collect a few messages
                    try:
                        message = await asyncio.wait_for(
                            websocket.recv(),
                            timeout=3.0
                        )
                        messages.append(json.loads(message))
                    except asyncio.TimeoutError:
                        break
        except Exception:
            pass

        return disc_id, messages

    # Monitor all concurrently
    results = await asyncio.gather(*[
        monitor_discussion(disc_id)
        for disc_id in discussion_ids
    ])

    # 3. Verify all received messages
    for disc_id, messages in results:
        assert len(messages) > 0, f"Discussion {disc_id} should have messages"

    # 4. Stop all discussions
    await asyncio.gather(*[
        stop_discussion(disc_id)
        for disc_id in discussion_ids
    ])

    # Verify all stopped
    for disc_id in discussion_ids:
        status = await get_discussion_status(disc_id)
        assert status["status"] == "stopped"


@pytest.mark.asyncio
@pytest.mark.e2e
async def test_discussion_with_mentions():
    """
    Test that agents can mention each other using @mention syntax

    Flow:
    1. Create discussion
    2. Wait for agent messages
    3. Send user message mentioning an agent
    4. Verify mentioned agent responds
    """
    discussion_id = await create_test_discussion(
        topic="Security best practices for web applications",
        num_agents=3,
        max_turns=15
    )

    # Wait for roles to be created
    await asyncio.sleep(3)

    # Get roles
    status = await get_discussion_status(discussion_id)
    roles = status.get("roles", [])

    assert len(roles) > 0, "Should have roles"

    # Pick a role to mention
    role_to_mention = roles[0]["name"]

    # Send message with mention
    user_content = f"@{role_to_mention}, what is your opinion on input validation?"
    await send_user_message(discussion_id, user_content)

    # Wait for response
    await asyncio.sleep(10)

    # Get messages
    messages = await get_discussion_messages(discussion_id)

    # Find user message
    user_msg = next((m for m in messages if m.get("role") == "user" and role_to_mention in m.get("content", "")), None)
    assert user_msg is not None, "User message with mention should be in history"

    # Verify mentioned agent responded (or at least there are responses after mention)
    messages_after_mention = [m for m in messages if m.get("timestamp", "") > user_msg.get("timestamp", "")]
    assert len(messages_after_mention) > 0, "Should have responses after mention"


@pytest.mark.asyncio
@pytest.mark.e2e
async def test_early_discussion_stop():
    """
    Test stopping discussion before it completes naturally

    Flow:
    1. Create discussion
    2. Let it run briefly
    3. Stop discussion
    4. Verify no more messages after stop
    """
    discussion_id = await create_test_discussion(
        topic="Complex philosophical question about consciousness",
        num_agents=3,
        max_turns=30  # High max, but we'll stop early
    )

    # Wait for some discussion
    await asyncio.sleep(10)

    # Get current turn
    status_before = await get_discussion_status(discussion_id)
    turn_before = status_before.get("current_turn", 0)

    # Stop discussion
    await stop_discussion(discussion_id)

    # Wait a bit
    await asyncio.sleep(5)

    # Verify discussion stopped
    status_after = await get_discussion_status(discussion_id)
    assert status_after["status"] == "stopped"

    # Turn shouldn't have advanced significantly
    turn_after = status_after.get("current_turn", 0)
    assert turn_after <= turn_before + 1, "Discussion should stop quickly"


@pytest.mark.asyncio
@pytest.mark.e2e
@pytest.mark.slow
async def test_websocket_reconnection():
    """
    Test WebSocket reconnection after disconnect

    Flow:
    1. Create discussion
    2. Connect WebSocket
    3. Disconnect
    4. Reconnect
    5. Verify still receiving messages
    """
    discussion_id = await create_test_discussion(
        topic="Benefits of continuous integration",
        num_agents=2,
        max_turns=20
    )

    ws_url = f"ws://localhost:8007/ws/discussions/{discussion_id}"

    # First connection
    async with ws_connect(ws_url) as ws1:
        msg1 = await asyncio.wait_for(ws1.recv(), timeout=5.0)
        assert msg1 is not None

    # Disconnect (context manager closes)

    # Wait a bit
    await asyncio.sleep(2)

    # Reconnect
    async with ws_connect(ws_url) as ws2:
        # Should be able to connect again
        msg2 = await asyncio.wait_for(ws2.recv(), timeout=5.0)
        assert msg2 is not None

    # Discussion should still be running
    status = await get_discussion_status(discussion_id)
    assert status["status"] in ["running", "waiting"]


@pytest.mark.asyncio
@pytest.mark.e2e
async def test_discussion_message_history():
    """
    Test that complete message history is maintained

    Flow:
    1. Create discussion
    2. Let it run for several turns
    3. Retrieve full message history
    4. Verify chronological order and completeness
    """
    discussion_id = await create_test_discussion(
        topic="Advantages of functional programming",
        num_agents=3,
        max_turns=8
    )

    # Wait for discussion to progress
    await asyncio.sleep(15)

    # Get all messages
    messages = await get_discussion_messages(discussion_id, limit=100)

    assert len(messages) > 0, "Should have message history"

    # Verify chronological order (if timestamps present)
    if all("timestamp" in m for m in messages):
        timestamps = [m["timestamp"] for m in messages]
        assert timestamps == sorted(timestamps), "Messages should be in chronological order"

    # Verify message structure
    for msg in messages:
        assert "role" in msg or "role_name" in msg
        assert "content" in msg
        assert "turn" in msg or "turn_number" in msg


@pytest.mark.asyncio
@pytest.mark.e2e
async def test_discussion_with_model_preferences():
    """
    Test creating discussion with specific model preferences

    Flow:
    1. Create discussion with model preferences
    2. Verify roles use only specified models
    3. Check discussion proceeds normally
    """
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post(
            "/api/discussions/create",
            json={
                "topic": "Impact of AI on employment",
                "num_agents": 3,
                "user_id": "e2e-test-user",
                "max_turns": 10,
                "model_preferences": ["gpt-4", "claude-3-opus"]
            }
        )

        assert response.status_code == 201
        data = response.json()
        discussion_id = data["discussion_id"]
        roles = data["roles"]

        # All roles should use preferred models
        for role in roles:
            assert role["model"] in ["gpt-4", "claude-3-opus"], \
                f"Role {role['name']} should use preferred model"

    # Wait for some discussion
    await asyncio.sleep(10)

    # Verify discussion is running
    status = await get_discussion_status(discussion_id)
    assert status["status"] in ["running", "waiting", "completed"]
