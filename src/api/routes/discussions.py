"""
Discussion API Routes
Handles all discussion-related HTTP endpoints
"""
from fastapi import APIRouter, HTTPException, BackgroundTasks
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from loguru import logger
from datetime import datetime
import asyncio

from ...camel_engine.orchestrator import DiscussionOrchestrator
from ...database.models import Discussion, Message
from ...database.session import async_session
from ..websocket.manager import manager as ws_manager
from ...utils.config import settings
from sqlalchemy import select
from sqlalchemy.orm import selectinload


router = APIRouter()
orchestrator = DiscussionOrchestrator(
    openrouter_api_key=settings.OPENROUTER_API_KEY,
    max_turns=settings.CAMEL_MAX_TURNS,
    consensus_threshold=settings.CAMEL_CONSENSUS_THRESHOLD
)


# ============================================================================
# REQUEST/RESPONSE MODELS
# ============================================================================

class CreateDiscussionRequest(BaseModel):
    """Request to create a new discussion"""
    topic: str = Field(..., min_length=10, max_length=500, description="Discussion topic")
    num_agents: int = Field(4, ge=2, le=8, description="Number of AI agents (2-8)")
    model_preferences: Optional[List[str]] = Field(None, description="Preferred models (e.g., ['gpt-4', 'claude-3-opus'])")
    user_id: str = Field("default", description="User identifier")
    max_turns: Optional[int] = Field(None, ge=3, le=50, description="Maximum discussion turns")

    class Config:
        json_schema_extra = {
            "example": {
                "topic": "What are the best strategies for treating chronic migraine?",
                "num_agents": 4,
                "model_preferences": ["gpt-4", "claude-3-opus"],
                "user_id": "user123",
                "max_turns": 20
            }
        }


class RoleInfo(BaseModel):
    """AI role information"""
    name: str
    expertise: str
    perspective: str
    model: str


class CreateDiscussionResponse(BaseModel):
    """Response after creating discussion"""
    discussion_id: str
    topic: str
    roles: List[RoleInfo]
    status: str = "running"
    created_at: str
    websocket_url: str

    class Config:
        json_schema_extra = {
            "example": {
                "discussion_id": "disc_abc123",
                "topic": "Best strategies for treating chronic migraine",
                "roles": [
                    {
                        "name": "Neurologist",
                        "expertise": "Brain disorders and neurology",
                        "perspective": "Clinical evidence-based treatment",
                        "model": "gpt-4"
                    }
                ],
                "status": "running",
                "created_at": "2025-10-12T10:00:00Z",
                "websocket_url": "ws://localhost:8007/ws/discussions/disc_abc123"
            }
        }


class SendMessageRequest(BaseModel):
    """Request to send user message to discussion"""
    content: str = Field(..., min_length=1, max_length=2000, description="Message content")
    user_id: str = Field("default", description="User identifier")


class DiscussionStatus(BaseModel):
    """Discussion status response"""
    discussion_id: str
    topic: str
    status: str
    current_turn: int
    max_turns: int
    consensus_reached: bool
    consensus_confidence: Optional[float]
    message_count: int
    created_at: str
    updated_at: str


class MessageResponse(BaseModel):
    """Single message response"""
    id: int
    discussion_id: str
    role_name: str
    model: str
    content: str
    is_user: bool
    created_at: str
    metadata: Optional[Dict[str, Any]]


# ============================================================================
# API ENDPOINTS
# ============================================================================

