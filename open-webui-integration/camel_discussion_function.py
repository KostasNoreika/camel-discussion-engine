"""
CAMEL Multi-Agent Discussion Function for Open WebUI
=====================================================

This function integrates the CAMEL Discussion Engine with Open WebUI,
allowing users to create and participate in multi-agent AI discussions
directly from the chat interface.

Installation:
1. Go to Open WebUI Admin Panel
2. Navigate to Functions
3. Click "Add Function"
4. Paste this code
5. Configure API endpoint in Valves
6. Enable the function

Usage:
- Type: "Start discussion about [topic]"
- The function will create a multi-agent discussion
- Agents will discuss the topic with emergent communication
- You can guide the discussion by sending messages
- Consensus detection happens automatically
"""

from pydantic import BaseModel, Field
from typing import Optional, Dict, List, Any, Callable, Awaitable
import httpx
import json
import asyncio
from datetime import datetime


class Valves(BaseModel):
    """
    Configuration valves for CAMEL Discussion Function
    """
    API_ENDPOINT: str = Field(
        default="http://192.168.110.199:8007",
        description="CAMEL Discussion API endpoint (use local network IP)"
    )
    WEBSOCKET_ENDPOINT: str = Field(
        default="ws://192.168.110.199:8007",
        description="WebSocket endpoint for real-time updates"
    )
    DEFAULT_NUM_AGENTS: int = Field(
        default=3,
        ge=2,
        le=6,
        description="Default number of AI agents (2-6)"
    )
    DEFAULT_MAX_TURNS: int = Field(
        default=15,
        ge=3,
        le=30,
        description="Maximum discussion turns (3-30)"
    )
    SHOW_THINKING: bool = Field(
        default=True,
        description="Show agent thinking process"
    )
    AUTO_SUMMARIZE: bool = Field(
        default=True,
        description="Auto-summarize when consensus reached"
    )


