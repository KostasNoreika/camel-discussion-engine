"""
Discussion Orchestrator
Orchestrates multi-agent discussions with dynamic role creation and emergent communication
"""
import uuid
from typing import List, Dict, Optional
from datetime import datetime
from pydantic import BaseModel
from loguru import logger

from src.camel_engine.llm_provider import OpenRouterClient
from src.camel_engine.role_creator import RoleCreator, RoleDefinition
from src.camel_engine.consensus import ConsensusDetector, ConsensusResult, Message


class DiscussionMessage(BaseModel):
    """Message in a discussion"""
    id: int
    discussion_id: str
    role_name: str
    model: str
    content: str
    is_user: bool = False
    turn_number: int
    created_at: datetime


class Discussion(BaseModel):
    """Active discussion session"""
    id: str
    topic: str
    user_id: str
    roles: List[RoleDefinition]
    messages: List[DiscussionMessage] = []
    status: str = "active"  # active, completed, stopped
    consensus_reached: bool = False
    consensus_summary: Optional[str] = None
    current_turn: int = 0
    created_at: datetime
    updated_at: datetime


class DiscussionResult(BaseModel):
    """Final result of a discussion"""
    discussion_id: str
    topic: str
    total_turns: int
    consensus_reached: bool
    consensus_confidence: float
    final_summary: str
    key_agreements: List[str]
    disagreements: List[str]
    messages: List[DiscussionMessage]
    duration_seconds: float


