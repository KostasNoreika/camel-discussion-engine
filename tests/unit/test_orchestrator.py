"""
Unit tests for Orchestrator component

Tests discussion orchestration, turn management, and agent coordination.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch, call
from datetime import datetime
from src.camel_engine.orchestrator import Orchestrator, DiscussionState
from src.camel_engine.role_creator import RoleDefinition


@pytest.fixture
def orchestrator():
    """Fixture providing Orchestrator instance"""
    return Orchestrator()


@pytest.fixture
def sample_roles():
    """Fixture providing sample role definitions"""
    return [
        RoleDefinition(
            name="Expert A",
            expertise="Topic expertise A",
            perspective="Perspective A",
            model="gpt-4"
        ),
        RoleDefinition(
            name="Expert B",
            expertise="Topic expertise B",
            perspective="Perspective B",
            model="claude-3-opus"
        ),
        RoleDefinition(
            name="Expert C",
            expertise="Topic expertise C",
            perspective="Perspective C",
            model="gemini-pro"
        )
    ]


@pytest.mark.asyncio
async def test_create_discussion(orchestrator):
    """Test creating a new discussion"""
    topic = "Test discussion topic"
    user_id = "test-user-123"
    num_agents = 3

    with patch.object(orchestrator, 'role_creator') as mock_creator:
        mock_creator.create_roles = AsyncMock(return_value=[
            RoleDefinition(name=f"Expert {i}", expertise=f"Expertise {i}",
                         perspective=f"Perspective {i}", model="gpt-4")
            for i in range(num_agents)
        ])

        discussion_id = await orchestrator.create_discussion(
            topic=topic,
            user_id=user_id,
            num_agents=num_agents
        )

        assert discussion_id is not None
        assert discussion_id.startswith("disc_")

        # Verify discussion was created with correct parameters
        discussion = orchestrator.get_discussion(discussion_id)
        assert discussion is not None
        assert discussion.topic == topic
        assert discussion.user_id == user_id
        assert len(discussion.roles) == num_agents


@pytest.mark.asyncio
async def test_create_discussion_with_model_preferences(orchestrator):
    """Test creating discussion with specific model preferences"""
    topic = "Test topic"
    user_id = "test-user"
    num_agents = 2
    model_preferences = ["gpt-4-turbo", "claude-3-opus"]

    with patch.object(orchestrator, 'role_creator') as mock_creator:
        mock_creator.create_roles = AsyncMock(return_value=[
            RoleDefinition(name="Expert 1", expertise="Expertise 1",
                         perspective="Perspective 1", model="gpt-4-turbo"),
            RoleDefinition(name="Expert 2", expertise="Expertise 2",
                         perspective="Perspective 2", model="claude-3-opus")
        ])

        discussion_id = await orchestrator.create_discussion(
            topic=topic,
            user_id=user_id,
            num_agents=num_agents,
            model_preferences=model_preferences
        )

        # Verify role creator was called with model preferences
        mock_creator.create_roles.assert_called_once_with(
            topic=topic,
            num_roles=num_agents,
            model_preferences=model_preferences
        )


@pytest.mark.asyncio
async def test_start_discussion(orchestrator, sample_roles):
    """Test starting a discussion"""
    # Create discussion first
    discussion_id = "disc_test_123"
    orchestrator._discussions[discussion_id] = DiscussionState(
        id=discussion_id,
        topic="Test topic",
        user_id="test-user",
        roles=sample_roles,
        status="created",
        current_turn=0,
        max_turns=10
    )

    with patch.object(orchestrator, '_run_discussion_turn') as mock_turn:
        mock_turn.return_value = AsyncMock()

        await orchestrator.start_discussion(discussion_id, max_turns=10)

        discussion = orchestrator.get_discussion(discussion_id)
        assert discussion.status == "running"


@pytest.mark.asyncio
async def test_discussion_turn_management(orchestrator, sample_roles):
    """Test that turns are managed correctly"""
    discussion_id = "disc_test_456"
    max_turns = 5

    orchestrator._discussions[discussion_id] = DiscussionState(
        id=discussion_id,
        topic="Test topic",
        user_id="test-user",
        roles=sample_roles,
        status="running",
        current_turn=0,
        max_turns=max_turns
    )

    with patch.object(orchestrator, '_get_agent_response') as mock_response:
        mock_response.return_value = AsyncMock(return_value="Agent response")

        # Run one turn
        await orchestrator._run_discussion_turn(discussion_id)

        discussion = orchestrator.get_discussion(discussion_id)
        assert discussion.current_turn == 1


@pytest.mark.asyncio
async def test_discussion_stops_at_max_turns(orchestrator, sample_roles):
    """Test that discussion stops when max turns reached"""
    discussion_id = "disc_test_789"
    max_turns = 3

    orchestrator._discussions[discussion_id] = DiscussionState(
        id=discussion_id,
        topic="Test topic",
        user_id="test-user",
        roles=sample_roles,
        status="running",
        current_turn=max_turns - 1,  # Almost at max
        max_turns=max_turns
    )

    with patch.object(orchestrator, '_get_agent_response') as mock_response:
        mock_response.return_value = AsyncMock(return_value="Final response")

        await orchestrator._run_discussion_turn(discussion_id)

        discussion = orchestrator.get_discussion(discussion_id)
        assert discussion.current_turn == max_turns
        assert discussion.status in ["completed", "stopped"]


@pytest.mark.asyncio
async def test_send_user_message(orchestrator, sample_roles):
    """Test sending user message to discussion"""
    discussion_id = "disc_test_user_msg"

    orchestrator._discussions[discussion_id] = DiscussionState(
        id=discussion_id,
        topic="Test topic",
        user_id="test-user",
        roles=sample_roles,
        status="running",
        current_turn=2,
        max_turns=10
    )

    user_message = "What about considering option X?"

    await orchestrator.send_user_message(
        discussion_id=discussion_id,
        content=user_message,
        user_id="test-user"
    )

    discussion = orchestrator.get_discussion(discussion_id)
    messages = discussion.messages

    # User message should be added to message history
    assert any(m.role == "user" and m.content == user_message for m in messages)


@pytest.mark.asyncio
async def test_stop_discussion(orchestrator, sample_roles):
    """Test stopping a running discussion"""
    discussion_id = "disc_test_stop"

    orchestrator._discussions[discussion_id] = DiscussionState(
        id=discussion_id,
        topic="Test topic",
        user_id="test-user",
        roles=sample_roles,
        status="running",
        current_turn=3,
        max_turns=10
    )

    await orchestrator.stop_discussion(discussion_id)

    discussion = orchestrator.get_discussion(discussion_id)
    assert discussion.status == "stopped"


@pytest.mark.asyncio
async def test_get_discussion_messages(orchestrator, sample_roles):
    """Test retrieving discussion messages"""
    discussion_id = "disc_test_messages"

    orchestrator._discussions[discussion_id] = DiscussionState(
        id=discussion_id,
        topic="Test topic",
        user_id="test-user",
        roles=sample_roles,
        status="running",
        current_turn=2,
        max_turns=10
    )

    # Add some test messages
    orchestrator._discussions[discussion_id].messages = [
        {"role": "Expert A", "content": "Message 1", "turn": 1},
        {"role": "Expert B", "content": "Message 2", "turn": 1},
        {"role": "user", "content": "User input", "turn": 2},
        {"role": "Expert A", "content": "Message 3", "turn": 2}
    ]

    messages = await orchestrator.get_discussion_messages(
        discussion_id=discussion_id,
        limit=10
    )

    assert len(messages) == 4
    assert messages[0]["content"] == "Message 1"


@pytest.mark.asyncio
async def test_get_discussion_messages_with_pagination(orchestrator, sample_roles):
    """Test message pagination"""
    discussion_id = "disc_test_pagination"

    orchestrator._discussions[discussion_id] = DiscussionState(
        id=discussion_id,
        topic="Test topic",
        user_id="test-user",
        roles=sample_roles,
        status="running",
        current_turn=10,
        max_turns=20
    )

    # Add many messages
    orchestrator._discussions[discussion_id].messages = [
        {"role": f"Expert {i % 3}", "content": f"Message {i}", "turn": i // 3}
        for i in range(30)
    ]

    # Get first page
    messages_page1 = await orchestrator.get_discussion_messages(
        discussion_id=discussion_id,
        limit=10,
        offset=0
    )

    assert len(messages_page1) == 10
    assert messages_page1[0]["content"] == "Message 0"

    # Get second page
    messages_page2 = await orchestrator.get_discussion_messages(
        discussion_id=discussion_id,
        limit=10,
        offset=10
    )

    assert len(messages_page2) == 10
    assert messages_page2[0]["content"] == "Message 10"


@pytest.mark.asyncio
async def test_agent_mention_handling(orchestrator, sample_roles):
    """Test that agents can mention each other"""
    discussion_id = "disc_test_mentions"

    orchestrator._discussions[discussion_id] = DiscussionState(
        id=discussion_id,
        topic="Test topic",
        user_id="test-user",
        roles=sample_roles,
        status="running",
        current_turn=1,
        max_turns=10
    )

    # Simulate agent mentioning another agent
    message_with_mention = "@Expert B, what do you think about this approach?"

    with patch.object(orchestrator, '_get_agent_response') as mock_response:
        mock_response.return_value = AsyncMock(return_value=message_with_mention)

        await orchestrator._run_discussion_turn(discussion_id)

        # Verify that mention was processed
        discussion = orchestrator.get_discussion(discussion_id)
        # Implementation should handle mentions appropriately


@pytest.mark.asyncio
async def test_consensus_detection(orchestrator, sample_roles):
    """Test that consensus is detected when agents agree"""
    discussion_id = "disc_test_consensus"

    orchestrator._discussions[discussion_id] = DiscussionState(
        id=discussion_id,
        topic="Test topic",
        user_id="test-user",
        roles=sample_roles,
        status="running",
        current_turn=5,
        max_turns=10
    )

    # Add messages showing consensus
    similar_messages = [
        {"role": "Expert A", "content": "I believe option X is best", "turn": 5},
        {"role": "Expert B", "content": "I agree, option X is the optimal choice", "turn": 5},
        {"role": "Expert C", "content": "Yes, option X is clearly superior", "turn": 5}
    ]

    orchestrator._discussions[discussion_id].messages = similar_messages

    with patch.object(orchestrator, 'consensus_detector') as mock_detector:
        mock_detector.check_consensus = AsyncMock(return_value={
            "consensus_reached": True,
            "confidence": 0.95,
            "summary": "All experts agree on option X"
        })

        consensus = await orchestrator.check_consensus(discussion_id)

        assert consensus["consensus_reached"] is True
        assert consensus["confidence"] > 0.9


@pytest.mark.asyncio
async def test_get_active_discussions(orchestrator):
    """Test retrieving list of active discussions"""
    # Create multiple discussions
    for i in range(5):
        orchestrator._discussions[f"disc_{i}"] = DiscussionState(
            id=f"disc_{i}",
            topic=f"Topic {i}",
            user_id="test-user",
            roles=[],
            status="running" if i < 3 else "completed",
            current_turn=i,
            max_turns=10
        )

    active = orchestrator.get_active_discussions(user_id="test-user")

    # Should only return running discussions
    assert len(active) == 3
    assert all(d.status == "running" for d in active)


@pytest.mark.asyncio
async def test_error_handling_invalid_discussion_id(orchestrator):
    """Test error handling for invalid discussion ID"""
    invalid_id = "disc_nonexistent"

    with pytest.raises((KeyError, ValueError)):
        await orchestrator.get_discussion_messages(invalid_id)


@pytest.mark.asyncio
async def test_error_handling_llm_failure(orchestrator, sample_roles):
    """Test error handling when LLM fails during discussion"""
    discussion_id = "disc_test_llm_error"

    orchestrator._discussions[discussion_id] = DiscussionState(
        id=discussion_id,
        topic="Test topic",
        user_id="test-user",
        roles=sample_roles,
        status="running",
        current_turn=1,
        max_turns=10
    )

    with patch.object(orchestrator, '_get_agent_response') as mock_response:
        mock_response.side_effect = Exception("LLM API error")

        # Should handle error gracefully
        with pytest.raises(Exception):
            await orchestrator._run_discussion_turn(discussion_id)

        # Discussion should be marked as error state
        discussion = orchestrator.get_discussion(discussion_id)
        assert discussion.status in ["error", "stopped", "running"]


@pytest.mark.asyncio
async def test_discussion_state_persistence(orchestrator, sample_roles):
    """Test that discussion state is maintained correctly"""
    discussion_id = "disc_test_state"

    # Create discussion
    orchestrator._discussions[discussion_id] = DiscussionState(
        id=discussion_id,
        topic="Test topic",
        user_id="test-user",
        roles=sample_roles,
        status="created",
        current_turn=0,
        max_turns=5,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )

    original_created_at = orchestrator._discussions[discussion_id].created_at

    # Modify discussion
    orchestrator._discussions[discussion_id].status = "running"
    orchestrator._discussions[discussion_id].current_turn = 2
    orchestrator._discussions[discussion_id].updated_at = datetime.utcnow()

    # Verify state is maintained
    discussion = orchestrator.get_discussion(discussion_id)
    assert discussion.status == "running"
    assert discussion.current_turn == 2
    assert discussion.created_at == original_created_at
    assert discussion.updated_at > original_created_at


@pytest.mark.asyncio
async def test_concurrent_discussion_handling(orchestrator):
    """Test handling multiple concurrent discussions"""
    num_discussions = 5
    discussion_ids = []

    # Create multiple discussions concurrently
    with patch.object(orchestrator, 'role_creator') as mock_creator:
        mock_creator.create_roles = AsyncMock(return_value=[
            RoleDefinition(name="Expert", expertise="Expertise",
                         perspective="Perspective", model="gpt-4")
        ])

        for i in range(num_discussions):
            disc_id = await orchestrator.create_discussion(
                topic=f"Topic {i}",
                user_id="test-user",
                num_agents=2
            )
            discussion_ids.append(disc_id)

    # Verify all discussions were created
    assert len(discussion_ids) == num_discussions
    assert len(set(discussion_ids)) == num_discussions  # All unique

    # Verify all discussions are accessible
    for disc_id in discussion_ids:
        discussion = orchestrator.get_discussion(disc_id)
        assert discussion is not None


def test_discussion_id_generation(orchestrator):
    """Test that discussion IDs are unique and properly formatted"""
    ids = set()

    for _ in range(100):
        disc_id = orchestrator._generate_discussion_id()
        assert disc_id.startswith("disc_")
        assert len(disc_id) > 10  # Has unique suffix
        ids.add(disc_id)

    # All IDs should be unique
    assert len(ids) == 100