class Tools:
    """
    Tools for CAMEL Discussion integration
    """

    class Valves(Valves):
        pass

    def __init__(self):
        self.valves = self.Valves()
        self.active_discussions: Dict[str, Dict[str, Any]] = {}

    async def create_discussion(
        self,
        topic: str,
        user_id: str,
        num_agents: Optional[int] = None,
        max_turns: Optional[int] = None,
        __event_emitter__: Optional[Callable[[Any], Awaitable[None]]] = None
    ) -> str:
        """
        Create a new multi-agent discussion

        Args:
            topic: Discussion topic
            user_id: User identifier
            num_agents: Number of AI agents (optional)
            max_turns: Maximum discussion turns (optional)
            __event_emitter__: Event emitter for status updates

        Returns:
            Discussion ID
        """
        if __event_emitter__:
            await __event_emitter__({
                "type": "status",
                "data": {
                    "description": f"🎭 Creating discussion with {num_agents or self.valves.DEFAULT_NUM_AGENTS} AI agents...",
                    "done": False
                }
            })

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{self.valves.API_ENDPOINT}/api/discussions/create",
                    json={
                        "topic": topic,
                        "num_agents": num_agents or self.valves.DEFAULT_NUM_AGENTS,
                        "user_id": user_id,
                        "max_turns": max_turns or self.valves.DEFAULT_MAX_TURNS,
                        "model_preferences": ["gpt-4", "claude-3-opus", "gemini-pro"]
                    }
                )

                if response.status_code != 201:
                    error_msg = f"Failed to create discussion: {response.text}"
                    if __event_emitter__:
                        await __event_emitter__({
                            "type": "status",
                            "data": {
                                "description": f"❌ {error_msg}",
                                "done": True
                            }
                        })
                    return error_msg

                data = response.json()
                discussion_id = data["discussion_id"]

                # Store discussion info
                self.active_discussions[discussion_id] = {
                    "topic": topic,
                    "roles": data["roles"],
                    "created_at": datetime.utcnow().isoformat(),
                    "user_id": user_id
                }

                # Emit roles info
                if __event_emitter__:
                    roles_text = "\n".join([
                        f"  • **{role['name']}** ({role['model']}): {role['expertise']}"
                        for role in data["roles"]
                    ])

                    await __event_emitter__({
                        "type": "message",
                        "data": {
                            "content": f"### 🎭 Discussion Created!\n\n"
                                      f"**Topic**: {topic}\n\n"
                                      f"**Agents**:\n{roles_text}\n\n"
                                      f"**Discussion ID**: `{discussion_id}`\n\n"
                                      f"The AI agents are now discussing. Messages will appear below in real-time."
                        }
                    })

                    await __event_emitter__({
                        "type": "status",
                        "data": {
                            "description": "✅ Discussion started successfully",
                            "done": True
                        }
                    })

                return discussion_id

        except httpx.TimeoutException:
            error_msg = "⏱️ Request timeout - API may be slow or unavailable"
            if __event_emitter__:
                await __event_emitter__({
                    "type": "status",
                    "data": {"description": error_msg, "done": True}
                })
            return error_msg
        except Exception as e:
            error_msg = f"❌ Error creating discussion: {str(e)}"
            if __event_emitter__:
                await __event_emitter__({
                    "type": "status",
                    "data": {"description": error_msg, "done": True}
                })
            return error_msg

    async def send_message_to_discussion(
        self,
        discussion_id: str,
        message: str,
        user_id: str,
        __event_emitter__: Optional[Callable[[Any], Awaitable[None]]] = None
    ) -> str:
        """
        Send user message to ongoing discussion

        Args:
            discussion_id: Discussion ID
            message: User message content
            user_id: User identifier
            __event_emitter__: Event emitter

        Returns:
            Status message
        """
        if __event_emitter__:
            await __event_emitter__({
                "type": "status",
                "data": {
                    "description": "💬 Sending your message to the discussion...",
                    "done": False
                }
            })

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(
                    f"{self.valves.API_ENDPOINT}/api/discussions/{discussion_id}/message",
                    json={
                        "content": message,
                        "user_id": user_id
                    }
                )

                if response.status_code == 200:
                    if __event_emitter__:
                        await __event_emitter__({
                            "type": "message",
                            "data": {
                                "content": f"### 👤 Your message\n\n{message}\n\n"
                                          f"*The AI agents are considering your input...*"
                            }
                        })

                        await __event_emitter__({
                            "type": "status",
                            "data": {
                                "description": "✅ Message sent successfully",
                                "done": True
                            }
                        })

                    return "Message sent successfully"
                else:
                    error_msg = f"Failed to send message: {response.text}"
                    if __event_emitter__:
                        await __event_emitter__({
                            "type": "status",
                            "data": {"description": f"❌ {error_msg}", "done": True}
                        })
                    return error_msg

        except Exception as e:
            error_msg = f"Error sending message: {str(e)}"
            if __event_emitter__:
                await __event_emitter__({
                    "type": "status",
                    "data": {"description": f"❌ {error_msg}", "done": True}
                })
            return error_msg

    async def get_discussion_status(
        self,
        discussion_id: str,
        __event_emitter__: Optional[Callable[[Any], Awaitable[None]]] = None
    ) -> Dict[str, Any]:
        """
        Get discussion status and recent messages

        Args:
            discussion_id: Discussion ID
            __event_emitter__: Event emitter

        Returns:
            Discussion status dict
        """
        if __event_emitter__:
            await __event_emitter__({
                "type": "status",
                "data": {
                    "description": "📊 Fetching discussion status...",
                    "done": False
                }
            })

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                # Get discussion status
                status_response = await client.get(
                    f"{self.valves.API_ENDPOINT}/api/discussions/{discussion_id}"
                )

                # Get recent messages
                messages_response = await client.get(
                    f"{self.valves.API_ENDPOINT}/api/discussions/{discussion_id}/messages",
                    params={"limit": 10, "offset": 0}
                )

                if status_response.status_code == 200 and messages_response.status_code == 200:
                    status_data = status_response.json()
                    messages_data = messages_response.json()

                    # Format status message
                    status_icon = {
                        "running": "🔄",
                        "completed": "✅",
                        "stopped": "⏸️",
                        "failed": "❌"
                    }.get(status_data["status"], "❓")

                    consensus_text = "✅ Yes" if status_data["consensus_reached"] else "⏳ In progress"

                    status_message = (
                        f"### {status_icon} Discussion Status\n\n"
                        f"**Topic**: {status_data['topic']}\n"
                        f"**Status**: {status_data['status']}\n"
                        f"**Progress**: Turn {status_data['current_turn']} / {status_data['max_turns']}\n"
                        f"**Consensus**: {consensus_text}\n"
                        f"**Messages**: {status_data['message_count']}\n\n"
                    )

                    # Add recent messages
                    if messages_data["messages"]:
                        status_message += "**Recent Messages**:\n\n"
                        for msg in messages_data["messages"][-5:]:  # Last 5 messages
                            role_icon = "👤" if msg["is_user"] else "🤖"
                            status_message += f"{role_icon} **{msg['role_name']}**: {msg['content'][:100]}...\n\n"

                    if __event_emitter__:
                        await __event_emitter__({
                            "type": "message",
                            "data": {"content": status_message}
                        })

                        await __event_emitter__({
                            "type": "status",
                            "data": {
                                "description": "✅ Status retrieved successfully",
                                "done": True
                            }
                        })

                    return status_data
                else:
                    error_msg = "Failed to fetch discussion status"
                    if __event_emitter__:
                        await __event_emitter__({
                            "type": "status",
                            "data": {"description": f"❌ {error_msg}", "done": True}
                        })
                    return {"error": error_msg}

        except Exception as e:
            error_msg = f"Error fetching status: {str(e)}"
            if __event_emitter__:
                await __event_emitter__({
                    "type": "status",
                    "data": {"description": f"❌ {error_msg}", "done": True}
                })
            return {"error": error_msg}

    async def stop_discussion(
        self,
        discussion_id: str,
        __event_emitter__: Optional[Callable[[Any], Awaitable[None]]] = None
    ) -> str:
        """
        Stop an ongoing discussion

        Args:
            discussion_id: Discussion ID
            __event_emitter__: Event emitter

        Returns:
            Status message
        """
        if __event_emitter__:
            await __event_emitter__({
                "type": "status",
                "data": {
                    "description": "⏸️ Stopping discussion...",
                    "done": False
                }
            })

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(
                    f"{self.valves.API_ENDPOINT}/api/discussions/{discussion_id}/stop"
                )

                if response.status_code == 200:
                    if __event_emitter__:
                        await __event_emitter__({
                            "type": "message",
                            "data": {
                                "content": f"### ⏸️ Discussion Stopped\n\n"
                                          f"The discussion has been stopped. You can view the messages above."
                            }
                        })

                        await __event_emitter__({
                            "type": "status",
                            "data": {
                                "description": "✅ Discussion stopped successfully",
                                "done": True
                            }
                        })

                    # Remove from active discussions
                    self.active_discussions.pop(discussion_id, None)

                    return "Discussion stopped successfully"
                else:
                    error_msg = f"Failed to stop discussion: {response.text}"
                    if __event_emitter__:
                        await __event_emitter__({
                            "type": "status",
                            "data": {"description": f"❌ {error_msg}", "done": True}
                        })
                    return error_msg

        except Exception as e:
            error_msg = f"Error stopping discussion: {str(e)}"
            if __event_emitter__:
                await __event_emitter__({
                    "type": "status",
                    "data": {"description": f"❌ {error_msg}", "done": True}
                })
            return error_msg

    async def list_models(
        self,
        __event_emitter__: Optional[Callable[[Any], Awaitable[None]]] = None
    ) -> str:
        """
        List available LLM models

        Args:
            __event_emitter__: Event emitter

        Returns:
            Formatted model list
        """
        if __event_emitter__:
            await __event_emitter__({
                "type": "status",
                "data": {
                    "description": "📋 Fetching available models...",
                    "done": False
                }
            })

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(
                    f"{self.valves.API_ENDPOINT}/api/models/"
                )

                if response.status_code == 200:
                    data = response.json()
                    models_by_provider = {}

                    for model in data["models"]:
                        provider = model["provider"]
                        if provider not in models_by_provider:
                            models_by_provider[provider] = []
                        models_by_provider[provider].append(model)

                    # Format output
                    output = "### 🤖 Available LLM Models\n\n"

                    for provider, models in models_by_provider.items():
                        output += f"**{provider}**:\n"
                        for model in models:
                            output += f"  • **{model['name']}** - {model['context_length']:,} tokens\n"
                        output += "\n"

                    if __event_emitter__:
                        await __event_emitter__({
                            "type": "message",
                            "data": {"content": output}
                        })

                        await __event_emitter__({
                            "type": "status",
                            "data": {
                                "description": "✅ Models retrieved successfully",
                                "done": True
                            }
                        })

                    return output
                else:
                    error_msg = "Failed to fetch models"
                    if __event_emitter__:
                        await __event_emitter__({
                            "type": "status",
                            "data": {"description": f"❌ {error_msg}", "done": True}
                        })
                    return error_msg

        except Exception as e:
            error_msg = f"Error fetching models: {str(e)}"
            if __event_emitter__:
                await __event_emitter__({
                    "type": "status",
                    "data": {"description": f"❌ {error_msg}", "done": True}
                })
            return error_msg


