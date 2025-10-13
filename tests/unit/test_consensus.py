"""
Unit tests for ConsensusDetector component

Tests consensus detection, similarity analysis, and confidence scoring.
"""

import pytest
from unittest.mock import AsyncMock, patch
from src.camel_engine.consensus import ConsensusDetector, ConsensusResult


@pytest.fixture
def consensus_detector():
    """Fixture providing ConsensusDetector instance"""
    return ConsensusDetector()


@pytest.fixture
def agreement_messages():
    """Fixture providing messages showing strong agreement"""
    return [
        {
            "role": "Expert A",
            "content": "I strongly believe that option X is the best choice due to its efficiency and scalability.",
            "turn": 5
        },
        {
            "role": "Expert B",
            "content": "I agree with Expert A. Option X provides the best balance of performance and maintainability.",
            "turn": 5
        },
        {
            "role": "Expert C",
            "content": "Yes, I also think option X is optimal. It clearly outperforms the alternatives.",
            "turn": 5
        }
    ]


@pytest.fixture
def disagreement_messages():
    """Fixture providing messages showing disagreement"""
    return [
        {
            "role": "Expert A",
            "content": "I think option X is best because of its performance.",
            "turn": 3
        },
        {
            "role": "Expert B",
            "content": "I disagree. Option Y is superior due to its security features.",
            "turn": 3
        },
        {
            "role": "Expert C",
            "content": "Actually, option Z is the right choice for cost reasons.",
            "turn": 3
        }
    ]


@pytest.mark.asyncio
async def test_detect_consensus_strong_agreement(consensus_detector, agreement_messages):
    """Test consensus detection with strong agreement"""
    result = await consensus_detector.analyze_messages(agreement_messages)

    assert isinstance(result, ConsensusResult)
    assert result.consensus_reached is True
    assert result.confidence > 0.7
    assert result.summary is not None
    assert "option X" in result.summary.lower()


@pytest.mark.asyncio
async def test_detect_no_consensus(consensus_detector, disagreement_messages):
    """Test consensus detection with clear disagreement"""
    result = await consensus_detector.analyze_messages(disagreement_messages)

    assert isinstance(result, ConsensusResult)
    assert result.consensus_reached is False
    assert result.confidence < 0.5


@pytest.mark.asyncio
async def test_consensus_with_partial_agreement(consensus_detector):
    """Test consensus detection with partial agreement"""
    messages = [
        {
            "role": "Expert A",
            "content": "Option X is good, but it has some drawbacks.",
            "turn": 4
        },
        {
            "role": "Expert B",
            "content": "I agree option X is reasonable, though not perfect.",
            "turn": 4
        },
        {
            "role": "Expert C",
            "content": "Option X seems acceptable overall.",
            "turn": 4
        }
    ]

    result = await consensus_detector.analyze_messages(messages)

    assert isinstance(result, ConsensusResult)
    # Partial agreement should have moderate confidence
    assert 0.4 < result.confidence < 0.8


@pytest.mark.asyncio
async def test_consensus_requires_minimum_messages(consensus_detector):
    """Test that consensus requires sufficient messages"""
    messages = [
        {"role": "Expert A", "content": "I think X is best.", "turn": 1}
    ]

    result = await consensus_detector.analyze_messages(messages)

    # Single message cannot establish consensus
    assert result.consensus_reached is False or result.confidence < 0.5


@pytest.mark.asyncio
async def test_consensus_similarity_scoring(consensus_detector):
    """Test semantic similarity scoring between messages"""
    msg1 = "The best approach is to use microservices architecture."
    msg2 = "I agree, microservices is the optimal architectural pattern."
    msg3 = "We should definitely go with a completely different approach."

    similarity_1_2 = await consensus_detector.calculate_similarity(msg1, msg2)
    similarity_1_3 = await consensus_detector.calculate_similarity(msg1, msg3)

    # Similar messages should have higher similarity score
    assert similarity_1_2 > similarity_1_3
    assert similarity_1_2 > 0.5


