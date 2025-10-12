#!/usr/bin/env python3
"""
Manual Testing Script for CAMEL Discussion Engine

Usage:
    python scripts/test_discussion.py --topic "Best treatment for chronic migraine" --num-agents 3
"""
import asyncio
import sys
import argparse
import os
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
from loguru import logger

from src.camel_engine.orchestrator import DiscussionOrchestrator


async def test_discussion(
    topic: str,
    num_agents: int = 3,
    max_turns: int = 10
):
    """
    Test a complete discussion

    Args:
        topic: Discussion topic
        num_agents: Number of expert agents
        max_turns: Maximum turns to run
    """
    # Load environment
    load_dotenv()

    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        logger.error("OPENROUTER_API_KEY not found in environment")
        print("\n❌ Error: OPENROUTER_API_KEY not set")
        print("Please create .env file with your OpenRouter API key")
        return

    logger.info("=" * 80)
    logger.info(f"CAMEL DISCUSSION ENGINE - Test Run")
    logger.info("=" * 80)
    logger.info(f"Topic: {topic}")
    logger.info(f"Agents: {num_agents}")
    logger.info(f"Max Turns: {max_turns}")
    logger.info("=" * 80)

    # Create orchestrator
    orchestrator = DiscussionOrchestrator(
        openrouter_api_key=api_key,
        max_turns=max_turns
    )

    try:
        # Create discussion
        print("\n🔧 Creating discussion...")
        discussion_id = await orchestrator.create_discussion(
            topic=topic,
            num_agents=num_agents
        )
        print(f"✅ Discussion created: {discussion_id[:8]}")

        # Get discussion details
        discussion = orchestrator.get_discussion(discussion_id)
        print(f"\n👥 Participants:")
        for role in discussion.roles:
            print(f"  - {role.name} ({role.model})")
            print(f"    Expertise: {role.expertise}")

        # Run discussion
        print(f"\n🎯 Starting discussion...")
        print("-" * 80)

        result = await orchestrator.run_discussion(discussion_id, max_turns=max_turns)

        # Display results
        print("-" * 80)
        print(f"\n📊 Discussion Results")
        print("=" * 80)

        print(f"\n**Status**: {'✅ Consensus Reached' if result.consensus_reached else '⚠️ No Consensus'}")
        print(f"**Confidence**: {result.consensus_confidence:.1%}")
        print(f"**Total Turns**: {result.total_turns}")
        print(f"**Duration**: {result.duration_seconds:.1f} seconds")

        print(f"\n**Key Agreements**:")
        if result.key_agreements:
            for agreement in result.key_agreements:
                print(f"  ✓ {agreement}")
        else:
            print("  (none)")

        print(f"\n**Disagreements**:")
        if result.disagreements:
            for disagreement in result.disagreements:
                print(f"  ✗ {disagreement}")
        else:
            print("  (none)")

        print(f"\n**Final Summary**:")
        print("-" * 80)
        print(result.final_summary)
        print("-" * 80)

        print(f"\n**Full Conversation** ({len(result.messages)} messages):")
        print("=" * 80)
        for msg in result.messages:
            if msg.role_name == "System":
                print(f"\n[{msg.role_name}] {msg.content}\n")
            else:
                print(f"\n**Turn {msg.turn_number} - {msg.role_name}** ({msg.model}):")
                print(f"{msg.content}")
                print()

        print("=" * 80)
        print("✅ Test completed successfully!")

    except Exception as e:
        logger.exception("Test failed")
        print(f"\n❌ Error: {str(e)}")
        raise


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="Test CAMEL Discussion Engine",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python scripts/test_discussion.py --topic "Best migraine treatment" --num-agents 3
  python scripts/test_discussion.py --topic "Design microservices for e-commerce" --num-agents 4 --max-turns 15
        """
    )

    parser.add_argument(
        "--topic",
        type=str,
        required=True,
        help="Discussion topic"
    )

    parser.add_argument(
        "--num-agents",
        type=int,
        default=3,
        help="Number of expert agents (default: 3)"
    )

    parser.add_argument(
        "--max-turns",
        type=int,
        default=10,
        help="Maximum discussion turns (default: 10)"
    )

    args = parser.parse_args()

    # Run test
    asyncio.run(test_discussion(
        topic=args.topic,
        num_agents=args.num_agents,
        max_turns=args.max_turns
    ))


if __name__ == "__main__":
    main()