# This is required for Open WebUI to recognize this as a Function
class Action:
    """
    Main action handler for Open WebUI integration
    """

    def __init__(self):
        self.tools = Tools()

    async def action(
        self,
        body: dict,
        __user__: dict = {},
        __event_emitter__: Optional[Callable[[Any], Awaitable[None]]] = None
    ) -> str:
        """
        Main action handler called by Open WebUI

        Supports natural language commands:
        - "start discussion about [topic]"
        - "send message: [text]"
        - "show status"
        - "stop discussion"
        - "list models"
        """
        user_message = body.get("messages", [{}])[-1].get("content", "").lower()
        user_id = __user__.get("id", "anonymous")

        # Parse commands
        if "start discussion" in user_message or "create discussion" in user_message:
            # Extract topic
            topic = user_message.split("about", 1)[-1].strip()
            if not topic or len(topic) < 10:
                return "Please provide a discussion topic. Example: 'Start discussion about climate change solutions'"

            discussion_id = await self.tools.create_discussion(
                topic=topic,
                user_id=user_id,
                __event_emitter__=__event_emitter__
            )

            return f"Discussion created: {discussion_id}"

        elif "send message" in user_message:
            # Requires active discussion
            if not self.tools.active_discussions:
                return "No active discussions. Start one first with: 'start discussion about [topic]'"

            discussion_id = list(self.tools.active_discussions.keys())[-1]
            message_content = user_message.split(":", 1)[-1].strip()

            return await self.tools.send_message_to_discussion(
                discussion_id=discussion_id,
                message=message_content,
                user_id=user_id,
                __event_emitter__=__event_emitter__
            )

        elif "status" in user_message or "show discussion" in user_message:
            if not self.tools.active_discussions:
                return "No active discussions."

            discussion_id = list(self.tools.active_discussions.keys())[-1]
            await self.tools.get_discussion_status(
                discussion_id=discussion_id,
                __event_emitter__=__event_emitter__
            )

            return "Status displayed above"

        elif "stop" in user_message:
            if not self.tools.active_discussions:
                return "No active discussions to stop."

            discussion_id = list(self.tools.active_discussions.keys())[-1]
            return await self.tools.stop_discussion(
                discussion_id=discussion_id,
                __event_emitter__=__event_emitter__
            )

        elif "list models" in user_message or "show models" in user_message:
            return await self.tools.list_models(__event_emitter__=__event_emitter__)

        else:
            return (
                "### 🎭 CAMEL Multi-Agent Discussion\n\n"
                "**Available Commands**:\n"
                "• `start discussion about [topic]` - Create new discussion\n"
                "• `send message: [text]` - Send message to active discussion\n"
                "• `show status` - View discussion status\n"
                "• `stop discussion` - Stop active discussion\n"
                "• `list models` - Show available LLM models\n\n"
                "**Example**: Start discussion about sustainable energy solutions"
            )