@pytest.mark.asyncio
async def test_consensus_with_explicit_agreement_keywords(consensus_detector):
    """Test detection of explicit agreement keywords"""
    messages = [
        {"role": "Expert A", "content": "Option A is best.", "turn": 2},
        {"role": "Expert B", "content": "I agree with Expert A.", "turn": 2},
        {"role": "Expert C", "content": "I concur. Option A is optimal.", "turn": 2}
    ]

    result = await consensus_detector.analyze_messages(messages)

    # Explicit agreement should boost confidence
    assert result.consensus_reached is True
    assert result.confidence > 0.7


@pytest.mark.asyncio
async def test_consensus_with_explicit_disagreement_keywords(consensus_detector):
    """Test detection of explicit disagreement keywords"""
    messages = [
        {"role": "Expert A", "content": "Option A is best.", "turn": 2},
        {"role": "Expert B", "content": "I disagree. Option B is better.", "turn": 2},
        {"role": "Expert C", "content": "I must oppose this. Option C is superior.", "turn": 2}
    ]

    result = await consensus_detector.analyze_messages(messages)

    # Explicit disagreement should reduce confidence
    assert result.consensus_reached is False
    assert result.confidence < 0.5


@pytest.mark.asyncio
async def test_consensus_summary_generation(consensus_detector, agreement_messages):
    """Test that consensus summary is meaningful"""
    result = await consensus_detector.analyze_messages(agreement_messages)

    assert result.summary is not None
    assert len(result.summary) > 0

    # Summary should mention key points
    summary_lower = result.summary.lower()
    assert any(keyword in summary_lower for keyword in ["option", "agree", "expert"])


@pytest.mark.asyncio
async def test_consensus_confidence_range(consensus_detector, agreement_messages):
    """Test that confidence score is within valid range"""
    result = await consensus_detector.analyze_messages(agreement_messages)

    assert 0.0 <= result.confidence <= 1.0


@pytest.mark.asyncio
async def test_consensus_with_mixed_turns(consensus_detector):
    """Test consensus detection across multiple turns"""
    messages = [
        {"role": "Expert A", "content": "I suggest option X.", "turn": 1},
        {"role": "Expert B", "content": "What about option Y?", "turn": 1},
        {"role": "Expert A", "content": "After consideration, option Y is better.", "turn": 2},
        {"role": "Expert C", "content": "I also agree option Y is best.", "turn": 2},
        {"role": "Expert B", "content": "Great, we all agree on option Y.", "turn": 3}
    ]

    result = await consensus_detector.analyze_messages(messages)

    # Should detect eventual consensus despite initial disagreement
    assert result.consensus_reached is True


@pytest.mark.asyncio
async def test_consensus_ignores_old_messages(consensus_detector):
    """Test that consensus focuses on recent messages"""
    messages = [
        {"role": "Expert A", "content": "I think X is best.", "turn": 1},
        {"role": "Expert B", "content": "No, Y is better.", "turn": 1},
        # Gap in turns...
        {"role": "Expert A", "content": "Actually, Z is optimal.", "turn": 10},
        {"role": "Expert B", "content": "I agree, Z is the best choice.", "turn": 10},
        {"role": "Expert C", "content": "Yes, Z is clearly superior.", "turn": 10}
    ]

    result = await consensus_detector.analyze_messages(messages)

    # Should detect consensus based on recent messages
    assert result.consensus_reached is True
    assert "z" in result.summary.lower()


@pytest.mark.asyncio
async def test_consensus_with_empty_messages(consensus_detector):
    """Test handling of empty message list"""
    messages = []

    result = await consensus_detector.analyze_messages(messages)

    assert result.consensus_reached is False
    assert result.confidence == 0.0


@pytest.mark.asyncio
async def test_consensus_threshold_configuration(consensus_detector):
    """Test that consensus threshold can be configured"""
    messages = [
        {"role": "Expert A", "content": "Option X is good.", "turn": 1},
        {"role": "Expert B", "content": "Option X is acceptable.", "turn": 1}
    ]

    # Test with high threshold
    result_high = await consensus_detector.analyze_messages(
        messages,
        threshold=0.9
    )

    # Test with low threshold
    result_low = await consensus_detector.analyze_messages(
        messages,
        threshold=0.5
    )

    # Higher threshold should be harder to reach
    if result_high.consensus_reached:
        assert result_low.consensus_reached


