# CAMEL Discussion System - Test Summary

**Project**: CAMEL Multi-Agent Discussion System
**Test Suite Version**: 1.0.0
**Last Updated**: 2025-10-12

---

## Overview

Comprehensive test suite covering unit tests, integration tests, end-to-end tests, and load testing for the CAMEL Discussion System.

### Test Statistics

| Test Type | Files | Tests | Coverage Target |
|-----------|-------|-------|-----------------|
| **Unit Tests** | 4 | 85+ | > 80% |
| **Integration Tests** | 2 | 26+ | All critical paths |
| **E2E Tests** | 1 | 11+ | Complete workflows |
| **Load Tests** | 1 | N/A | Performance metrics |
| **Total** | 8 | **122+** | Comprehensive |

---

## Test Structure

```
tests/
├── conftest.py                      # Pytest configuration & fixtures
├── pytest.ini                       # Test settings
├── TEST_SUMMARY.md                  # This file
├── unit/                            # Unit tests (85+ tests)
│   ├── test_role_creator.py        # Role creation (18 tests)
│   ├── test_orchestrator.py        # Discussion orchestration (22 tests)
│   ├── test_consensus.py           # Consensus detection (21 tests)
│   └── test_websocket_manager.py   # WebSocket management (24 tests)
├── integration/                     # Integration tests (26+ tests)
│   ├── test_api.py                 # API endpoints (from TASK-003)
│   └── test_camel_integration.py   # CAMEL-AI integration
├── e2e/                             # End-to-end tests (11+ tests)
│   └── test_complete_discussion.py # Full workflows
└── load/                            # Load testing
    └── locustfile.py               # Locust load tests
```

---

## Unit Tests

### 1. Role Creator Tests (`test_role_creator.py`)
**Tests**: 18 | **Coverage**: Role creation & management

#### Test Categories:
- ✅ **Topic Analysis** (3 tests)
  - Medical topic role creation
  - Technical topic role creation
  - Role deduplication

- ✅ **System Prompt Generation** (2 tests)
  - Tailored prompts for roles
  - Topic context inclusion

- ✅ **Model Assignment** (3 tests)
  - Even distribution
  - More roles than models
  - Model preferences

- ✅ **Error Handling** (2 tests)
  - LLM API failures
  - Invalid inputs

- ✅ **Edge Cases** (4 tests)
  - Minimum agents (2)
  - Maximum agents (6)
  - Empty names
  - Duplicate names

- ✅ **Validation** (4 tests)
  - Field validation
  - Model preferences
  - Role definition structure

#### Sample Test:
```python
@pytest.mark.asyncio
async def test_analyze_medical_topic(role_creator, mock_llm_provider):
    """Test role creation for medical topic"""
    topic = "Best treatment for chronic migraine"
    roles = await role_creator.create_roles(topic, num_roles=3)

    assert len(roles) == 3
    assert any("neurolog" in r.name.lower() for r in roles)
    assert all(isinstance(r, RoleDefinition) for r in roles)
```

### 2. Orchestrator Tests (`test_orchestrator.py`)
**Tests**: 22 | **Coverage**: Discussion lifecycle management

#### Test Categories:
- ✅ **Discussion Creation** (3 tests)
  - Basic creation
  - With model preferences
  - ID generation

- ✅ **Discussion Lifecycle** (5 tests)
  - Start discussion
  - Turn management
  - Max turns enforcement
  - Stop discussion
  - State persistence

- ✅ **User Interaction** (3 tests)
  - Send user messages
  - Get messages
  - Message pagination

- ✅ **Multi-Discussion** (2 tests)
  - Active discussions list
  - Concurrent handling

- ✅ **Error Handling** (3 tests)
  - Invalid discussion ID
  - LLM failures
  - Concurrent operations

- ✅ **Advanced Features** (6 tests)
  - Agent mentions
  - Consensus detection
  - Message history
  - Discussion status
  - Concurrent discussions

#### Sample Test:
```python
@pytest.mark.asyncio
async def test_create_discussion(orchestrator):
    """Test creating a new discussion"""
    discussion_id = await orchestrator.create_discussion(
        topic="Test topic",
        user_id="test-user",
        num_agents=3
    )

    assert discussion_id.startswith("disc_")
    discussion = orchestrator.get_discussion(discussion_id)
    assert len(discussion.roles) == 3
```

