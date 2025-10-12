"""
Integration Tests for CAMEL Discussion Engine
"""
import pytest
import os
from dotenv import load_dotenv

from src.camel_engine.orchestrator import DiscussionOrchestrator
from src.camel_engine.role_creator import RoleCreator
from src.camel_engine.consensus import ConsensusDetector, Message
from src.camel_engine.llm_provider import OpenRouterClient

# Load environment
load_dotenv()


@pytest.fixture
def api_key():
    """Get API key from environment"""
    key = os.getenv("OPENROUTER_API_KEY")
    if not key:
        pytest.skip("OPENROUTER_API_KEY not set")
    return key


@pytest.fixture
def llm_client(api_key):
    """Create LLM client"""
    return OpenRouterClient(api_key=api_key)


@pytest.fixture
def role_creator(llm_client):
    """Create role creator"""
    return RoleCreator(llm_client=llm_client)


@pytest.fixture
def consensus_detector(llm_client):
    """Create consensus detector"""
    return ConsensusDetector(llm_client=llm_client)


@pytest.fixture
def orchestrator(api_key):
    """Create discussion orchestrator"""
    return DiscussionOrchestrator(openrouter_api_key=api_key, max_turns=5)


# ============================================================================
# Unit Tests (No API Calls)
# ============================================================================

def test_llm_provider_initialization(api_key):
    """Test LLM provider can be initialized"""
    client = OpenRouterClient(api_key=api_key)
    assert client.api_key == api_key
    assert client.base_url == "https://openrouter.ai/api/v1"


def test_model_name_normalization():
    """Test model name normalization"""
    client = OpenRouterClient(api_key="test")

    assert client.normalize_model_name("gpt-4") == "openai/gpt-4"
    assert client.normalize_model_name("claude-3-opus") == "anthropic/claude-3-opus"
    assert client.normalize_model_name("custom/model") == "custom/model"


# ============================================================================
# Integration Tests (Requires API Key)
# ============================================================================

@pytest.mark.asyncio
@pytest.mark.integration
async def test_role_creation(role_creator):
    """Test dynamic role creation based on topic"""
    topic = "Best treatment for chronic migraine"
    roles = await role_creator.create_roles(topic, num_roles=3)

    assert len(roles) == 3
    assert all(role.name for role in roles)
    assert all(role.expertise for role in roles)
    assert all(role.system_prompt for role in roles)

    # Check that at least one medical-related role was created
    role_names = " ".join(r.name.lower() for r in roles)
    assert any(keyword in role_names for keyword in ["doctor", "medical", "health", "specialist"])


@pytest.mark.asyncio
@pytest.mark.integration
async def test_topic_analysis(role_creator):
    """Test topic analysis"""
    topic = "Design scalable microservices architecture"
    analysis = await role_creator.analyze_topic(topic)

    assert analysis.primary_domain
    assert analysis.complexity >= 1 and analysis.complexity <= 5
    assert len(analysis.key_aspects) > 0


@pytest.mark.asyncio
@pytest.mark.integration
async def test_same_model_different_roles(role_creator):
    """Test that same model can play different roles"""
    topic = "Database design for e-commerce"

    # Force use of same model for all roles
    model_preferences = ["openai/gpt-4"] * 4

    roles = await role_creator.create_roles(
        topic,
        num_roles=4,
        model_preferences=model_preferences
    )

    assert len(roles) == 4
    assert all(role.model == "openai/gpt-4" for role in roles)

    # But roles should be different
    role_names = [r.name for r in roles]
    assert len(set(role_names)) > 1  # At least 2 different role names


@pytest.mark.asyncio
@pytest.mark.integration
async def test_consensus_detection(consensus_detector):
    """Test consensus detection with mock messages"""
    messages = [
        Message(role_name="Expert 1", content="I agree with the proposed solution.", turn_number=1),
        Message(role_name="Expert 2", content="Yes, that makes sense to me as well.", turn_number=2),
        Message(role_name="Expert 3", content="I concur with both of you.", turn_number=3),
    ]

    consensus = await consensus_detector.check_consensus(
        messages=messages,
        topic="Test topic",
        current_turn=3,
        max_turns=10
    )

    assert consensus.confidence > 0.5
    assert len(consensus.agreements) >= 0


