"""
API Integration Tests
Tests for FastAPI endpoints and WebSocket functionality
"""
import pytest
import asyncio
from fastapi.testclient import TestClient
from httpx import AsyncClient
import json

from src.api.main import app
from src.database.session import engine, Base
from src.utils.config import settings


# Test client
client = TestClient(app)


@pytest.fixture(scope="module")
async def setup_database():
    """Create test database"""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture
def test_topic():
    """Test discussion topic"""
    return "What are the best strategies for treating chronic migraine?"


# ============================================================================
# ROOT AND HEALTH ENDPOINTS
# ============================================================================

def test_root_endpoint():
    """Test root endpoint"""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["service"] == "CAMEL Discussion API"
    assert data["status"] == "running"
    assert "version" in data


def test_health_endpoint():
    """Test health check endpoint"""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == "camel-discussion-api"
    assert "version" in data
    assert "active_discussions" in data
    assert "total_connections" in data


# ============================================================================
# MODELS API TESTS
# ============================================================================

def test_list_models():
    """Test listing available models"""
    response = client.get("/api/models/")
    assert response.status_code == 200
    data = response.json()
    assert "models" in data
    assert "count" in data
    assert data["count"] > 0
    assert len(data["models"]) == data["count"]

    # Check model structure
    model = data["models"][0]
    assert "id" in model
    assert "name" in model
    assert "provider" in model
    assert "context_length" in model
    assert "pricing" in model
    assert "capabilities" in model


def test_get_model_info():
    """Test getting specific model info"""
    response = client.get("/api/models/openai/gpt-4")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == "openai/gpt-4"
    assert data["name"] == "GPT-4"
    assert data["provider"] == "OpenAI"


def test_get_nonexistent_model():
    """Test getting info for non-existent model"""
    response = client.get("/api/models/nonexistent/model")
    assert response.status_code == 404


def test_normalize_model_name():
    """Test model name normalization"""
    response = client.get("/api/models/normalize/gpt-4")
    assert response.status_code == 200
    data = response.json()
    assert data["input"] == "gpt-4"
    assert data["normalized"] == "openai/gpt-4"
    assert data["valid"] is True


def test_list_providers():
    """Test listing providers"""
    response = client.get("/api/models/providers/list")
    assert response.status_code == 200
    data = response.json()
    assert "providers" in data
    assert "total_providers" in data
    assert data["total_providers"] > 0

    # Check provider structure
    provider = data["providers"][0]
    assert "name" in provider
    assert "models" in provider
    assert "count" in provider


# ============================================================================
# ROLES API TESTS
# ============================================================================

def test_get_role_templates():
    """Test getting role templates"""
    response = client.get("/api/roles/templates")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) > 0

    # Check template structure
    template = data[0]
    assert "id" in template
    assert "name" in template
    assert "expertise" in template
    assert "perspective" in template
    assert "applicable_topics" in template
    assert "example_use_cases" in template


def test_get_specific_role_template():
    """Test getting specific role template"""
    response = client.get("/api/roles/templates/researcher")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == "researcher"
    assert data["name"] == "Research Scientist"


def test_get_nonexistent_role_template():
    """Test getting non-existent role template"""
    response = client.get("/api/roles/templates/nonexistent")
    assert response.status_code == 404


def test_analyze_topic():
    """Test topic analysis"""
    response = client.post(
        "/api/roles/analyze-topic",
        params={"topic": "What are the best strategies for treating chronic migraine?"}
    )
    assert response.status_code == 200
    data = response.json()
    assert "topic" in data
    assert "domain" in data
    assert "complexity" in data
    assert "key_aspects" in data
    assert "recommended_expertise" in data
    assert "suggested_num_roles" in data


def test_get_roles_by_domain():
    """Test getting roles by domain"""
    response = client.get("/api/roles/by-domain/medical")
    assert response.status_code == 200
    data = response.json()
    assert data["domain"] == "medical"
    assert "roles" in data
    assert "count" in data