@router.post("/create", response_model=CreateDiscussionResponse, status_code=201)
async def create_discussion(
    request: CreateDiscussionRequest,
    background_tasks: BackgroundTasks
):
    """
    Create a new AI discussion session

    This endpoint:
    1. Creates AI roles dynamically based on the topic
    2. Initializes discussion in memory and database
    3. Starts the discussion in background
    4. Returns WebSocket URL for real-time updates

    The discussion will run automatically until consensus is reached or max_turns exceeded.
    """
    try:
        logger.info(f"Creating discussion: {request.topic}")

        # Create discussion through CAMEL orchestrator
        discussion_id = await orchestrator.create_discussion(
            topic=request.topic,
            user_id=request.user_id,
            num_agents=request.num_agents,
            model_preferences=request.model_preferences
        )

        # Get created discussion details
        discussion = orchestrator.get_discussion(discussion_id)

        # Save to database
        await save_discussion_to_db(discussion, request.user_id)

        # Prepare response
        roles_info = [
            RoleInfo(
                name=role.name,
                expertise=role.expertise,
                perspective=role.perspective,
                model=role.model
            )
            for role in discussion.roles
        ]

        # Start discussion in background
        background_tasks.add_task(
            run_discussion_background,
            discussion_id,
            request.max_turns
        )

        logger.info(f"Discussion {discussion_id} created successfully")

        return CreateDiscussionResponse(
            discussion_id=discussion_id,
            topic=request.topic,
            roles=roles_info,
            status="running",
            created_at=datetime.utcnow().isoformat(),
            websocket_url=f"ws://localhost:8007/ws/discussions/{discussion_id}"
        )

    except Exception as e:
        logger.error(f"Failed to create discussion: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to create discussion: {str(e)}")


@router.post("/{discussion_id}/message", status_code=200)
async def send_message(
    discussion_id: str,
    request: SendMessageRequest
):
    """
    Send a user message to an ongoing discussion

    This allows users to:
    - Guide the discussion
    - Ask questions
    - Provide additional context
    - Interrupt with corrections

    The message will be broadcast to all WebSocket clients.
    """
    try:
        logger.info(f"User message to {discussion_id}: {request.content[:50]}...")

        # Verify discussion exists
        discussion = orchestrator.get_discussion(discussion_id)
        if not discussion:
            raise HTTPException(status_code=404, detail="Discussion not found")

        # Save message to database
        await save_message_to_db(
            discussion_id=discussion_id,
            role_name="User",
            model="human",
            content=request.content,
            is_user=True,
            metadata={"user_id": request.user_id}
        )

        # Broadcast to WebSocket clients
        await ws_manager.broadcast(discussion_id, {
            "type": "user_message",
            "data": {
                "role_name": "User",
                "content": request.content,
                "user_id": request.user_id,
                "timestamp": datetime.utcnow().isoformat()
            }
        })

        logger.info(f"User message sent to {discussion_id}")
        return {"status": "sent", "discussion_id": discussion_id}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to send message: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{discussion_id}", response_model=DiscussionStatus)