@pytest.mark.asyncio
async def test_consensus_with_llm_analysis(consensus_detector, agreement_messages):
    """Test consensus detection using LLM analysis"""
    with patch.object(consensus_detector, 'llm_provider') as mock_llm:
        mock_llm.chat_completion = AsyncMock(return_value={
            "consensus_reached": True,
            "confidence": 0.92,
            "summary": "All experts agree that option X is the optimal choice.",
            "reasoning": "Strong semantic agreement and explicit consensus keywords."
        })

        result = await consensus_detector.analyze_messages(agreement_messages)

        assert result.consensus_reached is True
        assert result.confidence > 0.9
        mock_llm.chat_completion.assert_called_once()


@pytest.mark.asyncio
async def test_consensus_reasoning_included(consensus_detector, agreement_messages):
    """Test that consensus result includes reasoning"""
    result = await consensus_detector.analyze_messages(agreement_messages)

    assert hasattr(result, 'reasoning')
    if result.reasoning:
        assert len(result.reasoning) > 0


@pytest.mark.asyncio
async def test_consensus_with_mention_chains(consensus_detector):
    """Test consensus detection with agent mentions"""
    messages = [
        {"role": "Expert A", "content": "I think option X is best.", "turn": 1},
        {"role": "Expert B", "content": "@Expert A I agree with your assessment of option X.", "turn": 1},
        {"role": "Expert C", "content": "@Expert B @Expert A I also support option X.", "turn": 2}
    ]

    result = await consensus_detector.analyze_messages(messages)

    # Mention chains should indicate consensus
    assert result.consensus_reached is True


@pytest.mark.asyncio
async def test_consensus_with_numerical_agreement(consensus_detector):
    """Test consensus on numerical values"""
    messages = [
        {"role": "Expert A", "content": "The optimal value is approximately 42.", "turn": 1},
        {"role": "Expert B", "content": "I calculated 41.5, very close to 42.", "turn": 1},
        {"role": "Expert C", "content": "My analysis also yields around 42.", "turn": 1}
    ]

    result = await consensus_detector.analyze_messages(messages)

    # Should detect consensus on similar numerical values
    assert result.consensus_reached is True


@pytest.mark.asyncio
async def test_consensus_divergence_detection(consensus_detector):
    """Test detection of consensus breaking down"""
    messages = [
        {"role": "Expert A", "content": "Option X is best.", "turn": 1},
        {"role": "Expert B", "content": "I agree, option X.", "turn": 1},
        {"role": "Expert C", "content": "Yes, option X.", "turn": 1},
        # Then divergence
        {"role": "Expert B", "content": "Wait, I reconsider. Option Y might be better.", "turn": 2},
        {"role": "Expert A", "content": "I still think X is optimal.", "turn": 2}
    ]

    # Analyze early messages
    result_early = await consensus_detector.analyze_messages(messages[:3])

    # Analyze all messages including divergence
    result_all = await consensus_detector.analyze_messages(messages)

    # Confidence should decrease with divergence
    if result_early.consensus_reached:
        assert result_all.confidence < result_early.confidence


def test_consensus_result_dataclass():
    """Test ConsensusResult dataclass structure"""
    result = ConsensusResult(
        consensus_reached=True,
        confidence=0.85,
        summary="Test summary",
        reasoning="Test reasoning"
    )

    assert result.consensus_reached is True
    assert result.confidence == 0.85
    assert result.summary == "Test summary"
    assert result.reasoning == "Test reasoning"


@pytest.mark.asyncio
async def test_consensus_performance_with_many_messages(consensus_detector):
    """Test consensus detection performance with large message count"""
    # Create 100 messages
    messages = [
        {"role": f"Expert {i % 3}", "content": f"Message {i} about option X", "turn": i // 3}
        for i in range(100)
    ]

    import time
    start = time.time()
    result = await consensus_detector.analyze_messages(messages)
    duration = time.time() - start

    # Should complete reasonably fast (< 5 seconds)
    assert duration < 5.0
    assert result is not None
