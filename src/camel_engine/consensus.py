"""
Consensus Detection
Detects when discussion participants have reached consensus
"""
from typing import List, Dict, Optional
from pydantic import BaseModel, Field
from loguru import logger

from src.camel_engine.llm_provider import OpenRouterClient


class ConsensusResult(BaseModel):
    """Result of consensus analysis"""
    reached: bool = Field(..., description="Whether consensus was reached")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence level (0-1)")
    summary: str = Field(..., description="Summary of the consensus or current state")
    agreements: List[str] = Field(default_factory=list, description="Key points of agreement")
    disagreements: List[str] = Field(default_factory=list, description="Remaining disagreements")
    recommendation: str = Field(..., description="Continue, conclude, or escalate")


class Message(BaseModel):
    """Message in a discussion"""
    role_name: str
    content: str
    turn_number: int


class ConsensusDetector:
    """
    Detects when discussion has reached consensus

    Uses LLM to analyze conversation patterns and determine:
    - Agreement level among participants
    - Key points of consensus
    - Remaining disagreements
    - Whether to continue or conclude
    """

    def __init__(
        self,
        llm_client: OpenRouterClient,
        analysis_model: str = "openai/gpt-5-chat",
        consensus_threshold: float = 0.85
    ):
        self.llm_client = llm_client
        self.analysis_model = analysis_model
        self.consensus_threshold = consensus_threshold

    async def check_consensus(
        self,
        messages: List[Message],
        topic: str,
        current_turn: int,
        max_turns: int
    ) -> ConsensusResult:
        """
        Analyze recent messages to determine consensus level

        Args:
            messages: List of discussion messages
            topic: Original discussion topic
            current_turn: Current turn number
            max_turns: Maximum allowed turns

        Returns:
            Consensus analysis result
        """
        logger.info(f"Checking consensus at turn {current_turn}/{max_turns}")

        # Only check after minimum number of messages
        if len(messages) < 3:
            return ConsensusResult(
                reached=False,
                confidence=0.0,
                summary="Discussion just started, need more exchanges",
                agreements=[],
                disagreements=[],
                recommendation="continue"
            )

        # Check for stalemate
        if await self.detect_stalemate(messages):
            return ConsensusResult(
                reached=False,
                confidence=0.3,
                summary="Discussion appears stuck in circular arguments",
                agreements=[],
                disagreements=["Repeated arguments without progress"],
                recommendation="escalate"
            )

        # Analyze conversation for consensus
        analysis = await self.analyze_consensus(messages, topic)

        # Determine if consensus is reached
        reached = analysis.confidence >= self.consensus_threshold

        # Add recommendation
        if reached:
            analysis.recommendation = "conclude"
        elif current_turn >= max_turns:
            analysis.recommendation = "conclude"  # Time's up
        elif len(analysis.disagreements) == 0:
            analysis.recommendation = "conclude"  # No more issues
        else:
            analysis.recommendation = "continue"

        logger.info(
            f"Consensus: {reached} (confidence: {analysis.confidence:.2f}) - "
            f"Recommendation: {analysis.recommendation}"
        )

        return analysis

    async def analyze_consensus(
        self,
        messages: List[Message],
        topic: str
    ) -> ConsensusResult:
        """
        Analyze conversation using LLM

        Args:
            messages: Discussion messages
            topic: Original topic

        Returns:
            Detailed consensus analysis
        """
        # Format recent messages for analysis
        recent_messages = messages[-10:]  # Last 10 messages
        formatted_messages = self.format_messages(recent_messages)

        prompt = f"""Analyze this multi-agent discussion and determine the consensus level.

**Topic**: {topic}

**Recent conversation**:
{formatted_messages}

Evaluate:
1. Are participants converging on shared understanding?
2. What are the key points of agreement?
3. What disagreements (if any) remain?
4. Overall confidence level that consensus has been reached (0.0 to 1.0)

Return JSON with:
{{
  "confidence": <float 0-1>,
  "summary": "<brief summary of current state>",
  "agreements": ["point 1", "point 2", ...],
  "disagreements": ["issue 1", "issue 2", ...]
}}

Consider consensus reached if:
- Participants explicitly agree on core points
- No significant disagreements remain
- Discussion has converged (not diverged)
"""

        try:
            llm_messages = [{"role": "user", "content": prompt}]

            response = await self.llm_client.chat_completion_structured(
                model=self.analysis_model,
                messages=llm_messages,
                temperature=0.2  # Low temperature for consistent analysis
            )

            return ConsensusResult(
                reached=response["confidence"] >= self.consensus_threshold,
                confidence=response["confidence"],
                summary=response["summary"],
                agreements=response.get("agreements", []),
                disagreements=response.get("disagreements", []),
                recommendation="continue"  # Will be set by caller
            )

        except Exception as e:
            logger.error(f"Consensus analysis failed: {str(e)}")
            # Fallback result
            return ConsensusResult(
                reached=False,
                confidence=0.5,
                summary="Unable to analyze consensus reliably",
                agreements=[],
                disagreements=["Analysis error"],
                recommendation="continue"
            )

    async def detect_stalemate(self, messages: List[Message]) -> bool:
        """
        Detect if discussion is stuck in circular arguments

        Args:
            messages: Recent discussion messages

        Returns:
            True if stalemate detected
        """
        # Check if last 6 messages show repetition
        if len(messages) < 6:
            return False

        recent = messages[-6:]

        # Simple heuristic: Check for repeated key phrases
        contents = [msg.content.lower() for msg in recent]

        # Count similar messages
        similarity_threshold = 0.7
        similar_count = 0

        for i in range(len(contents)):
            for j in range(i + 1, len(contents)):
                # Simple similarity check (can be improved)
                words_i = set(contents[i].split())
                words_j = set(contents[j].split())

                if len(words_i) == 0 or len(words_j) == 0:
                    continue

                intersection = len(words_i & words_j)
                union = len(words_i | words_j)

                similarity = intersection / union if union > 0 else 0

                if similarity > similarity_threshold:
                    similar_count += 1

        # If more than 2 pairs of similar messages, likely stalemate
        return similar_count > 2

    def format_messages(self, messages: List[Message]) -> str:
        """
        Format messages for LLM analysis

        Args:
            messages: List of messages to format

        Returns:
            Formatted string representation
        """
        formatted = []
        for msg in messages:
            formatted.append(f"**{msg.role_name}** (Turn {msg.turn_number}):\n{msg.content}\n")

        return "\n".join(formatted)

    async def generate_final_summary(
        self,
        messages: List[Message],
        topic: str,
        consensus: ConsensusResult
    ) -> str:
        """
        Generate final summary of the discussion

        Args:
            messages: All discussion messages
            topic: Original topic
            consensus: Final consensus result

        Returns:
            Comprehensive summary
        """
        formatted_messages = self.format_messages(messages)

        prompt = f"""Create a comprehensive summary of this multi-agent discussion.

**Topic**: {topic}

**Consensus Status**: {"✅ Reached" if consensus.reached else "⚠️ Not fully reached"}
**Confidence**: {consensus.confidence:.0%}

**Full conversation**:
{formatted_messages}

**Key agreements**:
{chr(10).join(f"- {a}" for a in consensus.agreements)}

**Remaining disagreements**:
{chr(10).join(f"- {d}" for d in consensus.disagreements) if consensus.disagreements else "None"}

Provide:
1. Executive summary (2-3 sentences)
2. Main conclusions
3. Recommended next steps (if any)

Keep it concise and actionable.
"""

        try:
            llm_messages = [{"role": "user", "content": prompt}]

            summary = await self.llm_client.chat_completion(
                model=self.analysis_model,
                messages=llm_messages,
                temperature=0.3
            )

            return summary

        except Exception as e:
            logger.error(f"Summary generation failed: {str(e)}")
            return consensus.summary