async def get_discussion(discussion_id: str):
    """
    Get discussion details and current status

    Returns:
    - Current status (running, completed, stopped, failed)
    - Progress (current turn, max turns)
    - Consensus information
    - Message count
    """
    try:
        # Check in-memory orchestrator first
        discussion = orchestrator.get_discussion(discussion_id)
        if not discussion:
            # Try database
            db_discussion = await get_discussion_from_db(discussion_id)
            if not db_discussion:
                raise HTTPException(status_code=404, detail="Discussion not found")

            return DiscussionStatus(
                discussion_id=db_discussion.id,
                topic=db_discussion.topic,
                status=db_discussion.status,
                current_turn=0,
                max_turns=20,
                consensus_reached=bool(db_discussion.consensus_reached),
                consensus_confidence=None,
                message_count=len(db_discussion.messages) if db_discussion.messages else 0,
                created_at=db_discussion.created_at.isoformat(),
                updated_at=db_discussion.updated_at.isoformat()
            )

        return DiscussionStatus(
            discussion_id=discussion.id,
            topic=discussion.topic,
            status=discussion.status,
            current_turn=discussion.current_turn,
            max_turns=20,  # Default max_turns since it's not stored in Discussion model
            consensus_reached=discussion.consensus_reached,
            consensus_confidence=None,  # Not available in in-memory Discussion model
            message_count=len(discussion.messages),
            created_at=discussion.created_at.isoformat() if discussion.created_at else datetime.utcnow().isoformat(),
            updated_at=discussion.updated_at.isoformat() if discussion.updated_at else datetime.utcnow().isoformat()
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get discussion {discussion_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{discussion_id}/messages", response_model=Dict[str, Any])
async def get_messages(
    discussion_id: str,
    limit: int = 100,
    offset: int = 0
):
    """
    Get discussion messages with pagination

    Query Parameters:
    - limit: Maximum number of messages to return (default: 100)
    - offset: Number of messages to skip (default: 0)

    Returns messages in chronological order (oldest first).
    """
    try:
        logger.info(f"Fetching messages for {discussion_id} (limit={limit}, offset={offset})")

        messages = await get_messages_from_db(
            discussion_id,
            limit=limit,
            offset=offset
        )

        if messages is None:
            raise HTTPException(status_code=404, detail="Discussion not found")

        message_responses = [
            MessageResponse(
                id=msg.id,
                discussion_id=msg.discussion_id,
                role_name=msg.role_name,
                model=msg.model,
                content=msg.content,
                is_user=bool(msg.is_user),
                created_at=msg.created_at.isoformat(),
                metadata=msg.extra_data  # Renamed from metadata to extra_data in DB model
            )
            for msg in messages
        ]

        return {
            "discussion_id": discussion_id,
            "messages": message_responses,
            "count": len(message_responses),
            "offset": offset,
            "limit": limit
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get messages: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{discussion_id}/stop", status_code=200)
async def stop_discussion(discussion_id: str):
    """
    Stop an ongoing discussion

    This will:
    1. Mark discussion as stopped in orchestrator
    2. Update database status
    3. Notify WebSocket clients

    The discussion can be resumed later if needed.
    """
    try:
        logger.info(f"Stopping discussion {discussion_id}")

        # Stop in orchestrator
        success = await orchestrator.stop_discussion(discussion_id)
        if not success:
            raise HTTPException(status_code=404, detail="Discussion not found or already stopped")

        # Update database
        await update_discussion_status(discussion_id, "stopped")

        # Notify WebSocket clients
        await ws_manager.broadcast(discussion_id, {
            "type": "discussion_stopped",
            "data": {
                "discussion_id": discussion_id,
                "timestamp": datetime.utcnow().isoformat(),
                "message": "Discussion stopped by user"
            }
        })

        logger.info(f"Discussion {discussion_id} stopped successfully")
        return {"status": "stopped", "discussion_id": discussion_id}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to stop discussion: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{discussion_id}", status_code=200)
async def delete_discussion(discussion_id: str):
    """
    Delete a discussion and all its messages

    WARNING: This operation cannot be undone!
    """
    try:
        logger.warning(f"Deleting discussion {discussion_id}")

        # Stop if running
        await orchestrator.stop_discussion(discussion_id)

        # Delete from database
        deleted = await delete_discussion_from_db(discussion_id)
        if not deleted:
            raise HTTPException(status_code=404, detail="Discussion not found")

        # Notify WebSocket clients before disconnecting
        await ws_manager.broadcast(discussion_id, {
            "type": "discussion_deleted",
            "data": {
                "discussion_id": discussion_id,
                "timestamp": datetime.utcnow().isoformat()
            }
        })

        logger.info(f"Discussion {discussion_id} deleted")
        return {"status": "deleted", "discussion_id": discussion_id}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete discussion: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# BACKGROUND TASKS
# ============================================================================

async def run_discussion_background(discussion_id: str, max_turns: Optional[int] = None):
    """
    Run discussion in background and stream updates via WebSocket

    This function:
    1. Runs the discussion orchestrator
    2. Saves each message to database
    3. Broadcasts updates to WebSocket clients
    4. Handles errors gracefully
    """
    try:
        logger.info(f"Starting background discussion: {discussion_id}")

        # Run discussion and get result
        result = await orchestrator.run_discussion(
            discussion_id=discussion_id,
            max_turns=max_turns
        )

        # Broadcast each message as it's generated
        for message in result.messages:
            # Save to database
            await save_message_to_db(
                discussion_id=discussion_id,
                role_name=message.role_name,
                model=message.model,
                content=message.content,
                is_user=False,
                metadata={
                    "turn": message.turn_number,
                    "timestamp": message.created_at.isoformat() if message.created_at else None
                }
            )

            # Broadcast via WebSocket
            await ws_manager.broadcast_agent_message(
                discussion_id=discussion_id,
                role_name=message.role_name,
                model=message.model,
                content=message.content,
                turn_number=message.turn_number
            )

            # Small delay to avoid overwhelming clients
            await asyncio.sleep(0.1)

        # Update database with final status
        await update_discussion_status(
            discussion_id=discussion_id,
            status="completed" if result.consensus_reached else "no_consensus",
            consensus_reached=result.consensus_reached,
            consensus_summary=result.final_summary
        )

        # Broadcast completion
        await ws_manager.broadcast_discussion_complete(
            discussion_id=discussion_id,
            total_turns=result.total_turns,
            consensus_reached=result.consensus_reached,
            final_summary=result.final_summary
        )

        logger.info(f"Discussion {discussion_id} completed: consensus={result.consensus_reached}")

    except Exception as e:
        logger.error(f"Discussion {discussion_id} failed: {e}", exc_info=True)

        # Update database
        await update_discussion_status(discussion_id, "failed")

        # Notify clients
        await ws_manager.broadcast_error(discussion_id, str(e))


# ============================================================================
# DATABASE HELPER FUNCTIONS
# ============================================================================

async def save_discussion_to_db(discussion, user_id: str):
    """Save discussion to database"""
    try:
        async with async_session() as session:
            db_discussion = Discussion(
                id=discussion.id,
                topic=discussion.topic,
                user_id=user_id,
                status="running",
                roles=[role.dict() for role in discussion.roles],
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            session.add(db_discussion)
            await session.commit()
            logger.debug(f"Saved discussion {discussion.id} to database")
    except Exception as e:
        logger.error(f"Failed to save discussion to database: {e}", exc_info=True)
        raise


async def save_message_to_db(
    discussion_id: str,
    role_name: str,
    model: str,
    content: str,
    is_user: bool = False,
    metadata: Optional[Dict[str, Any]] = None
):
    """Save message to database"""
    try:
        async with async_session() as session:
            message = Message(
                discussion_id=discussion_id,
                role_name=role_name,
                model=model,
                content=content,
                is_user=1 if is_user else 0,
                created_at=datetime.utcnow(),
                extra_data=metadata  # Renamed from metadata to extra_data in DB model
            )
            session.add(message)
            await session.commit()
            logger.debug(f"Saved message from {role_name} to database")
    except Exception as e:
        logger.error(f"Failed to save message to database: {e}", exc_info=True)


async def get_discussion_from_db(discussion_id: str) -> Optional[Discussion]:
    """Get discussion from database"""
    try:
        async with async_session() as session:
            result = await session.execute(
                select(Discussion)
                .options(selectinload(Discussion.messages))
                .where(Discussion.id == discussion_id)
            )
            return result.scalar_one_or_none()
    except Exception as e:
        logger.error(f"Failed to get discussion from database: {e}", exc_info=True)
        return None


async def get_messages_from_db(
    discussion_id: str,
    limit: int = 100,
    offset: int = 0
) -> Optional[List[Message]]:
    """Get messages from database with pagination"""
    try:
        async with async_session() as session:
            result = await session.execute(
                select(Message)
                .where(Message.discussion_id == discussion_id)
                .order_by(Message.created_at.asc())
                .limit(limit)
                .offset(offset)
            )
            return result.scalars().all()
    except Exception as e:
        logger.error(f"Failed to get messages from database: {e}", exc_info=True)
        return None


async def update_discussion_status(
    discussion_id: str,
    status: str,
    consensus_reached: bool = False,
    consensus_summary: Optional[str] = None
):
    """Update discussion status in database"""
    try:
        async with async_session() as session:
            result = await session.execute(
                select(Discussion).where(Discussion.id == discussion_id)
            )
            discussion = result.scalar_one_or_none()

            if discussion:
                discussion.status = status
                discussion.updated_at = datetime.utcnow()
                if consensus_reached:
                    discussion.consensus_reached = 1
                if consensus_summary:
                    discussion.consensus_summary = consensus_summary

                await session.commit()
                logger.debug(f"Updated discussion {discussion_id} status to {status}")
    except Exception as e:
        logger.error(f"Failed to update discussion status: {e}", exc_info=True)


async def delete_discussion_from_db(discussion_id: str) -> bool:
    """Delete discussion and all messages from database"""
    try:
        async with async_session() as session:
            # Delete messages first (foreign key constraint)
            await session.execute(
                Message.__table__.delete().where(Message.discussion_id == discussion_id)
            )

            # Delete discussion
            result = await session.execute(
                Discussion.__table__.delete().where(Discussion.id == discussion_id)
            )

            await session.commit()
            return result.rowcount > 0
    except Exception as e:
        logger.error(f"Failed to delete discussion from database: {e}", exc_info=True)
        return False