class DiscussionOrchestrator:
    """
    Orchestrates multi-agent discussions with dynamic role creation

    Features:
    - Dynamic role creation based on topic analysis
    - AI-driven speaker selection (not round-robin)
    - Natural conversation flow with @mentions
    - Consensus detection
    - Support for multiple LLM providers
    """

    def __init__(
        self,
        openrouter_api_key: str,
        max_turns: int = 20,
        consensus_threshold: float = 0.85
    ):
        self.llm_client = OpenRouterClient(api_key=openrouter_api_key)
        self.role_creator = RoleCreator(llm_client=self.llm_client)
        self.consensus_detector = ConsensusDetector(
            llm_client=self.llm_client,
            consensus_threshold=consensus_threshold
        )

        self.max_turns = max_turns
        self.active_discussions: Dict[str, Discussion] = {}

    async def create_discussion(
        self,
        topic: str,
        user_id: str = "default",
        num_agents: int = 4,
        model_preferences: Optional[List[str]] = None
    ) -> str:
        """
        Create a new discussion with dynamically assigned roles

        Args:
            topic: Discussion topic
            user_id: User identifier
            num_agents: Number of agent roles to create
            model_preferences: Preferred models for agents

        Returns:
            Discussion ID
        """
        logger.info(f"Creating discussion: {topic} (num_agents={num_agents})")

        # Generate unique discussion ID
        discussion_id = str(uuid.uuid4())

        # Analyze topic and create roles
        roles = await self.role_creator.create_roles(
            topic=topic,
            num_roles=num_agents,
            model_preferences=model_preferences
        )

        # Initialize discussion
        discussion = Discussion(
            id=discussion_id,
            topic=topic,
            user_id=user_id,
            roles=roles,
            messages=[],
            status="active",
            current_turn=0,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )

        self.active_discussions[discussion_id] = discussion

        logger.info(
            f"Discussion created: {discussion_id[:8]} | "
            f"Roles: {[r.name for r in roles]}"
        )

        return discussion_id

    async def run_discussion(
        self,
        discussion_id: str,
        max_turns: Optional[int] = None
    ) -> DiscussionResult:
        """
        Run discussion until consensus or max turns

        Args:
            discussion_id: Discussion identifier
            max_turns: Override default max turns

        Returns:
            Discussion result with final summary
        """
        discussion = self.active_discussions.get(discussion_id)
        if not discussion:
            raise ValueError(f"Discussion {discussion_id} not found")

        max_turns = max_turns or self.max_turns
        start_time = datetime.utcnow()

        logger.info(f"Starting discussion {discussion_id[:8]} (max {max_turns} turns)")

        # Initialize with topic introduction
        await self._add_system_message(
            discussion,
            f"Discussion started: {discussion.topic}\n"
            f"Participants: {', '.join(r.name for r in discussion.roles)}"
        )

        # Main discussion loop
        while discussion.current_turn < max_turns:
            discussion.current_turn += 1

            logger.debug(f"Turn {discussion.current_turn}/{max_turns}")

            # Select next speaker (AI-driven)
            speaker_role = await self.select_next_speaker(discussion)

            # Generate response from speaker
            message = await self.generate_agent_message(discussion, speaker_role)

            # Add message to discussion
            self._add_message(discussion, message)

            # Check for consensus every few turns
            if discussion.current_turn >= 3 and discussion.current_turn % 2 == 0:
                consensus = await self.check_consensus(discussion)

                if consensus.reached:
                    logger.info(f"Consensus reached at turn {discussion.current_turn}")
                    discussion.consensus_reached = True
                    discussion.status = "completed"
                    break

                if consensus.recommendation == "escalate":
                    logger.warning("Stalemate detected, concluding discussion")
                    break

        # Generate final result
        result = await self.generate_result(discussion, start_time)

        discussion.status = "completed"
        discussion.updated_at = datetime.utcnow()

        logger.info(
            f"Discussion completed: {discussion_id[:8]} | "
            f"Turns: {result.total_turns} | "
            f"Consensus: {result.consensus_reached}"
        )

        return result

    async def select_next_speaker(self, discussion: Discussion) -> RoleDefinition:
        """
        AI-driven selection of next speaker (not round-robin)

        Args:
            discussion: Current discussion state

        Returns:
            Role definition of next speaker
        """
        # For first turn, use first role
        if len(discussion.messages) <= 1:
            return discussion.roles[0]

        # Get recent conversation context
        recent_messages = discussion.messages[-5:]
        formatted_context = "\n".join([
            f"{msg.role_name}: {msg.content[:100]}..."
            for msg in recent_messages
        ])

        # Ask AI who should speak next
        prompt = f"""This is a multi-expert discussion. Based on the recent conversation, who should speak next?

**Topic**: {discussion.topic}

**Available participants**:
{chr(10).join(f"- {role.name}: {role.expertise}" for role in discussion.roles)}

**Recent conversation**:
{formatted_context}

Who should logically respond next based on:
1. What was just discussed
2. Whose expertise is most relevant
3. Natural conversation flow

Return ONLY the name of the participant (exactly as listed above).
"""

        try:
            messages = [{"role": "user", "content": prompt}]

            response = await self.llm_client.chat_completion(
                model="openai/gpt-4",
                messages=messages,
                temperature=0.5,
                max_tokens=50
            )

            # Find matching role
            selected_name = response.strip()
            for role in discussion.roles:
                if role.name in selected_name or selected_name in role.name:
                    logger.debug(f"AI selected next speaker: {role.name}")
                    return role

            # Fallback: rotate through roles
            logger.warning(f"Could not match AI selection '{selected_name}', using fallback")
            return self._fallback_speaker_selection(discussion)

        except Exception as e:
            logger.error(f"Speaker selection error: {str(e)}, using fallback")
            return self._fallback_speaker_selection(discussion)

    def _fallback_speaker_selection(self, discussion: Discussion) -> RoleDefinition:
        """Fallback speaker selection (round-robin with variations)"""
        # Get roles that spoke least recently
        role_counts = {role.name: 0 for role in discussion.roles}

        for msg in discussion.messages[-10:]:
            if msg.role_name in role_counts:
                role_counts[msg.role_name] += 1

        # Select role with fewest recent messages
        min_count = min(role_counts.values())
        candidates = [
            role for role in discussion.roles
            if role_counts[role.name] == min_count
        ]

        return candidates[0]

    async def generate_agent_message(
        self,
        discussion: Discussion,
        role: RoleDefinition
    ) -> DiscussionMessage:
        """
        Generate message from an agent role

        Args:
            discussion: Current discussion
            role: Role generating the message

        Returns:
            Generated message
        """
        # Build conversation context
        context_messages = []

        # Add system prompt
        context_messages.append({
            "role": "system",
            "content": role.system_prompt
        })

        # Add conversation history
        for msg in discussion.messages:
            if msg.is_user:
                context_messages.append({
                    "role": "user",
                    "content": f"[User]: {msg.content}"
                })
            else:
                context_messages.append({
                    "role": "assistant" if msg.role_name == role.name else "user",
                    "content": f"[{msg.role_name}]: {msg.content}"
                })

        # Generate response
        try:
            response = await self.llm_client.chat_completion(
                model=role.model,
                messages=context_messages,
                temperature=0.7,
                max_tokens=500
            )

            # Create message object
            message = DiscussionMessage(
                id=len(discussion.messages) + 1,
                discussion_id=discussion.id,
                role_name=role.name,
                model=role.model,
                content=response,
                is_user=False,
                turn_number=discussion.current_turn,
                created_at=datetime.utcnow()
            )

            logger.debug(f"Generated message from {role.name} ({len(response)} chars)")

            return message

        except Exception as e:
            logger.error(f"Message generation error for {role.name}: {str(e)}")

            # Return error message
            return DiscussionMessage(
                id=len(discussion.messages) + 1,
                discussion_id=discussion.id,
                role_name=role.name,
                model=role.model,
                content=f"[Error generating response: {str(e)}]",
                is_user=False,
                turn_number=discussion.current_turn,
                created_at=datetime.utcnow()
            )

    async def check_consensus(self, discussion: Discussion) -> ConsensusResult:
        """Check if consensus has been reached"""
        # Convert DiscussionMessage to consensus.Message
        messages = [
            Message(
                role_name=msg.role_name,
                content=msg.content,
                turn_number=msg.turn_number
            )
            for msg in discussion.messages
            if not msg.is_user
        ]

        return await self.consensus_detector.check_consensus(
            messages=messages,
            topic=discussion.topic,
            current_turn=discussion.current_turn,
            max_turns=self.max_turns
        )

    async def generate_result(
        self,
        discussion: Discussion,
        start_time: datetime
    ) -> DiscussionResult:
        """Generate final discussion result"""
        # Check final consensus
        consensus = await self.check_consensus(discussion)

        # Generate final summary
        messages = [
            Message(
                role_name=msg.role_name,
                content=msg.content,
                turn_number=msg.turn_number
            )
            for msg in discussion.messages
            if not msg.is_user
        ]

        final_summary = await self.consensus_detector.generate_final_summary(
            messages=messages,
            topic=discussion.topic,
            consensus=consensus
        )

        # Calculate duration
        duration = (datetime.utcnow() - start_time).total_seconds()

        return DiscussionResult(
            discussion_id=discussion.id,
            topic=discussion.topic,
            total_turns=discussion.current_turn,
            consensus_reached=consensus.reached,
            consensus_confidence=consensus.confidence,
            final_summary=final_summary,
            key_agreements=consensus.agreements,
            disagreements=consensus.disagreements,
            messages=discussion.messages,
            duration_seconds=duration
        )

    def _add_message(self, discussion: Discussion, message: DiscussionMessage):
        """Add message to discussion"""
        discussion.messages.append(message)
        discussion.updated_at = datetime.utcnow()

    async def _add_system_message(self, discussion: Discussion, content: str):
        """Add system message to discussion"""
        message = DiscussionMessage(
            id=len(discussion.messages) + 1,
            discussion_id=discussion.id,
            role_name="System",
            model="system",
            content=content,
            is_user=False,
            turn_number=0,
            created_at=datetime.utcnow()
        )
        self._add_message(discussion, message)

    def get_discussion(self, discussion_id: str) -> Optional[Discussion]:
        """Retrieve discussion by ID"""
        return self.active_discussions.get(discussion_id)

    def list_active_discussions(self) -> List[str]:
        """List all active discussion IDs"""
        return [
            disc_id for disc_id, disc in self.active_discussions.items()
            if disc.status == "active"
        ]
