#!/usr/bin/env python3
"""
WebSocket Test Script
Tests real-time WebSocket communication with the discussion API
"""
import asyncio
import websockets
import json
import sys
from datetime import datetime
import requests
from rich.console import Console
from rich.table import Table
from rich.live import Live
from rich.panel import Panel
from rich.text import Text

console = Console()

API_URL = "http://localhost:8007"
WS_URL = "ws://localhost:8007"


class WebSocketTester:
    """WebSocket test client"""

    def __init__(self):
        self.discussion_id = None
        self.websocket = None
        self.messages = []
        self.running = False

    async def create_discussion(self, topic: str, num_agents: int = 3):
        """Create a discussion via REST API"""
        console.print("\n[bold blue]Creating discussion...[/bold blue]")

        try:
            response = requests.post(
                f"{API_URL}/api/discussions/create",
                json={
                    "topic": topic,
                    "num_agents": num_agents,
                    "model_preferences": ["gpt-4", "claude-3-opus"],
                    "user_id": "websocket_test_user",
                    "max_turns": 10
                },
                timeout=30
            )

            if response.status_code == 201:
                data = response.json()
                self.discussion_id = data["discussion_id"]

                console.print(f"[green]✓ Discussion created: {self.discussion_id}[/green]")
                console.print(f"[cyan]Topic: {data['topic']}[/cyan]")
                console.print(f"[cyan]Roles: {len(data['roles'])}[/cyan]")

                # Display roles
                table = Table(title="AI Agents")
                table.add_column("Role", style="cyan")
                table.add_column("Expertise", style="green")
                table.add_column("Model", style="yellow")

                for role in data["roles"]:
                    table.add_row(role["name"], role["expertise"], role["model"])

                console.print(table)

                return True
            else:
                console.print(f"[red]✗ Failed to create discussion: {response.status_code}[/red]")
                console.print(response.text)
                return False

        except Exception as e:
            console.print(f"[red]✗ Error creating discussion: {e}[/red]")
            return False

    async def connect_websocket(self):
        """Connect to WebSocket endpoint"""
        console.print(f"\n[bold blue]Connecting to WebSocket...[/bold blue]")

        try:
            ws_url = f"{WS_URL}/ws/discussions/{self.discussion_id}"
            console.print(f"[dim]URL: {ws_url}[/dim]")

            self.websocket = await websockets.connect(ws_url)
            console.print("[green]✓ WebSocket connected[/green]")
            return True

        except Exception as e:
            console.print(f"[red]✗ WebSocket connection failed: {e}[/red]")
            return False

    async def receive_messages(self):
        """Receive and display WebSocket messages"""
        console.print("\n[bold blue]Listening for messages...[/bold blue]")
        console.print("[dim]Press Ctrl+C to stop[/dim]\n")

        self.running = True
        message_count = 0

        try:
            async for message in self.websocket:
                if not self.running:
                    break

                data = json.loads(message)
                message_count += 1

                # Format timestamp
                timestamp = data.get("timestamp", datetime.utcnow().isoformat())
                time_str = datetime.fromisoformat(timestamp.replace('Z', '+00:00')).strftime("%H:%M:%S")

                # Display based on message type
                msg_type = data.get("type", "unknown")

                if msg_type == "connected":
                    console.print(Panel(
                        f"[green]Connected to discussion {data['discussion_id'][:8]}...[/green]",
                        title="Connected",
                        border_style="green"
                    ))

                elif msg_type == "agent_message":
                    agent_data = data.get("data", {})
                    role = agent_data.get("role_name", "Unknown")
                    model = agent_data.get("model", "Unknown")
                    content = agent_data.get("content", "")
                    turn = agent_data.get("turn_number", "?")

                    console.print(Panel(
                        f"[bold cyan]{role}[/bold cyan] [dim]({model})[/dim]\n\n{content}",
                        title=f"Turn {turn} • {time_str}",
                        border_style="cyan"
                    ))

                elif msg_type == "user_message":
                    user_data = data.get("data", {})
                    content = user_data.get("content", "")

                    console.print(Panel(
                        f"[bold yellow]User:[/bold yellow]\n\n{content}",
                        title=f"User Message • {time_str}",
                        border_style="yellow"
                    ))

                elif msg_type == "consensus_update":
                    consensus_data = data.get("data", {})
                    reached = consensus_data.get("reached", False)
                    confidence = consensus_data.get("confidence", 0)
                    summary = consensus_data.get("summary", "")

                    status = "✓ REACHED" if reached else "In Progress"
                    color = "green" if reached else "yellow"

                    console.print(Panel(
                        f"[bold]Status:[/bold] [{color}]{status}[/{color}]\n"
                        f"[bold]Confidence:[/bold] {confidence:.1%}\n\n"
                        f"{summary}",
                        title=f"Consensus Update • {time_str}",
                        border_style=color
                    ))

                elif msg_type == "discussion_complete":
                    complete_data = data.get("data", {})
                    total_turns = complete_data.get("total_turns", 0)
                    consensus = complete_data.get("consensus_reached", False)
                    summary = complete_data.get("final_summary", "")

                    console.print(Panel(
                        f"[bold]Total Turns:[/bold] {total_turns}\n"
                        f"[bold]Consensus:[/bold] {'Yes ✓' if consensus else 'No ✗'}\n\n"
                        f"{summary}",
                        title="Discussion Complete",
                        border_style="green"
                    ))

                    console.print(f"\n[bold green]Discussion finished after {total_turns} turns![/bold green]")
                    break

                elif msg_type == "error":
                    error = data.get("error", "Unknown error")
                    console.print(Panel(
                        f"[bold red]{error}[/bold red]",
                        title="Error",
                        border_style="red"
                    ))

                elif msg_type == "discussion_stopped":
                    console.print(Panel(
                        "[yellow]Discussion stopped by user[/yellow]",
                        title="Stopped",
                        border_style="yellow"
                    ))
                    break

                else:
                    console.print(f"[dim]Unknown message type: {msg_type}[/dim]")
                    console.print(f"[dim]{json.dumps(data, indent=2)}[/dim]")

                # Store message
                self.messages.append(data)

        except KeyboardInterrupt:
            console.print("\n[yellow]Interrupted by user[/yellow]")
        except Exception as e:
            console.print(f"\n[red]Error receiving messages: {e}[/red]")
        finally:
            console.print(f"\n[bold]Total messages received: {message_count}[/bold]")

    async def send_ping(self):
        """Send periodic ping messages"""
        try:
            while self.running:
                await asyncio.sleep(30)
                if self.websocket:
                    await self.websocket.send("ping")
                    console.print("[dim]→ Sent ping[/dim]")
        except Exception:
            pass

    async def close(self):
        """Close WebSocket connection"""
        self.running = False
        if self.websocket:
            await self.websocket.close()
            console.print("[green]✓ WebSocket closed[/green]")

    async def run(self, topic: str, num_agents: int = 3):
        """Run complete test"""
        try:
            # Create discussion
            if not await self.create_discussion(topic, num_agents):
                return False

            # Connect WebSocket
            if not await self.connect_websocket():
                return False

            # Start ping task
            ping_task = asyncio.create_task(self.send_ping())

            # Receive messages
            await self.receive_messages()

            # Cancel ping task
            ping_task.cancel()

            # Close connection
            await self.close()

            # Summary
            console.print("\n[bold]Test Summary:[/bold]")
            console.print(f"Discussion ID: {self.discussion_id}")
            console.print(f"Messages received: {len(self.messages)}")
            console.print("[green]✓ Test completed successfully[/green]")

            return True

        except Exception as e:
            console.print(f"\n[red]✗ Test failed: {e}[/red]")
            return False


