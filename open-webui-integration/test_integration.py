#!/usr/bin/env python3
"""
CAMEL Discussion - Open WebUI Integration Test Script

Tests connectivity and basic operations of the CAMEL Discussion API
to verify the integration is working correctly.

Usage:
    python3 test_integration.py
    python3 test_integration.py --api-url http://custom-url:8007
    python3 test_integration.py --verbose
"""

import argparse
import asyncio
import json
import sys
import time
from typing import Optional, Dict, Any

try:
    import httpx
    from rich.console import Console
    from rich.table import Table
    from rich.panel import Panel
    from rich.progress import Progress, SpinnerColumn, TextColumn
except ImportError:
    print("❌ Missing dependencies. Install with:")
    print("   pip install httpx rich")
    sys.exit(1)

console = Console()

# Default API endpoint
DEFAULT_API_URL = "http://192.168.110.199:8007"
DEFAULT_TIMEOUT = 30.0


class IntegrationTester:
    """Test suite for CAMEL Discussion API integration"""

    def __init__(self, api_url: str, verbose: bool = False):
        self.api_url = api_url.rstrip('/')
        self.verbose = verbose
        self.test_results = []
        self.discussion_id: Optional[str] = None

    def log(self, message: str):
        """Log verbose messages"""
        if self.verbose:
            console.print(f"  [dim]{message}[/dim]")

    def record_result(self, test_name: str, passed: bool, message: str):
        """Record test result"""
        self.test_results.append({
            "name": test_name,
            "passed": passed,
            "message": message
        })

        if passed:
            console.print(f"✅ {test_name}: [green]{message}[/green]")
        else:
            console.print(f"❌ {test_name}: [red]{message}[/red]")

    async def test_health_check(self) -> bool:
        """Test 1: API Health Check"""
        test_name = "Health Check"

        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                self.log(f"GET {self.api_url}/health")
                response = await client.get(f"{self.api_url}/health")

                if response.status_code != 200:
                    self.record_result(test_name, False,
                                     f"Status {response.status_code}")
                    return False

                data = response.json()
                status = data.get("status")

                if status == "healthy":
                    self.record_result(test_name, True,
                                     f"API is healthy (v{data.get('version', 'unknown')})")
                    return True
                else:
                    self.record_result(test_name, False,
                                     f"Unexpected status: {status}")
                    return False

        except httpx.ConnectError:
            self.record_result(test_name, False,
                             f"Cannot connect to {self.api_url}")
            return False
        except httpx.TimeoutException:
            self.record_result(test_name, False, "Connection timeout")
            return False
        except Exception as e:
            self.record_result(test_name, False, f"Error: {str(e)}")
            return False

    async def test_list_models(self) -> bool:
        """Test 2: List Available Models"""
        test_name = "List Models"

        try:
            async with httpx.AsyncClient(timeout=DEFAULT_TIMEOUT) as client:
                self.log(f"GET {self.api_url}/api/models/")
                response = await client.get(f"{self.api_url}/api/models/")

                if response.status_code != 200:
                    self.record_result(test_name, False,
                                     f"Status {response.status_code}")
                    return False

                data = response.json()
                models = data.get("models", [])

                if len(models) > 0:
                    model_names = [m.get("model_name") for m in models]
                    self.record_result(test_name, True,
                                     f"Found {len(models)} models: {', '.join(model_names[:3])}")
                    return True
                else:
                    self.record_result(test_name, False, "No models available")
                    return False

        except Exception as e:
            self.record_result(test_name, False, f"Error: {str(e)}")
            return False

    async def test_create_discussion(self) -> bool:
        """Test 3: Create Discussion"""
        test_name = "Create Discussion"

        try:
            async with httpx.AsyncClient(timeout=DEFAULT_TIMEOUT) as client:
                payload = {
                    "topic": "Test discussion for integration verification",
                    "num_agents": 3,
                    "user_id": "test_user_integration",
                    "max_turns": 5
                }

                self.log(f"POST {self.api_url}/api/discussions/create")
                self.log(f"Payload: {json.dumps(payload, indent=2)}")

                response = await client.post(
                    f"{self.api_url}/api/discussions/create",
                    json=payload
                )

                if response.status_code != 201:
                    self.record_result(test_name, False,
                                     f"Status {response.status_code}: {response.text}")
                    return False

                data = response.json()
                self.discussion_id = data.get("discussion_id")
                num_agents = len(data.get("roles", []))

                if self.discussion_id and num_agents == 3:
                    self.record_result(test_name, True,
                                     f"Created discussion {self.discussion_id} with {num_agents} agents")
                    return True
                else:
                    self.record_result(test_name, False,
                                     "Unexpected response format")
                    return False

        except Exception as e:
            self.record_result(test_name, False, f"Error: {str(e)}")
            return False

    async def test_get_discussion(self) -> bool:
        """Test 4: Get Discussion Status"""
        test_name = "Get Discussion Status"

        if not self.discussion_id:
            self.record_result(test_name, False, "No discussion_id available")
            return False

        try:
            async with httpx.AsyncClient(timeout=DEFAULT_TIMEOUT) as client:
                self.log(f"GET {self.api_url}/api/discussions/{self.discussion_id}")
                response = await client.get(
                    f"{self.api_url}/api/discussions/{self.discussion_id}"
                )

                if response.status_code != 200:
                    self.record_result(test_name, False,
                                     f"Status {response.status_code}")
                    return False

                data = response.json()
                status = data.get("status")
                turn = data.get("current_turn", 0)

                if status in ["running", "waiting", "completed", "stopped"]:
                    self.record_result(test_name, True,
                                     f"Status: {status}, Turn: {turn}")
                    return True
                else:
                    self.record_result(test_name, False,
                                     f"Unexpected status: {status}")
                    return False

        except Exception as e:
            self.record_result(test_name, False, f"Error: {str(e)}")
            return False

    async def test_send_message(self) -> bool:
        """Test 5: Send User Message"""
        test_name = "Send User Message"

        if not self.discussion_id:
            self.record_result(test_name, False, "No discussion_id available")
            return False

        try:
            async with httpx.AsyncClient(timeout=DEFAULT_TIMEOUT) as client:
                payload = {
                    "content": "This is a test message from integration testing.",
                    "user_id": "test_user_integration"
                }

                self.log(f"POST {self.api_url}/api/discussions/{self.discussion_id}/message")
                response = await client.post(
                    f"{self.api_url}/api/discussions/{self.discussion_id}/message",
                    json=payload
                )

                if response.status_code != 200:
                    self.record_result(test_name, False,
                                     f"Status {response.status_code}")
                    return False

                data = response.json()

                if data.get("status") == "sent":
                    self.record_result(test_name, True, "Message sent successfully")
                    return True
                else:
                    self.record_result(test_name, False, "Unexpected response")
                    return False

        except Exception as e:
            self.record_result(test_name, False, f"Error: {str(e)}")
            return False

    async def test_get_messages(self) -> bool:
        """Test 6: Get Discussion Messages"""
        test_name = "Get Discussion Messages"

        if not self.discussion_id:
            self.record_result(test_name, False, "No discussion_id available")
            return False

        try:
            async with httpx.AsyncClient(timeout=DEFAULT_TIMEOUT) as client:
                self.log(f"GET {self.api_url}/api/discussions/{self.discussion_id}/messages")
                response = await client.get(
                    f"{self.api_url}/api/discussions/{self.discussion_id}/messages",
                    params={"limit": 10}
                )

                if response.status_code != 200:
                    self.record_result(test_name, False,
                                     f"Status {response.status_code}")
                    return False

                data = response.json()
                messages = data.get("messages", [])
                total = data.get("total", 0)

                self.record_result(test_name, True,
                                 f"Retrieved {len(messages)}/{total} messages")
                return True

        except Exception as e:
            self.record_result(test_name, False, f"Error: {str(e)}")
            return False

    async def test_stop_discussion(self) -> bool:
        """Test 7: Stop Discussion"""
        test_name = "Stop Discussion"

        if not self.discussion_id:
            self.record_result(test_name, False, "No discussion_id available")
            return False

        try:
            async with httpx.AsyncClient(timeout=DEFAULT_TIMEOUT) as client:
                self.log(f"POST {self.api_url}/api/discussions/{self.discussion_id}/stop")
                response = await client.post(
                    f"{self.api_url}/api/discussions/{self.discussion_id}/stop"
                )

                if response.status_code != 200:
                    self.record_result(test_name, False,
                                     f"Status {response.status_code}")
                    return False

                data = response.json()

                if data.get("status") == "stopped":
                    self.record_result(test_name, True, "Discussion stopped successfully")
                    return True
                else:
                    self.record_result(test_name, False, "Unexpected response")
                    return False

        except Exception as e:
            self.record_result(test_name, False, f"Error: {str(e)}")
            return False

    async def run_all_tests(self) -> bool:
        """Run complete test suite"""
        console.print("\n[bold cyan]🧪 CAMEL Discussion Integration Test Suite[/bold cyan]\n")
        console.print(f"Testing API: [yellow]{self.api_url}[/yellow]\n")

        # Test sequence
        tests = [
            ("Health Check", self.test_health_check),
            ("List Models", self.test_list_models),
            ("Create Discussion", self.test_create_discussion),
            ("Get Discussion Status", self.test_get_discussion),
            ("Send User Message", self.test_send_message),
            ("Get Discussion Messages", self.test_get_messages),
            ("Stop Discussion", self.test_stop_discussion),
        ]

        for test_name, test_func in tests:
            console.print(f"\n[bold]Testing: {test_name}[/bold]")
            result = await test_func()

            # If critical test fails, stop
            if not result and test_name in ["Health Check", "Create Discussion"]:
                console.print(f"\n[red]❌ Critical test '{test_name}' failed. Stopping tests.[/red]")
                break

            # Small delay between tests
            await asyncio.sleep(0.5)

        # Print summary
        self.print_summary()

        # Return overall success
        return all(r["passed"] for r in self.test_results)

    def print_summary(self):
        """Print test summary"""
        console.print("\n" + "="*60 + "\n")

        passed = sum(1 for r in self.test_results if r["passed"])
        total = len(self.test_results)

        # Create summary table
        table = Table(title="Test Summary", show_header=True, header_style="bold cyan")
        table.add_column("Test", style="white", width=30)
        table.add_column("Result", width=10)
        table.add_column("Details", style="dim")

        for result in self.test_results:
            status = "✅ PASS" if result["passed"] else "❌ FAIL"
            status_style = "green" if result["passed"] else "red"
            table.add_row(
                result["name"],
                f"[{status_style}]{status}[/{status_style}]",
                result["message"]
            )

        console.print(table)

        # Overall result
        success_rate = (passed / total * 100) if total > 0 else 0

        if passed == total:
            panel = Panel(
                f"[bold green]✅ ALL TESTS PASSED ({passed}/{total})[/bold green]\n\n"
                "The integration is working correctly!",
                title="🎉 Success",
                border_style="green"
            )
        else:
            panel = Panel(
                f"[bold red]❌ SOME TESTS FAILED ({passed}/{total} passed)[/bold red]\n\n"
                f"Success rate: {success_rate:.1f}%\n"
                "Check the API logs for more details.",
                title="⚠️ Issues Detected",
                border_style="red"
            )

        console.print("\n")
        console.print(panel)
        console.print("\n")


async def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="Test CAMEL Discussion API integration for Open WebUI"
    )
    parser.add_argument(
        "--api-url",
        default=DEFAULT_API_URL,
        help=f"API base URL (default: {DEFAULT_API_URL})"
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable verbose output"
    )

    args = parser.parse_args()

    # Create tester
    tester = IntegrationTester(api_url=args.api_url, verbose=args.verbose)

    # Run tests
    success = await tester.run_all_tests()

    # Exit with appropriate code
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        console.print("\n\n[yellow]Tests interrupted by user[/yellow]")
        sys.exit(130)
