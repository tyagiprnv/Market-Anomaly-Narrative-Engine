"""Example usage of Phase 2 agent tools.

This script demonstrates how to use each of the 5 journalist agent tools
to analyze market anomalies and generate narratives.
"""

import asyncio
from datetime import datetime, timedelta
from sqlalchemy.orm import Session

from src.phase2_journalist.tools import (
    VerifyTimestampTool,
    SentimentCheckTool,
    SearchHistoricalTool,
    CheckMarketContextTool,
    CheckSocialSentimentTool,
    ToolRegistry,
    get_all_tool_definitions,
)
from src.database.connection import get_db_session


async def example_verify_timestamp():
    """Example: Verify if news timing is consistent with causality."""
    print("\n" + "=" * 70)
    print("EXAMPLE 1: Verify Timestamp Tool")
    print("=" * 70)

    tool = VerifyTimestampTool()

    # Scenario 1: News before anomaly (causal)
    news_time = datetime(2024, 1, 15, 14, 5, 0)
    anomaly_time = datetime(2024, 1, 15, 14, 10, 0)

    result = await tool.execute(
        news_timestamp=news_time, anomaly_timestamp=anomaly_time, threshold_minutes=30
    )

    print(f"\nScenario 1: News at {news_time}, Anomaly at {anomaly_time}")
    print(f"  Success: {result.success}")
    print(f"  Is Causal: {result.is_causal}")
    print(f"  Timing Tag: {result.timing_tag}")
    print(f"  Time Difference: {result.time_diff_minutes} minutes")

    # Scenario 2: News after anomaly (not causal)
    news_time2 = datetime(2024, 1, 15, 14, 20, 0)

    result2 = await tool.execute(
        news_timestamp=news_time2, anomaly_timestamp=anomaly_time
    )

    print(f"\nScenario 2: News at {news_time2}, Anomaly at {anomaly_time}")
    print(f"  Is Causal: {result2.is_causal}")
    print(f"  Timing Tag: {result2.timing_tag}")
    print(f"  Time Difference: {result2.time_diff_minutes} minutes")


async def example_sentiment_check():
    """Example: Analyze sentiment of financial text."""
    print("\n" + "=" * 70)
    print("EXAMPLE 2: Sentiment Check Tool (FinBERT)")
    print("=" * 70)

    tool = SentimentCheckTool()

    # Example news headlines
    bullish_headlines = [
        "Bitcoin rallies to new all-time high as institutional adoption grows",
        "Ethereum ETF approval boosts crypto market confidence",
        "Major tech companies announce blockchain integration plans",
    ]

    bearish_headlines = [
        "Bitcoin crashes 10% amid regulatory crackdown fears",
        "Crypto market sees $200B wiped out in flash crash",
        "Major exchange security breach raises concerns",
    ]

    print("\n--- Bullish Headlines ---")
    result1 = await tool.execute(texts=bullish_headlines)
    if result1.success:
        print(f"Average Sentiment: {result1.average_sentiment:.2f}")
        print(f"Dominant Label: {result1.dominant_label}")
        print(f"Individual Scores: {[f'{s:.2f}' for s in result1.sentiments]}")

    print("\n--- Bearish Headlines ---")
    result2 = await tool.execute(texts=bearish_headlines)
    if result2.success:
        print(f"Average Sentiment: {result2.average_sentiment:.2f}")
        print(f"Dominant Label: {result2.dominant_label}")
        print(f"Individual Scores: {[f'{s:.2f}' for s in result2.sentiments]}")


async def example_search_historical(session: Session):
    """Example: Search for similar historical anomalies."""
    print("\n" + "=" * 70)
    print("EXAMPLE 3: Search Historical Tool")
    print("=" * 70)

    tool = SearchHistoricalTool(session=session)

    # Search for similar BTC price drops
    result = await tool.execute(
        symbol="BTC-USD", anomaly_type="price_drop", min_similarity=0.7, limit=5
    )

    print(f"\nSearching for similar BTC-USD price drops...")
    print(f"Success: {result.success}")
    print(f"Results Found: {result.count}")

    if result.results:
        print("\nSimilar Historical Anomalies:")
        for i, anomaly in enumerate(result.results[:3], 1):
            print(f"\n{i}. {anomaly.symbol} ({anomaly.detected_at.strftime('%Y-%m-%d %H:%M')})")
            print(f"   Type: {anomaly.anomaly_type}")
            print(f"   Change: {anomaly.price_change_pct:.2f}%")
            print(f"   Similarity: {anomaly.similarity_score:.2f}")
            if anomaly.narrative_text:
                print(f"   Narrative: {anomaly.narrative_text[:100]}...")
    else:
        print("No historical anomalies found (database may be empty)")


async def example_market_context(session: Session):
    """Example: Check if anomaly is market-wide or isolated."""
    print("\n" + "=" * 70)
    print("EXAMPLE 4: Check Market Context Tool")
    print("=" * 70)

    tool = CheckMarketContextTool(session=session)

    # Check market context for SOL anomaly
    result = await tool.execute(
        target_symbol="SOL-USD",
        reference_symbols=["BTC-USD", "ETH-USD"],
        timestamp=datetime.now(),
        window_minutes=10,
    )

    print(f"\nChecking market context for SOL-USD...")
    print(f"Success: {result.success}")

    if result.target_context:
        print(f"\nTarget Symbol: {result.target_context.symbol}")
        print(f"  Price Change: {result.target_context.price_change_pct}%")
        print(f"  Is Moving: {result.target_context.is_moving}")
        print(f"  Direction: {result.target_context.direction}")

    print(f"\nMarket-Wide Movement: {result.is_market_wide}")
    print(f"Description: {result.correlation_description}")