async def test_multiple_clients(discussion_id: str, num_clients: int = 3):
    """Test multiple WebSocket clients connected to same discussion"""
    console.print(f"\n[bold blue]Testing {num_clients} concurrent clients...[/bold blue]")

    clients = []

    async def client_listener(client_id: int):
        """Listen for messages on a client"""
        ws_url = f"{WS_URL}/ws/discussions/{discussion_id}"
        async with websockets.connect(ws_url) as websocket:
            console.print(f"[green]Client {client_id} connected[/green]")
            message_count = 0

            try:
                async for message in websocket:
                    message_count += 1
                    data = json.loads(message)
                    if data.get("type") == "discussion_complete":
                        break
            except Exception as e:
                console.print(f"[red]Client {client_id} error: {e}[/red]")

            console.print(f"[cyan]Client {client_id} received {message_count} messages[/cyan]")

    # Create client tasks
    tasks = [client_listener(i) for i in range(num_clients)]

    # Run all clients concurrently
    await asyncio.gather(*tasks)

    console.print("[green]✓ Multi-client test completed[/green]")


async def main():
    """Main test function"""
    console.print("[bold blue]╔════════════════════════════════════╗[/bold blue]")
    console.print("[bold blue]║   CAMEL Discussion API WS Test    ║[/bold blue]")
    console.print("[bold blue]╚════════════════════════════════════╝[/bold blue]")

    # Check if API is running
    try:
        response = requests.get(f"{API_URL}/health", timeout=5)
        if response.status_code == 200:
            console.print("[green]✓ API is running[/green]")
        else:
            console.print("[red]✗ API health check failed[/red]")
            return
    except Exception as e:
        console.print(f"[red]✗ Cannot connect to API: {e}[/red]")
        console.print(f"[yellow]Make sure the API is running on {API_URL}[/yellow]")
        return

    # Get topic from user or use default
    if len(sys.argv) > 1:
        topic = " ".join(sys.argv[1:])
    else:
        topic = "What are the best strategies for treating chronic migraine?"

    # Run test
    tester = WebSocketTester()
    success = await tester.run(topic, num_agents=3)

    if success:
        console.print("\n[bold green]All tests passed! ✓[/bold green]")
    else:
        console.print("\n[bold red]Test failed! ✗[/bold red]")
        sys.exit(1)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        console.print("\n[yellow]Interrupted by user[/yellow]")
        sys.exit(0)