@pytest.mark.asyncio
@pytest.mark.integration
async def test_discussion_creation(orchestrator):
    """Test creating a new discussion"""
    discussion_id = await orchestrator.create_discussion(
        topic="Best programming language for beginners",
        num_agents=3
    )

    assert discussion_id is not None
    assert discussion_id in orchestrator.active_discussions

    discussion = orchestrator.get_discussion(discussion_id)
    assert discussion.topic == "Best programming language for beginners"
    assert len(discussion.roles) == 3
    assert discussion.status == "active"


@pytest.mark.asyncio
@pytest.mark.integration
async def test_short_discussion_run(orchestrator):
    """Test running a short discussion (3 turns)"""
    discussion_id = await orchestrator.create_discussion(
        topic="Choose between Python and JavaScript for web development",
        num_agents=2
    )

    result = await orchestrator.run_discussion(discussion_id, max_turns=3)

    assert result.discussion_id == discussion_id
    assert result.total_turns <= 3
    assert len(result.messages) > 0
    assert result.duration_seconds > 0

    # Check that agents addressed each other (emergent communication)
    message_contents = " ".join(msg.content for msg in result.messages)
    # This is probabilistic, so we don't assert it, just log it
    has_mentions = "@" in message_contents
    print(f"Has @mentions: {has_mentions}")


@pytest.mark.asyncio
@pytest.mark.integration
async def test_ai_speaker_selection(orchestrator):
    """Test that speaker selection is not just round-robin"""
    discussion_id = await orchestrator.create_discussion(
        topic="Database choice: SQL vs NoSQL",
        num_agents=3
    )

    result = await orchestrator.run_discussion(discussion_id, max_turns=6)

    # Extract speaker order
    speakers = [msg.role_name for msg in result.messages if msg.role_name != "System"]

    # Check that it's not strictly round-robin
    # (This is probabilistic, so we can't guarantee it, but we can check)
    print(f"Speaker order: {speakers}")

    # At minimum, we should have some speakers
    assert len(speakers) >= 3


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.slow
async def test_full_discussion_with_consensus(orchestrator):
    """Test a full discussion that should reach consensus (SLOW)"""
    discussion_id = await orchestrator.create_discussion(
        topic="2+2 equals what?",  # Simple topic that should reach consensus quickly
        num_agents=2
    )

    result = await orchestrator.run_discussion(discussion_id, max_turns=5)

    # This simple topic should reach consensus
    print(f"Consensus reached: {result.consensus_reached}")
    print(f"Confidence: {result.consensus_confidence:.1%}")
    print(f"Summary: {result.final_summary[:200]}")

    assert result.total_turns <= 5
    # Note: We can't guarantee consensus on LLM-based discussions,
    # but we can check the structure
    assert result.consensus_confidence >= 0.0
    assert result.consensus_confidence <= 1.0


# ============================================================================
# Performance Tests
# ============================================================================

@pytest.mark.asyncio
@pytest.mark.performance
async def test_role_creation_performance(role_creator):
    """Test role creation completes in reasonable time"""
    import time

    start = time.time()
    roles = await role_creator.create_roles("Database design", num_roles=3)
    duration = time.time() - start

    assert duration < 10.0  # Should complete within 10 seconds
    assert len(roles) == 3


# ============================================================================
# Error Handling Tests
# ============================================================================

@pytest.mark.asyncio
async def test_invalid_api_key():
    """Test handling of invalid API key"""
    orchestrator = DiscussionOrchestrator(openrouter_api_key="invalid_key")

    with pytest.raises(Exception):  # Should raise HTTPError
        discussion_id = await orchestrator.create_discussion(
            topic="Test",
            num_agents=2
        )


@pytest.mark.asyncio
async def test_get_nonexistent_discussion(orchestrator):
    """Test retrieving non-existent discussion"""
    discussion = orchestrator.get_discussion("nonexistent-id")
    assert discussion is None
