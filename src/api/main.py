"""
CAMEL Discussion API - Main Application
"""
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from loguru import logger
import sys

from .routes import discussions, models, roles
from .websocket.manager import manager as ws_manager
from ..database.session import init_db
from ..utils.config import settings

# Configure logging
logger.remove()
logger.add(
    sys.stdout,
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
    level=settings.LOG_LEVEL
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager for startup and shutdown events
    Replaces deprecated @app.on_event decorators
    """
    # Startup
    logger.info("🚀 Starting CAMEL Discussion API")
    logger.info(f"📚 API Documentation: http://localhost:{settings.API_PORT}/api/docs")
    logger.info(f"🔌 WebSocket endpoint: ws://localhost:{settings.API_PORT}/ws/discussions/{{id}}")

    # Initialize database
    try:
        await init_db()
        logger.info("✅ Database initialized")
    except Exception as e:
        logger.error(f"❌ Failed to initialize database: {e}")
        raise

    yield

    # Shutdown
    logger.info("👋 Shutting down CAMEL Discussion API")

    # Disconnect all WebSocket clients gracefully
    try:
        await ws_manager.disconnect_all()
        logger.info("✅ All WebSocket connections closed")
    except Exception as e:
        logger.error(f"Error closing WebSocket connections: {e}")


app = FastAPI(
    title="CAMEL Discussion API",
    description="Dynamic multi-agent AI discussion system with emergent communication",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
    lifespan=lifespan
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routers
app.include_router(
    discussions.router,
    prefix="/api/discussions",
    tags=["discussions"]
)
app.include_router(
    models.router,
    prefix="/api/models",
    tags=["models"]
)
app.include_router(
    roles.router,
    prefix="/api/roles",
    tags=["roles"]
)


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "CAMEL Discussion API",
        "version": "0.1.0",
        "status": "running",
        "docs": "/api/docs"
    }


@app.get("/health")
async def health_check():
    """Health check endpoint for monitoring"""
    return {
        "status": "healthy",
        "service": "camel-discussion-api",
        "version": "1.0.0",
        "active_discussions": len(ws_manager.get_active_discussions()),
        "total_connections": ws_manager.get_connection_count()
    }


@app.websocket("/ws/discussions/{discussion_id}")
async def websocket_endpoint(websocket: WebSocket, discussion_id: str):
    """
    WebSocket endpoint for real-time discussion updates

    Connect to this endpoint to receive live updates:
    - Agent messages as they're generated
    - Consensus updates
    - Discussion completion
    - Error notifications

    Example:
        ws://localhost:8007/ws/discussions/disc_abc123
    """
    await ws_manager.connect(websocket, discussion_id)

    try:
        # Keep connection alive and handle client messages
        while True:
            data = await websocket.receive_text()

            # Client can send ping messages to keep connection alive
            if data == "ping":
                await websocket.send_json({"type": "pong"})
            else:
                # Echo or log other messages
                logger.debug(f"Received WebSocket message: {data}")

    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected: {discussion_id}")
    except Exception as e:
        logger.error(f"WebSocket error: {e}", exc_info=True)
    finally:
        await ws_manager.disconnect(websocket, discussion_id)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "src.api.main:app",
        host=settings.API_HOST,
        port=settings.API_PORT,
        reload=settings.DEBUG,
        log_level=settings.LOG_LEVEL.lower()
    )
