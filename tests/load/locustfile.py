"""
Load testing for CAMEL Discussion API

Tests system performance under concurrent load using Locust.

Usage:
    locust -f tests/load/locustfile.py --host=http://localhost:8007
    locust -f tests/load/locustfile.py --host=http://localhost:8007 --users 10 --spawn-rate 2
"""

from locust import HttpUser, task, between, events
import json
import random


class DiscussionUser(HttpUser):
    """
    Simulates a user creating and interacting with discussions
    """

    wait_time = between(1, 3)  # Wait 1-3 seconds between tasks
    host = "http://localhost:8007"

    def on_start(self):
        """Called when a user starts (initialization)"""
        self.discussion_id = None
        self.user_id = f"load-test-user-{self.environment.runner.user_count}"

        # Sample topics for variety
        self.topics = [
            "Best practices for microservices architecture",
            "Impact of AI on software development",
            "Choosing between SQL and NoSQL databases",
            "Security considerations for web applications",
            "Benefits of continuous integration and deployment",
            "Scalability patterns for cloud applications",
            "Code review best practices",
            "Testing strategies for modern applications",
            "DevOps culture and practices",
            "Performance optimization techniques"
        ]

    @task(1)
    def create_discussion(self):
        """
        Create a new discussion

        Weight: 1 (less frequent - creation is expensive)
        """
        topic = random.choice(self.topics)

        with self.client.post(
            "/api/discussions/create",
            json={
                "topic": topic,
                "num_agents": random.randint(2, 4),
                "user_id": self.user_id,
                "max_turns": random.randint(5, 15)
            },
            catch_response=True
        ) as response:
            if response.status_code == 201:
                data = response.json()
                self.discussion_id = data.get("discussion_id")
                response.success()
            else:
                response.failure(f"Failed to create discussion: {response.status_code}")

    @task(3)
    def get_discussion(self):
        """
        Get discussion details

        Weight: 3 (frequent - lightweight operation)
        """
        if not self.discussion_id:
            return

        with self.client.get(
            f"/api/discussions/{self.discussion_id}",
            catch_response=True
        ) as response:
            if response.status_code == 200:
                response.success()
            elif response.status_code == 404:
                # Discussion not found, create a new one
                self.discussion_id = None
                response.success()  # Not an error, just reset
            else:
                response.failure(f"Failed to get discussion: {response.status_code}")

    @task(2)
    def get_messages(self):
        """
        Get discussion messages

        Weight: 2 (moderate - common operation)
        """
        if not self.discussion_id:
            return

        with self.client.get(
            f"/api/discussions/{self.discussion_id}/messages",
            params={"limit": 20},
            catch_response=True
        ) as response:
            if response.status_code == 200:
                data = response.json()
                message_count = len(data.get("messages", []))
                response.success()
            elif response.status_code == 404:
                self.discussion_id = None
                response.success()
            else:
                response.failure(f"Failed to get messages: {response.status_code}")

    @task(1)
    def send_message(self):
        """
        Send user message to discussion

        Weight: 1 (less frequent - triggers agent responses)
        """
        if not self.discussion_id:
            return

        messages = [
            "What do you think about this approach?",
            "Can you elaborate on that point?",
            "I'd like to hear more perspectives.",
            "What are the trade-offs here?",
            "How does this compare to alternatives?",
            "What about security considerations?",
            "Can you provide specific examples?",
            "What are the performance implications?"
        ]

        with self.client.post(
            f"/api/discussions/{self.discussion_id}/message",
            json={
                "content": random.choice(messages),
                "user_id": self.user_id
            },
            catch_response=True
        ) as response:
            if response.status_code == 200:
                response.success()
            elif response.status_code == 404:
                self.discussion_id = None
                response.success()
            else:
                response.failure(f"Failed to send message: {response.status_code}")

    @task(1)
    def stop_discussion(self):
        """
        Stop an active discussion

        Weight: 1 (cleanup operation)
        """
        if not self.discussion_id:
            return

        # Only stop occasionally (10% chance)
        if random.random() < 0.1:
            with self.client.post(
                f"/api/discussions/{self.discussion_id}/stop",
                catch_response=True
            ) as response:
                if response.status_code == 200:
                    response.success()
                    self.discussion_id = None  # Reset after stopping
                elif response.status_code == 404:
                    self.discussion_id = None
                    response.success()
                else:
                    response.failure(f"Failed to stop discussion: {response.status_code}")

    @task(2)
    def health_check(self):
        """
        Health check endpoint

        Weight: 2 (frequent - lightweight)
        """
        with self.client.get(
            "/health",
            catch_response=True
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Health check failed: {response.status_code}")

    @task(1)
    def list_models(self):
        """
        List available models

        Weight: 1 (occasional - informational)
        """
        with self.client.get(
            "/api/models/",
            catch_response=True
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Failed to list models: {response.status_code}")


class HeavyDiscussionUser(HttpUser):
    """
    Simulates users creating longer, more intensive discussions

    Use for stress testing with:
    locust -f tests/load/locustfile.py --user-classes HeavyDiscussionUser
    """

    wait_time = between(2, 5)
    host = "http://localhost:8007"

    def on_start(self):
        self.discussion_id = None
        self.user_id = f"heavy-user-{self.environment.runner.user_count}"

    @task(2)
    def create_large_discussion(self):
        """Create discussion with many agents"""
        with self.client.post(
            "/api/discussions/create",
            json={
                "topic": "Complex multi-faceted technical decision",
                "num_agents": 6,  # Maximum agents
                "user_id": self.user_id,
                "max_turns": 30  # Long discussion
            },
            catch_response=True
        ) as response:
            if response.status_code == 201:
                data = response.json()
                self.discussion_id = data.get("discussion_id")
                response.success()
            else:
                response.failure(f"Failed to create large discussion: {response.status_code}")

    @task(1)
    def send_multiple_messages(self):
        """Send burst of messages"""
        if not self.discussion_id:
            return

        for i in range(3):
            self.client.post(
                f"/api/discussions/{self.discussion_id}/message",
                json={
                    "content": f"Message burst {i+1}: What are your thoughts?",
                    "user_id": self.user_id
                }
            )

    @task(3)
    def get_full_history(self):
        """Retrieve full message history"""
        if not self.discussion_id:
            return

        with self.client.get(
            f"/api/discussions/{self.discussion_id}/messages",
            params={"limit": 100},  # Large limit
            catch_response=True
        ) as response:
            if response.status_code == 200:
                response.success()
            elif response.status_code == 404:
                self.discussion_id = None
                response.success()
            else:
                response.failure(f"Failed to get full history: {response.status_code}")


# Event hooks for custom reporting

@events.test_start.add_listener
def on_test_start(environment, **kwargs):
    """Called when load test starts"""
    print("\n" + "="*60)
    print("🧪 CAMEL Discussion API Load Test Starting")
    print("="*60 + "\n")


@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    """Called when load test ends"""
    print("\n" + "="*60)
    print("🏁 CAMEL Discussion API Load Test Complete")
    print("="*60)

    stats = environment.stats
    print(f"\nTotal Requests: {stats.total.num_requests}")
    print(f"Total Failures: {stats.total.num_failures}")
    print(f"Average Response Time: {stats.total.avg_response_time:.2f}ms")
    print(f"Requests per Second: {stats.total.current_rps:.2f}")

    if stats.total.num_failures > 0:
        print(f"\n⚠️  {stats.total.num_failures} requests failed")

        failure_rate = (stats.total.num_failures / stats.total.num_requests) * 100
        if failure_rate > 5:
            print(f"❌ High failure rate: {failure_rate:.2f}%")
            print("   System may be overloaded or have issues")
        else:
            print(f"✅ Acceptable failure rate: {failure_rate:.2f}%")
    else:
        print("\n✅ All requests successful!")

    print("\n")


@events.request.add_listener
def on_request(request_type, name, response_time, response_length, exception, **kwargs):
    """
    Track slow requests

    Logs requests that take longer than threshold
    """
    SLOW_REQUEST_THRESHOLD = 2000  # 2 seconds

    if response_time > SLOW_REQUEST_THRESHOLD:
        print(f"⚠️  Slow request: {name} took {response_time:.0f}ms")


# Custom load test scenarios

class ReadOnlyUser(HttpUser):
    """
    User that only reads, doesn't create or modify

    Use for testing read scalability:
    locust -f tests/load/locustfile.py --user-classes ReadOnlyUser
    """

    wait_time = between(0.5, 1.5)
    host = "http://localhost:8007"

    def on_start(self):
        # Pre-create a discussion to read from
        response = self.client.post(
            "/api/discussions/create",
            json={
                "topic": "Read-only test discussion",
                "num_agents": 3,
                "user_id": "readonly-setup",
                "max_turns": 10
            }
        )
        if response.status_code == 201:
            self.discussion_id = response.json().get("discussion_id")
        else:
            self.discussion_id = "disc_fallback"

    @task(5)
    def read_discussion(self):
        """Read discussion status repeatedly"""
        self.client.get(f"/api/discussions/{self.discussion_id}")

    @task(3)
    def read_messages(self):
        """Read messages repeatedly"""
        self.client.get(f"/api/discussions/{self.discussion_id}/messages")

    @task(2)
    def health_check(self):
        """Health checks"""
        self.client.get("/health")


# Helper class for WebSocket load testing
class WebSocketLoadTest:
    """
    WebSocket load testing (separate from Locust HTTP)

    Run with: python tests/load/websocket_load.py
    """

    @staticmethod
    async def run_websocket_test(num_clients: int = 10):
        """
        Test WebSocket connections under load

        Args:
            num_clients: Number of concurrent WebSocket clients
        """
        import asyncio
        from websockets import connect

        async def websocket_client(discussion_id: str, client_id: int):
            """Single WebSocket client"""
            ws_url = f"ws://localhost:8007/ws/discussions/{discussion_id}"
            messages_received = 0

            try:
                async with connect(ws_url) as websocket:
                    # Receive messages for 30 seconds
                    timeout = 30
                    start = asyncio.get_event_loop().time()

                    while asyncio.get_event_loop().time() - start < timeout:
                        try:
                            await asyncio.wait_for(websocket.recv(), timeout=2.0)
                            messages_received += 1
                        except asyncio.TimeoutError:
                            pass

                return client_id, messages_received, None

            except Exception as e:
                return client_id, messages_received, str(e)

        # Create discussion for test
        import httpx
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "http://localhost:8007/api/discussions/create",
                json={
                    "topic": "WebSocket load test",
                    "num_agents": 3,
                    "user_id": "ws-load-test",
                    "max_turns": 20
                }
            )

            if response.status_code == 201:
                discussion_id = response.json()["discussion_id"]
            else:
                print("Failed to create discussion for WebSocket test")
                return

        # Run clients concurrently
        results = await asyncio.gather(*[
            websocket_client(discussion_id, i)
            for i in range(num_clients)
        ])

        # Report results
        successful = sum(1 for _, _, error in results if error is None)
        total_messages = sum(count for _, count, _ in results)

        print(f"\nWebSocket Load Test Results:")
        print(f"Clients: {num_clients}")
        print(f"Successful: {successful}/{num_clients}")
        print(f"Total Messages: {total_messages}")
        print(f"Avg Messages/Client: {total_messages/num_clients:.1f}")

        # Show errors
        errors = [(cid, err) for cid, _, err in results if err]
        if errors:
            print(f"\nErrors: {len(errors)}")
            for cid, err in errors[:5]:  # Show first 5
                print(f"  Client {cid}: {err}")


if __name__ == "__main__":
    """
    Run directly for WebSocket testing
    """
    import asyncio
    asyncio.run(WebSocketLoadTest.run_websocket_test(num_clients=20))
