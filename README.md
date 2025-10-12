# CAMEL Multi-Agent Discussion System

Dynamic multi-agent AI discussion system where AI models communicate naturally with emergent behavior.

## Features

- **Dynamic Role Creation**: AI analyzes topics and creates appropriate expert roles
- **Emergent Communication**: Models address each other naturally (@mentions)
- **Same Model, Different Roles**: One LLM can play multiple expert roles
- **Consensus Detection**: AI automatically detects when discussion reaches consensus
- **Real-time Updates**: WebSocket support for live discussion viewing
- **Multi-LLM Support**: Works with GPT-4, Claude, Gemini, and more via OpenRouter

## Quick Start

### 1. Prerequisites

- Python 3.11+
- Docker & Docker Compose
- OpenRouter API key (get at https://openrouter.ai)

### 2. Setup

```bash
# Clone and navigate
cd /opt/dev/camel-discussion-engine

# Create virtual environment
python3.11 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Create .env file
cp .env.example .env
# Edit .env and add your API keys
```

### 3. Run Locally

```bash
# Activate virtual environment
source venv/bin/activate

# Start API server
python src/api/main.py

# Visit http://localhost:8007/api/docs
```

### 4. Run with Docker

```bash
# Build and start
docker-compose up --build

# Visit http://localhost:8007/api/docs
```

## Project Structure

```
/opt/dev/camel-discussion-engine/
├── src/
│   ├── api/                 # FastAPI application
│   │   ├── main.py          # Application entry point
│   │   ├── routes/          # API endpoints
│   │   ├── models/          # Pydantic models
│   │   └── websocket/       # WebSocket handlers
│   ├── camel_engine/        # CAMEL-AI integration
│   │   ├── orchestrator.py  # Discussion orchestrator
│   │   ├── role_creator.py  # Dynamic role creation
│   │   └── consensus.py     # Consensus detection
│   ├── database/            # Database models
│   └── utils/               # Utilities
├── tests/                   # Test suite
├── docs/                    # Documentation
├── data/                    # Data directory (logs, db)
├── docker-compose.yml       # Docker configuration
├── Dockerfile               # Docker image
└── requirements.txt         # Python dependencies
```

## Development Status

✅ **TASK-001**: Project Setup (Complete)
- [x] Project structure created
- [x] Git initialized
- [x] Docker configuration
- [x] Dependencies installed
- [x] FastAPI skeleton

✅ **TASK-002**: CAMEL-AI Integration (Complete)
- [x] OpenRouter client (llm_provider.py)
- [x] Role creator with topic analysis
- [x] Discussion orchestrator with AI-driven speaker selection
- [x] Consensus detector
- [x] Integration tests
- [x] Manual testing script

✅ **TASK-003**: FastAPI Bridge (Complete)
- [x] Discussion API routes (6 endpoints)
- [x] Models API routes (5 endpoints)
- [x] Roles API routes (5 endpoints)
- [x] WebSocket server with multi-client support
- [x] Database integration with async SQLAlchemy
- [x] Background task execution
- [x] API integration tests (26 test cases)
- [x] Interactive WebSocket test script

⏳ **TASK-004**: Open WebUI Plugin (Planned)
- [ ] UI components
- [ ] Real-time updates

⏳ **TASK-005**: Testing (Planned)
- [ ] Unit tests
- [ ] Integration tests
- [ ] E2E tests

⏳ **TASK-006**: Deployment (Planned)
- [ ] Production Docker
- [ ] Coolify deployment

## API Endpoints

### Core Endpoints

- `GET /` - Root endpoint
- `GET /health` - Health check
- `GET /api/docs` - API documentation

### Discussion Endpoints

- `POST /api/discussions/create` - Create new discussion
- `GET /api/discussions/{id}` - Get discussion details
- `POST /api/discussions/{id}/message` - Send user message
- `GET /api/discussions/{id}/messages` - Get message history (with pagination)
- `POST /api/discussions/{id}/stop` - Stop ongoing discussion
- `DELETE /api/discussions/{id}` - Delete discussion
- `WS /ws/discussions/{id}` - WebSocket for real-time updates

### Models Endpoints

- `GET /api/models/` - List all available models
- `GET /api/models/{id}` - Get model information
- `GET /api/models/normalize/{name}` - Normalize model name
- `GET /api/models/providers/list` - List providers
- `POST /api/models/test` - Test model with prompt

### Roles Endpoints

- `POST /api/roles/preview` - Preview roles for a topic
- `GET /api/roles/templates` - Get role templates
- `GET /api/roles/templates/{id}` - Get specific template
- `POST /api/roles/analyze-topic` - Analyze topic
- `GET /api/roles/by-domain/{domain}` - Get roles by domain

## Example Use Case

```python
# Topic: "Best treatment for chronic migraine"

# AI automatically creates roles:
- Neurologist (GPT-4)
- Pharmacologist (Claude Opus)
- Pain Management Specialist (GPT-4, different role)
- Patient Advocate (Gemini)

# Discussion flows naturally:
Neurologist: "Based on clinical evidence, I recommend..."
Pharmacologist: "@Neurologist, regarding beta-blockers, we must consider..."
Pain Management: "@Both, from a holistic perspective..."
# [Natural conversation until consensus]
```

## Technology Stack

- **Framework**: FastAPI
- **AI Engine**: CAMEL-AI v0.1.5.3
- **LLM Access**: OpenRouter
- **Database**: SQLite (async)
- **WebSocket**: python-socketio
- **Deployment**: Docker + Coolify

## Documentation

- [Project Specification](/opt/prod/services/llm-chat-ui/tasks/PROJECT_SPECIFICATION.md)
- [Architecture Diagram](/opt/prod/services/llm-chat-ui/tasks/ARCHITECTURE_DIAGRAM.md)
- [Implementation Guide](/opt/prod/services/llm-chat-ui/tasks/IMPLEMENTATION_GUIDE.md)
- [Task Breakdown](/opt/prod/services/llm-chat-ui/tasks/README.md)

## Contributing

See development guidelines in `/opt/prod/services/llm-chat-ui/tasks/IMPLEMENTATION_GUIDE.md`

## License

MIT License - See LICENSE file for details

## Contact

Project Lead: Kostas Noreika
Status: Active Development (Week 1)
