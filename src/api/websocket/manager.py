"""
WebSocket Connection Manager
Manages real-time WebSocket connections for discussion updates
"""
from fastapi import WebSocket, WebSocketDisconnect
from typing import Dict, Set, Any
from loguru import logger
import json
from datetime import datetime


class ConnectionManager:
    """
    Manages WebSocket connections for real-time discussion updates

    Features:
    - Multiple clients per discussion
    - Broadcast to all clients in a discussion
    - Personal messages to specific clients
    - Automatic cleanup of dead connections
    - Graceful disconnection handling
    """

    def __init__(self):
        # discussion_id -> Set of WebSocket connections
        self.active_connections: Dict[str, Set[WebSocket]] = {}

        # WebSocket -> discussion_id mapping (for reverse lookup)
        self.connection_mapping: Dict[WebSocket, str] = {}

    async def connect(self, websocket: WebSocket, discussion_id: str):
        """
        Accept and register WebSocket connection

        Args:
            websocket: WebSocket connection
            discussion_id: Discussion to connect to
        """
        await websocket.accept()

        # Initialize discussion set if needed
        if discussion_id not in self.active_connections:
            self.active_connections[discussion_id] = set()

        # Add connection
        self.active_connections[discussion_id].add(websocket)
        self.connection_mapping[websocket] = discussion_id

        # Send welcome message
        await self.send_personal_message(websocket, {
            "type": "connected",
            "discussion_id": discussion_id,
            "timestamp": datetime.utcnow().isoformat(),
            "message": "Connected to discussion"
        })

        logger.info(
            f"WebSocket connected: {discussion_id[:8]} "
            f"(total: {len(self.active_connections[discussion_id])} clients)"
        )

    async def disconnect(self, websocket: WebSocket, discussion_id: str = None):
        """
        Remove WebSocket connection

        Args:
            websocket: WebSocket to disconnect
            discussion_id: Discussion ID (optional, will lookup if not provided)
        """
        # Lookup discussion_id if not provided
        if discussion_id is None:
            discussion_id = self.connection_mapping.get(websocket)

        if not discussion_id:
            return

        # Remove from active connections
        if discussion_id in self.active_connections:
            self.active_connections[discussion_id].discard(websocket)

            # Clean up empty sets
            if not self.active_connections[discussion_id]:
                del self.active_connections[discussion_id]

        # Remove from mapping
        self.connection_mapping.pop(websocket, None)

        logger.info(f"WebSocket disconnected: {discussion_id[:8]}")

    async def broadcast(self, discussion_id: str, message: dict):
        """
        Broadcast message to all clients connected to discussion

        Args:
            discussion_id: Discussion to broadcast to
            message: Message dict to send
        """
        if discussion_id not in self.active_connections:
            logger.debug(f"No active connections for discussion {discussion_id[:8]}")
            return

        # Add timestamp if not present
        if "timestamp" not in message:
            message["timestamp"] = datetime.utcnow().isoformat()

        message_json = json.dumps(message)
        dead_connections = set()

        # Send to all clients
        for connection in self.active_connections[discussion_id]:
            try:
                await connection.send_text(message_json)
            except WebSocketDisconnect:
                logger.warning(f"Client disconnected during broadcast")
                dead_connections.add(connection)
            except Exception as e:
                logger.error(f"Failed to send message: {e}")
                dead_connections.add(connection)

        # Clean up dead connections
        for connection in dead_connections:
            await self.disconnect(connection, discussion_id)

        logger.debug(
            f"Broadcast to {discussion_id[:8]}: "
            f"{len(self.active_connections.get(discussion_id, set()))} clients, "
            f"{len(dead_connections)} failed"
        )

    async def send_personal_message(self, websocket: WebSocket, message: dict):
        """
        Send message to specific client

        Args:
            websocket: Target WebSocket
            message: Message dict to send
        """
        try:
            # Add timestamp if not present
            if "timestamp" not in message:
                message["timestamp"] = datetime.utcnow().isoformat()

            await websocket.send_json(message)
        except Exception as e:
            logger.error(f"Failed to send personal message: {e}")

    async def broadcast_agent_message(
        self,
        discussion_id: str,
        role_name: str,
        model: str,
        content: str,
        turn_number: int
    ):
        """
        Broadcast agent message (convenience method)

        Args:
            discussion_id: Discussion ID
            role_name: Agent role name
            model: LLM model used
            content: Message content
            turn_number: Turn number
        """
        await self.broadcast(discussion_id, {
            "type": "agent_message",
            "data": {
                "role_name": role_name,
                "model": model,
                "content": content,
                "turn_number": turn_number
            }
        })

    async def broadcast_consensus_update(
        self,
        discussion_id: str,
        reached: bool,
        confidence: float,
        summary: str,
        agreements: list,
        disagreements: list
    ):
        """
        Broadcast consensus update (convenience method)

        Args:
            discussion_id: Discussion ID
            reached: Whether consensus reached
            confidence: Confidence score
            summary: Consensus summary
            agreements: List of agreements
            disagreements: List of disagreements
        """
        await self.broadcast(discussion_id, {
            "type": "consensus_update",
            "data": {
                "reached": reached,
                "confidence": confidence,
                "summary": summary,
                "agreements": agreements,
                "disagreements": disagreements
            }
        })

    async def broadcast_discussion_complete(
        self,
        discussion_id: str,
        total_turns: int,
        consensus_reached: bool,
        final_summary: str
    ):
        """
        Broadcast discussion completion (convenience method)

        Args:
            discussion_id: Discussion ID
            total_turns: Total turns completed
            consensus_reached: Whether consensus reached
            final_summary: Final summary
        """
        await self.broadcast(discussion_id, {
            "type": "discussion_complete",
            "data": {
                "total_turns": total_turns,
                "consensus_reached": consensus_reached,
                "final_summary": final_summary,
                "status": "completed"
            }
        })

    async def broadcast_error(self, discussion_id: str, error: str):
        """
        Broadcast error message (convenience method)

        Args:
            discussion_id: Discussion ID
            error: Error message
        """
        await self.broadcast(discussion_id, {
            "type": "error",
            "error": error
        })

    async def disconnect_all(self):
        """Disconnect all clients (for shutdown)"""
        logger.info("Disconnecting all WebSocket clients...")

        for discussion_id in list(self.active_connections.keys()):
            for connection in list(self.active_connections[discussion_id]):
                try:
                    await connection.close(code=1000, reason="Server shutdown")
                except:
                    pass

        self.active_connections.clear()
        self.connection_mapping.clear()

        logger.info("All WebSocket connections closed")

    def get_connection_count(self, discussion_id: str = None) -> int:
        """
        Get number of active connections

        Args:
            discussion_id: Specific discussion (optional)

        Returns:
            Connection count
        """
        if discussion_id:
            return len(self.active_connections.get(discussion_id, set()))
        else:
            return sum(len(conns) for conns in self.active_connections.values())

    def get_active_discussions(self) -> list:
        """
        Get list of discussions with active connections

        Returns:
            List of discussion IDs
        """
        return list(self.active_connections.keys())


# Global instance
manager = ConnectionManager()