### 3. Consensus Detector Tests (`test_consensus.py`)
**Tests**: 21 | **Coverage**: Consensus analysis

#### Test Categories:
- ✅ **Consensus Detection** (5 tests)
  - Strong agreement
  - Clear disagreement
  - Partial agreement
  - Minimum messages
  - Eventual consensus

- ✅ **Similarity Analysis** (2 tests)
  - Semantic similarity
  - Message comparison

- ✅ **Keyword Detection** (2 tests)
  - Agreement keywords ("agree", "concur")
  - Disagreement keywords ("disagree", "oppose")

- ✅ **Summary Generation** (2 tests)
  - Meaningful summaries
  - Key points extraction

- ✅ **Configuration** (2 tests)
  - Confidence range validation
  - Threshold configuration

- ✅ **Advanced Features** (8 tests)
  - Recent message focus
  - Mention chains
  - Numerical consensus
  - Divergence detection
  - LLM analysis
  - Empty messages
  - Performance with many messages

#### Sample Test:
```python
@pytest.mark.asyncio
async def test_detect_consensus_strong_agreement(consensus_detector):
    """Test consensus detection with strong agreement"""
    messages = [
        {"role": "Expert A", "content": "Option X is best..."},
        {"role": "Expert B", "content": "I agree, option X..."},
        {"role": "Expert C", "content": "Yes, option X..."}
    ]

    result = await consensus_detector.analyze_messages(messages)

    assert result.consensus_reached is True
    assert result.confidence > 0.7
```

### 4. WebSocket Manager Tests (`test_websocket_manager.py`)
**Tests**: 24 | **Coverage**: Real-time communication

#### Test Categories:
- ✅ **Connection Management** (6 tests)
  - New connections
  - Multiple clients
  - Disconnection
  - Empty discussion cleanup
  - Connection count
  - Connection mapping

- ✅ **Message Broadcasting** (5 tests)
  - Broadcast to all clients
  - Nonexistent discussion
  - Dead connection removal
  - Personal messages
  - Concurrent broadcast

- ✅ **Convenience Methods** (3 tests)
  - Agent messages
  - Consensus updates
  - Discussion complete

- ✅ **Advanced Features** (6 tests)
  - Disconnect all
  - Active discussions list
  - Message serialization
  - Connection limits
  - Heartbeat ping
  - Graceful error handling

- ✅ **Error Handling** (4 tests)
  - Dead connections
  - Disconnect errors
  - Complex message serialization
  - Connection limit enforcement

#### Sample Test:
```python
@pytest.mark.asyncio
async def test_broadcast_message_to_all_clients(connection_manager):
    """Test broadcasting message to all connected clients"""
    ws1, ws2, ws3 = AsyncMock(), AsyncMock(), AsyncMock()

    await connection_manager.connect(ws1, "disc_123")
    await connection_manager.connect(ws2, "disc_123")
    await connection_manager.connect(ws3, "disc_123")

    await connection_manager.broadcast("disc_123", {"type": "test"})

    # All clients receive message
    ws1.send_text.assert_called_once()
    ws2.send_text.assert_called_once()
    ws3.send_text.assert_called_once()
```

---

## Integration Tests

### 1. API Endpoints Tests (`test_api.py`)
**Tests**: 26+ | **From**: TASK-003

Comprehensive API testing including:
- Discussion creation
- Message sending
- Status retrieval
- WebSocket integration
- Error handling
- Pagination

See: `/opt/dev/camel-discussion-engine/tests/integration/test_api.py`

### 2. CAMEL Integration Tests (`test_camel_integration.py`)
**Tests**: Existing | **From**: TASK-002

CAMEL-AI library integration testing.

---

## End-to-End Tests

### Complete Discussion Tests (`test_complete_discussion.py`)
**Tests**: 11 | **Coverage**: Full user workflows

#### Test Scenarios:

1. **Complete Discussion Flow** (`test_complete_discussion_flow`)
   - Create discussion → WebSocket connection → Agent messages → Conclusion
   - Verifies: Message types, agent participation, consensus/completion

2. **User Intervention** (`test_user_intervention`)
   - Discussion → User message → Agent responses
   - Verifies: User guidance affects discussion direction

3. **Consensus Flow** (`test_consensus_flow`)
   - Simple topic → Consensus updates → Final consensus
   - Verifies: Consensus detection mechanism works