async def example_social_sentiment():
    """Example: Analyze social sentiment from news articles."""
    print("\n" + "=" * 70)
    print("EXAMPLE 5: Check Social Sentiment Tool")
    print("=" * 70)

    tool = CheckSocialSentimentTool()

    # Example social media posts and news
    articles = [
        "Bitcoin reaches new milestone as adoption accelerates worldwide",
        "Community excitement grows over upcoming Bitcoin halving event",
        "Major banks announce Bitcoin custody services",
        "Concerns raised about Bitcoin energy consumption",
        "Bitcoin price volatility continues to worry investors",
    ]

    result = await tool.execute(symbol="BTC-USD", news_articles=articles)

    print(f"\nAnalyzing social sentiment for BTC-USD...")
    print(f"Success: {result.success}")

    if result.success:
        print(f"\nArticles Analyzed: {result.article_count}")
        print(f"Average Sentiment: {result.average_sentiment:.2f}")
        print(f"Sentiment Label: {result.sentiment_label}")
        print(f"\nSentiment Distribution:")
        for label, count in result.sentiment_distribution.items():
            print(f"  {label.capitalize()}: {count}")


async def example_tool_registry(session: Session):
    """Example: Using the ToolRegistry for centralized access."""
    print("\n" + "=" * 70)
    print("EXAMPLE 6: Tool Registry")
    print("=" * 70)

    # Initialize registry with database session
    registry = ToolRegistry(session=session)

    print(f"\nRegistered Tools: {', '.join(registry.get_tool_names())}")

    # Get tool definitions for LLM function calling
    tool_defs = registry.get_all_tool_definitions()
    print(f"\nTotal Tool Definitions: {len(tool_defs)}")
    print("\nTool Definitions for LLM:")
    for tool_def in tool_defs:
        func = tool_def["function"]
        print(f"  - {func['name']}: {func['description'][:60]}...")

    # Execute a tool through registry
    print("\n--- Executing Tool via Registry ---")
    result = await registry.execute_tool(
        "verify_timestamp",
        news_timestamp=datetime.now() - timedelta(minutes=5),
        anomaly_timestamp=datetime.now(),
    )
    print(f"Executed verify_timestamp: success={result.success}")


async def example_llm_integration(session: Session):
    """Example: How tools integrate with LLM agents."""
    print("\n" + "=" * 70)
    print("EXAMPLE 7: LLM Integration")
    print("=" * 70)

    # Get tool definitions for LLM
    tool_definitions = get_all_tool_definitions(session=session)

    print("\nTool definitions ready for LLM function calling:")
    print(f"Format: OpenAI/Anthropic function calling schema")
    print(f"Number of tools: {len(tool_definitions)}")

    # Example: This is how you'd pass tools to LLM
    print("\n--- Example LLM Integration Code ---")
    print("""
from src.llm import LLMClient, LLMMessage, LLMRole
from src.phase2_journalist.tools import get_all_tool_definitions

# Initialize LLM client
client = LLMClient()

# Get tool definitions
tools = get_all_tool_definitions(session=db_session)

# Create messages
messages = [
    LLMMessage(role=LLMRole.SYSTEM, content="You are a crypto analyst."),
    LLMMessage(role=LLMRole.USER, content="Analyze this BTC anomaly...")
]

# Call LLM with tools
response = await client.chat_completion(
    messages=messages,
    tools=tools,
    tool_choice="auto"
)

# LLM will decide which tools to call based on the context
if response.tool_calls:
    for tool_call in response.tool_calls:
        print(f"LLM wants to call: {tool_call.function['name']}")
    """)


async def main():
    """Run all examples."""
    print("\n" + "=" * 70)
    print("PHASE 2: AGENT TOOLS - USAGE EXAMPLES")
    print("=" * 70)

    # Examples that don't need database
    await example_verify_timestamp()

    print("\n\n[NOTE] Skipping sentiment examples (requires transformers library)")
    print("To run sentiment examples, install: pip install transformers torch")
    # await example_sentiment_check()
    # await example_social_sentiment()

    # Examples that need database session
    try:
        with get_db_session() as session:
            await example_search_historical(session)
            await example_market_context(session)
            await example_tool_registry(session)
            await example_llm_integration(session)
    except Exception as e:
        print(f"\n[NOTE] Database examples skipped (database not configured): {e}")
        print("To run database examples, configure PostgreSQL and run migrations.")

    print("\n" + "=" * 70)
    print("EXAMPLES COMPLETE")
    print("=" * 70)
    print("\nFor more information, see:")
    print("  - /src/phase2_journalist/tools/ - Tool implementations")
    print("  - /tests/unit/phase2/test_agent_tools.py - Unit tests")
    print("  - /docs/API.md - API documentation")


if __name__ == "__main__":
    asyncio.run(main())
