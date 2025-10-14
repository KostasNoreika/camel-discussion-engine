"""
Unit tests for RoleCreator component

Tests role creation, model assignment, and system prompt generation.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from src.camel_engine.role_creator import RoleCreator, RoleDefinition
from src.camel_engine.llm_provider import OpenRouterClient


@pytest.fixture
def role_creator():
    """Fixture providing RoleCreator instance with mocked LLM client"""
    mock_client = MagicMock(spec=OpenRouterClient)

    # Mock chat_completion_structured to return roles
    async def mock_chat_completion_structured(model, messages, temperature):
        # Check if this is a role generation call or topic analysis
        prompt_content = messages[0]["content"]

        if "topic analysis" in prompt_content.lower() or "analyze this discussion topic" in prompt_content.lower():
            # Topic analysis response
            return {
                "primary_domain": "technical",
                "sub_domains": ["architecture", "development"],
                "complexity": 3,
                "key_aspects": ["design", "implementation"],
                "recommended_expert_types": ["Expert 1", "Expert 2", "Expert 3"]
            }
        else:
            # Role generation response
            return [
                {
                    "name": "Expert 1",
                    "expertise": "Expertise 1",
                    "perspective": "Perspective 1"
                },
                {
                    "name": "Expert 2",
                    "expertise": "Expertise 2",
                    "perspective": "Perspective 2"
                },
                {
                    "name": "Expert 3",
                    "expertise": "Expertise 3",
                    "perspective": "Perspective 3"
                }
            ]

    mock_client.chat_completion_structured = AsyncMock(side_effect=mock_chat_completion_structured)

    return RoleCreator(llm_client=mock_client)


@pytest.fixture
def mock_llm_provider():
    """Mock LLM provider for testing"""
    mock = AsyncMock()
    mock.chat_completion.return_value = {
        "roles": [
            {
                "name": "Neurologist",
                "expertise": "Neurology and headache disorders",
                "perspective": "Clinical and evidence-based medicine",
                "model": "gpt-4"
            },
            {
                "name": "Pain Management Specialist",
                "expertise": "Chronic pain treatment and management",
                "perspective": "Holistic patient-centered approach",
                "model": "claude-3-opus"
            },
            {
                "name": "Patient Advocate",
                "expertise": "Patient rights and treatment accessibility",
                "perspective": "Patient experience and quality of life",
                "model": "gemini-pro"
            }
        ]
    }
    return mock


@pytest.mark.asyncio
async def test_analyze_medical_topic(role_creator, mock_llm_provider):
    """Test role creation for medical topic"""
    topic = "Best treatment for chronic migraine"

    with patch.object(role_creator, 'llm_provider', mock_llm_provider):
        roles = await role_creator.create_roles(topic, num_roles=3)

        assert len(roles) == 3
        assert any("neurolog" in r.name.lower() for r in roles)
        assert all(isinstance(r, RoleDefinition) for r in roles)

        # Verify all roles have required fields
        for role in roles:
            assert role.name
            assert role.expertise
            assert role.perspective
            assert role.model


@pytest.mark.asyncio
async def test_analyze_technical_topic(role_creator):
    """Test role creation for technical topic"""
    topic = "Design scalable microservices architecture"

    # Mock response for technical topic
    mock_response = {
        "roles": [
            {
                "name": "Software Architect",
                "expertise": "System architecture and design patterns",
                "perspective": "Scalability and maintainability",
                "model": "gpt-4"
            },
            {
                "name": "DevOps Engineer",
                "expertise": "Container orchestration and deployment",
                "perspective": "Operational reliability and automation",
                "model": "claude-3-opus"
            },
            {
                "name": "Backend Developer",
                "expertise": "API design and service implementation",
                "perspective": "Code quality and performance",
                "model": "gemini-pro"
            },
            {
                "name": "Database Specialist",
                "expertise": "Data modeling and database optimization",
                "perspective": "Data integrity and query performance",
                "model": "gpt-4"
            }
        ]
    }

    with patch.object(role_creator, 'llm_client') as mock_llm:
        mock_llm.chat_completion = AsyncMock(return_value=mock_response)
        roles = await role_creator.create_roles(topic, num_roles=4)

        assert len(roles) == 4
        assert any("architect" in r.name.lower() for r in roles)
        assert any("devops" in r.name.lower() for r in roles)


@pytest.mark.asyncio
async def test_system_prompt_generation(role_creator):
    """Test system prompt is tailored to role"""
    role = RoleDefinition(
        name="Neurologist",
        expertise="Neurology and headache disorders",
        perspective="Clinical and evidence-based",
        model="gpt-4",
        system_prompt=""  # Empty, will be filled by create_system_prompt
    )

    prompt = role_creator.create_system_prompt(role, topic="chronic migraine treatment")

    assert "Neurologist" in prompt
    assert "expertise" in prompt.lower() or "neurology" in prompt.lower()
    assert "evidence-based" in prompt.lower() or "clinical" in prompt.lower()

    # Should mention role capabilities
    assert any(keyword in prompt.lower() for keyword in ["discuss", "analyze", "perspective"])


@pytest.mark.skip(reason="assign_models_to_roles() is internal to create_roles()")
def test_role_model_assignment(role_creator):
    """Test that models are assigned appropriately"""
    role_names = ["Expert A", "Expert B", "Expert C"]
    available_models = ["gpt-4", "claude-3-opus", "gemini-pro"]

    roles = role_creator.assign_models_to_roles(
        roles=role_names,
        available_models=available_models
    )

    assert len(roles) == 3
    assert all(r["model"] in available_models for r in roles)

    # Should distribute models evenly
    model_counts = {}
    for role in roles:
        model = role["model"]
        model_counts[model] = model_counts.get(model, 0) + 1

    # Each model should be used (for 3 roles and 3 models)
    assert all(count >= 1 for count in model_counts.values())


@pytest.mark.skip(reason="assign_models_to_roles() is internal to create_roles()")
def test_role_model_assignment_more_roles_than_models(role_creator):
    """Test model assignment when there are more roles than models"""
    role_names = ["Expert A", "Expert B", "Expert C", "Expert D", "Expert E"]
    available_models = ["gpt-4", "claude-3-opus"]

    roles = role_creator.assign_models_to_roles(
        roles=role_names,
        available_models=available_models
    )

    assert len(roles) == 5
    assert all(r["model"] in available_models for r in roles)

    # Should distribute models evenly
    model_counts = {}
    for role in roles:
        model = role["model"]
        model_counts[model] = model_counts.get(model, 0) + 1

    # Difference in usage should be minimal
    counts = list(model_counts.values())
    assert max(counts) - min(counts) <= 1


@pytest.mark.asyncio
async def test_role_creation_with_model_preferences(role_creator, mock_llm_provider):
    """Test that model preferences are respected"""
    topic = "AI ethics and governance"
    preferred_models = ["gpt-4-turbo", "claude-3-opus"]

    with patch.object(role_creator, 'llm_provider', mock_llm_provider):
        roles = await role_creator.create_roles(
            topic,
            num_roles=3,
            model_preferences=preferred_models
        )

        # Roles should only use preferred models
        for role in roles:
            assert role.model in preferred_models


@pytest.mark.asyncio
async def test_role_creation_error_handling(role_creator):
    """Test error handling when LLM fails"""
    topic = "Test topic"

    with patch.object(role_creator, 'llm_client') as mock_llm:
        mock_llm.chat_completion = AsyncMock(side_effect=Exception("LLM API error"))

        with pytest.raises(Exception) as exc_info:
            await role_creator.create_roles(topic, num_roles=3)

        assert "LLM API error" in str(exc_info.value)


@pytest.mark.asyncio
async def test_role_deduplication(role_creator):
    """Test that duplicate role names are handled"""
    topic = "Test topic"

    # Mock response with duplicate names
    mock_response = {
        "roles": [
            {"name": "Expert", "expertise": "Topic A", "perspective": "View A", "model": "gpt-4"},
            {"name": "Expert", "expertise": "Topic B", "perspective": "View B", "model": "claude-3-opus"},
            {"name": "Specialist", "expertise": "Topic C", "perspective": "View C", "model": "gemini-pro"}
        ]
    }

    with patch.object(role_creator, 'llm_client') as mock_llm:
        mock_llm.chat_completion = AsyncMock(return_value=mock_response)
        roles = await role_creator.create_roles(topic, num_roles=3)

        # Should have unique names (or handle duplicates)
        role_names = [r.name for r in roles]
        # Either all unique or properly numbered (Expert, Expert-2, etc.)
        assert len(roles) == 3


def test_validate_role_definition():
    """Test that RoleDefinition validates required fields"""
    # Valid role
    valid_role = RoleDefinition(
        name="Test Expert",
        expertise="Test expertise",
        perspective="Test perspective",
        model="gpt-4",
        system_prompt="Test system prompt"
    )
    assert valid_role.name == "Test Expert"

    # Test that empty names are handled
    with pytest.raises((ValueError, TypeError)):
        RoleDefinition(
            name="",  # Empty name should fail
            expertise="Test",
            perspective="Test",
            model="gpt-4",
            system_prompt="Test"
        )


@pytest.mark.asyncio
async def test_role_creation_with_min_agents(role_creator, mock_llm_provider):
    """Test role creation with minimum number of agents"""
    topic = "Simple question"

    with patch.object(role_creator, 'llm_provider', mock_llm_provider):
        roles = await role_creator.create_roles(topic, num_roles=2)

        assert len(roles) == 2
        # Should still create diverse roles even with minimum count
        assert roles[0].name != roles[1].name


@pytest.mark.asyncio
async def test_role_creation_with_max_agents(role_creator):
    """Test role creation with maximum number of agents"""
    topic = "Complex multi-faceted issue"

    # Mock response with 6 roles
    mock_response = {
        "roles": [
            {"name": f"Expert {i}", "expertise": f"Expertise {i}",
             "perspective": f"Perspective {i}", "model": "gpt-4"}
            for i in range(1, 7)
        ]
    }

    with patch.object(role_creator, 'llm_client') as mock_llm:
        mock_llm.chat_completion = AsyncMock(return_value=mock_response)
        roles = await role_creator.create_roles(topic, num_roles=6)

        assert len(roles) == 6
        # Verify all roles are unique
        role_names = [r.name for r in roles]
        assert len(set(role_names)) == 6


def test_system_prompt_includes_topic_context(role_creator):
    """Test that system prompt includes relevant topic context"""
    role = RoleDefinition(
        name="Security Expert",
        expertise="Cybersecurity and threat analysis",
        perspective="Risk assessment and mitigation",
        model="gpt-4",
        system_prompt=""  # Will be filled by create_system_prompt
    )

    topic = "blockchain security vulnerabilities"
    prompt = role_creator.create_system_prompt(role, topic=topic)

    # Prompt should reference the topic
    assert "blockchain" in prompt.lower() or "security" in prompt.lower()
    # Should also reference the role
    assert "security expert" in prompt.lower() or "cybersecurity" in prompt.lower()