@pytest.mark.integration
async def test_preview_roles(test_topic):
    """Test previewing roles for a topic"""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.post(
            "/api/roles/preview",
            json={
                "topic": test_topic,
                "num_roles": 3,
                "model_preferences": ["gpt-4"]
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert data["topic"] == test_topic
        assert "roles" in data
        assert len(data["roles"]) == 3
        assert "topic_analysis" in data

        # Check role structure
        role = data["roles"][0]
        assert "name" in role
        assert "expertise" in role
        assert "perspective" in role
        assert "model" in role
        assert "system_prompt" in role


# ============================================================================
# DISCUSSIONS API TESTS
# ============================================================================

@pytest.mark.integration
@pytest.mark.slow
async def test_create_discussion(test_topic, setup_database):
    """Test creating a discussion"""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.post(
            "/api/discussions/create",
            json={
                "topic": test_topic,
                "num_agents": 3,
                "model_preferences": ["gpt-4"],
                "user_id": "test_user",
                "max_turns": 5
            }
        )
        assert response.status_code == 201
        data = response.json()
        assert "discussion_id" in data
        assert data["topic"] == test_topic
        assert data["status"] == "running"
        assert len(data["roles"]) == 3
        assert "websocket_url" in data

        return data["discussion_id"]


@pytest.mark.integration
async def test_get_discussion(test_topic, setup_database):
    """Test getting discussion details"""
    # First create a discussion
    discussion_id = await test_create_discussion(test_topic, setup_database)

    async with AsyncClient(app=app, base_url="http://test") as ac:
        # Wait a bit for discussion to start
        await asyncio.sleep(2)

        # Get discussion details
        response = await ac.get(f"/api/discussions/{discussion_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["discussion_id"] == discussion_id
        assert data["topic"] == test_topic
        assert "status" in data
        assert "current_turn" in data
        assert "max_turns" in data


@pytest.mark.integration
async def test_get_nonexistent_discussion():
    """Test getting non-existent discussion"""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.get("/api/discussions/nonexistent_id")
        assert response.status_code == 404


@pytest.mark.integration
async def test_send_message_to_discussion(test_topic, setup_database):
    """Test sending user message to discussion"""
    # First create a discussion
    discussion_id = await test_create_discussion(test_topic, setup_database)

    async with AsyncClient(app=app, base_url="http://test") as ac:
        # Send user message
        response = await ac.post(
            f"/api/discussions/{discussion_id}/message",
            json={
                "content": "Please focus on evidence-based treatments",
                "user_id": "test_user"
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "sent"
        assert data["discussion_id"] == discussion_id


@pytest.mark.integration
async def test_get_discussion_messages(test_topic, setup_database):
    """Test getting discussion messages"""
    # First create a discussion
    discussion_id = await test_create_discussion(test_topic, setup_database)

    async with AsyncClient(app=app, base_url="http://test") as ac:
        # Wait for some messages
        await asyncio.sleep(5)

        # Get messages
        response = await ac.get(
            f"/api/discussions/{discussion_id}/messages",
            params={"limit": 100, "offset": 0}
        )
        assert response.status_code == 200
        data = response.json()
        assert "messages" in data
        assert "count" in data
        assert "offset" in data
        assert "limit" in data

        if data["count"] > 0:
            message = data["messages"][0]
            assert "id" in message
            assert "discussion_id" in message
            assert "role_name" in message
            assert "model" in message
            assert "content" in message
            assert "is_user" in message
            assert "created_at" in message


@pytest.mark.integration
async def test_stop_discussion(test_topic, setup_database):
    """Test stopping a discussion"""
    # First create a discussion
    discussion_id = await test_create_discussion(test_topic, setup_database)

    async with AsyncClient(app=app, base_url="http://test") as ac:
        # Stop discussion
        response = await ac.post(f"/api/discussions/{discussion_id}/stop")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "stopped"
        assert data["discussion_id"] == discussion_id


@pytest.mark.integration
async def test_delete_discussion(test_topic, setup_database):
    """Test deleting a discussion"""
    # First create a discussion
    discussion_id = await test_create_discussion(test_topic, setup_database)

    async with AsyncClient(app=app, base_url="http://test") as ac:
        # Delete discussion
        response = await ac.delete(f"/api/discussions/{discussion_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "deleted"
        assert data["discussion_id"] == discussion_id

        # Verify discussion is gone
        response = await ac.get(f"/api/discussions/{discussion_id}")
        assert response.status_code == 404


# ============================================================================
# ERROR HANDLING TESTS
# ============================================================================

@pytest.mark.integration
async def test_create_discussion_invalid_topic():
    """Test creating discussion with invalid topic"""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.post(
            "/api/discussions/create",
            json={
                "topic": "short",  # Too short (min 10 chars)
                "num_agents": 3,
                "user_id": "test_user"
            }
        )
        assert response.status_code == 422  # Validation error


@pytest.mark.integration
async def test_create_discussion_invalid_num_agents():
    """Test creating discussion with invalid number of agents"""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.post(
            "/api/discussions/create",
            json={
                "topic": "What are the best strategies for treating chronic migraine?",
                "num_agents": 1,  # Too few (min 2)
                "user_id": "test_user"
            }
        )
        assert response.status_code == 422  # Validation error


# ============================================================================
# PERFORMANCE TESTS
# ============================================================================

@pytest.mark.performance
async def test_concurrent_discussions(test_topic, setup_database):
    """Test creating multiple concurrent discussions"""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        # Create 3 concurrent discussions
        tasks = []
        for i in range(3):
            task = ac.post(
                "/api/discussions/create",
                json={
                    "topic": f"{test_topic} (variant {i})",
                    "num_agents": 2,
                    "model_preferences": ["gpt-4"],
                    "user_id": f"test_user_{i}",
                    "max_turns": 3
                }
            )
            tasks.append(task)

        responses = await asyncio.gather(*tasks)

        # All should succeed
        for response in responses:
            assert response.status_code == 201
            data = response.json()
            assert "discussion_id" in data


@pytest.mark.performance
def test_api_response_times():
    """Test API response times"""
    import time

    endpoints = [
        "/",
        "/health",
        "/api/models/",
        "/api/roles/templates"
    ]

    for endpoint in endpoints:
        start = time.time()
        response = client.get(endpoint)
        elapsed = (time.time() - start) * 1000  # Convert to ms

        assert response.status_code == 200
        assert elapsed < 1000  # Should respond within 1 second
        print(f"{endpoint}: {elapsed:.2f}ms")