4. **Multiple Concurrent Discussions** (`test_multiple_concurrent_discussions`)
   - 3 simultaneous discussions → Independent progression → Cleanup
   - Verifies: System handles concurrency

5. **Agent Mentions** (`test_discussion_with_mentions`)
   - Create discussion → Mention agent → Verify response
   - Verifies: @mention functionality

6. **Early Stop** (`test_early_discussion_stop`)
   - Start discussion → Stop early → Verify termination
   - Verifies: Graceful shutdown

7. **WebSocket Reconnection** (`test_websocket_reconnection`)
   - Connect → Disconnect → Reconnect → Verify messages
   - Verifies: Reconnection resilience

8. **Message History** (`test_discussion_message_history`)
   - Discussion runs → Retrieve history → Verify order
   - Verifies: Message persistence and ordering

9. **Model Preferences** (`test_discussion_with_model_preferences`)
   - Create with preferences → Verify models used
   - Verifies: Model selection respects preferences

#### Sample Test:
```python
@pytest.mark.asyncio
@pytest.mark.e2e
async def test_complete_discussion_flow():
    """Test complete discussion from creation to consensus"""
    discussion_id = await create_test_discussion(
        topic="Best programming language for AI",
        num_agents=3
    )

    ws_url = f"ws://localhost:8007/ws/discussions/{discussion_id}"
    messages_received = []

    async with ws_connect(ws_url) as websocket:
        # Collect messages until completion
        while True:
            message = await websocket.recv()
            msg_data = json.loads(message)
            messages_received.append(msg_data)

            if msg_data["type"] in ["consensus_reached", "discussion_complete"]:
                break

    # Verify discussion completed successfully
    assert len(messages_received) > 0
    agent_messages = [m for m in messages_received if m["type"] == "agent_message"]
    assert len(agent_messages) > 0
```

---

## Load Testing

### Locust Load Tests (`locustfile.py`)

#### User Classes:

**1. DiscussionUser** (Standard User)
- **Weight Distribution**:
  - Create discussion: 1 (expensive)
  - Get discussion: 3 (frequent)
  - Get messages: 2 (moderate)
  - Send message: 1 (triggers responses)
  - Stop discussion: 1 (cleanup)
  - Health check: 2 (lightweight)
  - List models: 1 (occasional)

**2. HeavyDiscussionUser** (Stress Testing)
- Creates discussions with 6 agents (maximum)
- Long discussions (30 turns)
- Message bursts (3 messages at once)
- Large history retrieval (100 messages)

**3. ReadOnlyUser** (Read Scalability)
- Only reads, no writes
- Tests read endpoint performance
- Rapid polling (0.5-1.5s wait)

#### Running Load Tests:

```bash
# Standard load test (10 users)
locust -f tests/load/locustfile.py --host=http://localhost:8007

# Web UI (open browser)
locust -f tests/load/locustfile.py --host=http://localhost:8007 --web-host=0.0.0.0

# Headless (command line)
locust -f tests/load/locustfile.py --host=http://localhost:8007 \
    --users 50 --spawn-rate 5 --run-time 5m --headless

# Specific user class
locust -f tests/load/locustfile.py --user-classes HeavyDiscussionUser \
    --users 5 --spawn-rate 1

# Read-only testing
locust -f tests/load/locustfile.py --user-classes ReadOnlyUser \
    --users 100 --spawn-rate 10
```

#### WebSocket Load Testing:

```bash
# Run WebSocket load test directly
cd tests/load
python locustfile.py
```

Tests 20 concurrent WebSocket clients receiving messages for 30 seconds.

---

## Performance Targets

| Metric | Target | Method | Status |
|--------|--------|--------|--------|
| **API Response Time** | < 200ms | Locust | ⏳ To measure |
| **WebSocket Latency** | < 500ms | Custom script | ⏳ To measure |
| **Concurrent Discussions** | 10+ | Locust | ⏳ To measure |
| **Messages/second** | 50+ | Load test | ⏳ To measure |
| **Memory Usage** | < 2GB | Docker stats | ⏳ To measure |
| **Code Coverage** | > 80% | pytest-cov | ⏳ To measure |

---

## Running Tests

### Quick Commands

