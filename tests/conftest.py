"""
Pytest configuration and shared fixtures
"""
import pytest
import os
from pathlib import Path


def pytest_configure(config):
    """Configure pytest"""
    # Add custom markers
    config.addinivalue_line(
        "markers", "unit: Unit tests (no external dependencies)"
    )
    config.addinivalue_line(
        "markers", "integration: Integration tests (requires API key)"
    )
    config.addinivalue_line(
        "markers", "e2e: End-to-end tests (requires running API)"
    )
    config.addinivalue_line(
        "markers", "slow: Slow tests (> 30 seconds)"
    )
    config.addinivalue_line(
        "markers", "performance: Performance benchmarks"
    )


def pytest_collection_modifyitems(config, items):
    """Modify test collection"""
    # Skip integration tests if no API key
    api_key = os.getenv("OPENROUTER_API_KEY")

    for item in items:
        if "integration" in item.keywords and not api_key:
            item.add_marker(
                pytest.mark.skip(reason="OPENROUTER_API_KEY not set")
            )


@pytest.fixture(scope="session")
def test_data_dir():
    """Get test data directory"""
    return Path(__file__).parent / "fixtures"


@pytest.fixture(scope="session")
def test_topics(test_data_dir):
    """Load test topics"""
    import json

    topics_file = test_data_dir / "test_topics.json"
    with open(topics_file) as f:
        return json.load(f)