```bash
# All tests
pytest tests/ -v

# Unit tests only (fast)
pytest tests/unit/ -v

# Integration tests (requires API key)
pytest tests/integration/ -v

# E2E tests (requires running API)
pytest tests/e2e/ -v

# Skip slow tests
pytest tests/ -v -m "not slow"

# Specific test file
pytest tests/unit/test_role_creator.py -v

# Specific test
pytest tests/unit/test_role_creator.py::test_analyze_medical_topic -v
```

### Coverage

```bash
# Run with coverage
pytest tests/ --cov=src --cov-report=html

# View coverage report
open htmlcov/index.html

# Coverage for specific module
pytest tests/unit/ --cov=src.camel_engine --cov-report=term-missing

# Fail if coverage < 80%
pytest tests/ --cov=src --cov-fail-under=80
```

### Markers

```bash
# Unit tests only
pytest -m unit

# Integration tests
pytest -m integration

# E2E tests
pytest -m e2e

# Slow tests
pytest -m slow

# Exclude slow tests
pytest -m "not slow"

# Multiple markers
pytest -m "unit or integration"
```

### Parallel Execution

```bash
# Install pytest-xdist
pip install pytest-xdist

# Run tests in parallel (4 workers)
pytest tests/ -n 4

# Auto-detect CPU count
pytest tests/ -n auto
```

---

## Test Data & Fixtures

### Shared Fixtures (`conftest.py`)

```python
@pytest.fixture
def test_data_dir():
    """Test data directory"""
    return Path(__file__).parent / "fixtures"

@pytest.fixture
def test_topics(test_data_dir):
    """Load test topics from JSON"""
    with open(test_data_dir / "test_topics.json") as f:
        return json.load(f)
```

### Custom Markers

- `@pytest.mark.unit` - Unit test (no external dependencies)
- `@pytest.mark.integration` - Integration test (requires API key)
- `@pytest.mark.e2e` - End-to-end test (requires running API)
- `@pytest.mark.slow` - Slow test (> 30 seconds)
- `@pytest.mark.performance` - Performance benchmark

---

## Continuous Integration

### GitHub Actions (Future)

```yaml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      - run: pip install -r requirements.txt
      - run: pytest tests/ --cov=src --cov-report=xml
      - uses: codecov/codecov-action@v3
```

---

## Debugging Tests

### Verbose Output

```bash
# Extra verbose
pytest tests/ -vv

# Show print statements
pytest tests/ -s

# Show local variables on failure
pytest tests/ -l

# Drop into debugger on failure
pytest tests/ --pdb

# Stop on first failure
pytest tests/ -x
```

### Logging

```bash
# Show log output
pytest tests/ --log-cli-level=DEBUG

# Capture warnings
pytest tests/ -W default
```

---

## Known Issues & Limitations

### Current Limitations:

1. **E2E Tests** - Require running API server on port 8007
2. **Integration Tests** - Require `OPENROUTER_API_KEY` environment variable
3. **Load Tests** - Best run separately from unit/integration tests
4. **WebSocket Tests** - May have timing issues in CI environments

### Future Improvements:

- [ ] Add test database fixtures
- [ ] Mock LLM responses for faster tests
- [ ] Add property-based testing (Hypothesis)
- [ ] Improve test isolation
- [ ] Add mutation testing (mutmut)
- [ ] Add benchmark tests (pytest-benchmark)

---

## Test Maintenance

### Adding New Tests:

1. Choose appropriate directory (`unit/`, `integration/`, `e2e/`)
2. Follow naming convention (`test_*.py`)
3. Add appropriate markers (`@pytest.mark.unit`, etc.)
4. Add docstrings explaining test purpose
5. Use fixtures for common setup
6. Mock external dependencies in unit tests

### Updating Tests:

1. Run tests after changes: `pytest tests/`
2. Update coverage: `pytest --cov=src --cov-report=html`
3. Check for broken tests: `pytest tests/ -x`
4. Update documentation if test behavior changes

---

## Resources

- **Pytest Documentation**: https://docs.pytest.org/
- **pytest-asyncio**: https://pytest-asyncio.readthedocs.io/
- **Locust Documentation**: https://docs.locust.io/
- **Coverage.py**: https://coverage.readthedocs.io/

---

**Test Suite Status**: ✅ **READY FOR EXECUTION**

**Next Steps**:
1. Run full test suite
2. Measure coverage
3. Run load tests
4. Generate performance report
