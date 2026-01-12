"""Unit tests for Phase 2 Journalist Agent."""

import json
from datetime import datetime, timezone
from unittest.mock import AsyncMock, Mock

import pytest

from src.database.models import Anomaly, AnomalyTypeEnum, NewsArticle
from src.llm import LLMClient
from src.llm.models import LLMMessage, LLMResponse, LLMRole, TokenUsage, ToolCall
from src.phase2_journalist.agent import JournalistAgent
from src.phase2_journalist.tools import ToolRegistry


@pytest.fixture
def mock_llm_client():
    """Create a mock LLM client."""
    client = AsyncMock(spec=LLMClient)
    client.provider = "anthropic"
    client.model = "claude-3-5-haiku-20241022"
    return client


@pytest.fixture
def mock_tool_registry():
    """Create a mock tool registry."""
    registry = Mock(spec=ToolRegistry)
    registry.get_all_tool_definitions = Mock(
        return_value=[
            {
                "type": "function",
                "function": {
                    "name": "verify_timestamp",
                    "description": "Verify news timing",
                    "parameters": {"type": "object", "properties": {}},
                },
            }
        ]
    )
    return registry


@pytest.fixture
def mock_db_session():
    """Create a mock database session."""
    session = Mock()
    session.add = Mock()
    session.commit = Mock()
    session.refresh = Mock()
    return session


@pytest.fixture
def test_anomaly():
    """Create a test anomaly."""
    return Anomaly(
        id="test-anomaly-123",
        symbol="BTC-USD",
        detected_at=datetime(2024, 1, 15, 14, 15, 0, tzinfo=timezone.utc),
        anomaly_type=AnomalyTypeEnum.PRICE_DROP,
        z_score=-3.5,
        price_change_pct=-5.2,
        volume_change_pct=120.5,
        confidence=0.95,
        baseline_window_minutes=60,
        price_before=45000.0,
        price_at_detection=42660.0,
        volume_before=1000.0,
        volume_at_detection=2205.0,
    )


@pytest.fixture
def test_news_articles():
    """Create test news articles."""
    return [
        NewsArticle(
            id="news-1",
            anomaly_id="test-anomaly-123",
            source="cryptopanic",
            title="SEC announces stricter cryptocurrency regulations",
            url="https://example.com/news1",
            published_at=datetime(2024, 1, 15, 14, 0, 0, tzinfo=timezone.utc),
            timing_tag="pre_event",
            time_diff_minutes=-15,
        ),
        NewsArticle(
            id="news-2",
            anomaly_id="test-anomaly-123",
            source="reddit",
            title="Bitcoin plummets on regulatory news",
            url="https://reddit.com/r/crypto/123",
            published_at=datetime(2024, 1, 15, 14, 20, 0, tzinfo=timezone.utc),
            timing_tag="post_event",
            time_diff_minutes=5,
        ),
    ]


@pytest.mark.asyncio
async def test_generate_narrative_with_tools(
    mock_llm_client, mock_tool_registry, mock_db_session, test_anomaly, test_news_articles
):
    """Test successful narrative generation with tool usage."""
    # Mock LLM responses
    mock_llm_client.chat_completion.side_effect = [
        # First call: LLM wants to use verify_timestamp
        LLMResponse(
            finish_reason="tool_calls",
            tool_calls=[
                ToolCall(
                    id="call_1",
                    type="function",
                    function={
                        "name": "verify_timestamp",
                        "arguments": json.dumps(
                            {
                                "news_timestamp": "2024-01-15T14:00:00Z",
                                "anomaly_timestamp": "2024-01-15T14:15:00Z",
                            }
                        ),
                    },
                )
            ],
            content=None,
            usage=TokenUsage(prompt_tokens=100, completion_tokens=20, total_tokens=120),
            role=LLMRole.ASSISTANT,
            model="claude-3-5-haiku-20241022",
            id="msg_1",
            created_at=datetime.now(timezone.utc),
        ),
        # Second call: LLM generates narrative
        LLMResponse(
            finish_reason="stop",
            content="Bitcoin dropped 5.2% following SEC announcement of stricter cryptocurrency regulations. The negative sentiment amplified the sell-off.",
            tool_calls=None,
            usage=TokenUsage(prompt_tokens=200, completion_tokens=30, total_tokens=230),
            role=LLMRole.ASSISTANT,
            model="claude-3-5-haiku-20241022",
            id="msg_2",
            created_at=datetime.now(timezone.utc),
        ),
    ]

    # Mock tool execution
    mock_tool_registry.execute_tool = AsyncMock(
        return_value={
            "success": True,
            "is_causal": True,
            "time_diff_minutes": -15,
            "timing_tag": "pre_event",
        }
    )

    # Create agent
    agent = JournalistAgent(
        llm_client=mock_llm_client,
        tool_registry=mock_tool_registry,
        session=mock_db_session,
    )

    # Generate narrative
    narrative = await agent.generate_narrative(test_anomaly, test_news_articles)

    # Assertions
    assert narrative is not None
    assert "Bitcoin" in narrative.narrative_text or "BTC" in narrative.narrative_text
    assert narrative.llm_provider == "anthropic"
    assert narrative.llm_model == "claude-3-5-haiku-20241022"
    assert len(narrative.tools_used) == 1
    assert "verify_timestamp" in narrative.tools_used
    assert narrative.validated is False
    assert narrative.generation_time_seconds > 0

    # Verify tool was executed
    mock_tool_registry.execute_tool.assert_called_once()

    # Verify database operations
    mock_db_session.add.assert_called_once()
    mock_db_session.commit.assert_called_once()
    mock_db_session.refresh.assert_called_once()


@pytest.mark.asyncio
async def test_generate_narrative_without_tools(
    mock_llm_client, mock_tool_registry, mock_db_session, test_anomaly
):
    """Test narrative generation without using any tools."""
    # Mock LLM response: immediate narrative without tools
    mock_llm_client.chat_completion.side_effect = [
        LLMResponse(
            finish_reason="stop",
            content="Bitcoin experienced a 5.2% price drop. Cause unknown due to insufficient evidence.",
            tool_calls=None,
            usage=TokenUsage(prompt_tokens=150, completion_tokens=20, total_tokens=170),
            role=LLMRole.ASSISTANT,
            model="claude-3-5-haiku-20241022",
            id="msg_1",
            created_at=datetime.now(timezone.utc),
        )
    ]

    # Create agent
    agent = JournalistAgent(
        llm_client=mock_llm_client,
        tool_registry=mock_tool_registry,
        session=mock_db_session,
    )

    # Generate narrative (no news articles)
    narrative = await agent.generate_narrative(test_anomaly, [])

    # Assertions
    assert narrative is not None
    assert "Bitcoin" in narrative.narrative_text or "BTC" in narrative.narrative_text
    assert len(narrative.tools_used) == 0
    assert narrative.tool_results == {}
    assert narrative.validated is False

    # Verify no tools were executed
    mock_tool_registry.execute_tool.assert_not_called()


@pytest.mark.asyncio
async def test_generate_narrative_fallback_on_error(
    mock_llm_client, mock_tool_registry, mock_db_session, test_anomaly
):
    """Test fallback narrative generation when LLM fails."""
    # Mock LLM to raise an error
    mock_llm_client.chat_completion.side_effect = Exception("API Error: Rate limit exceeded")

    # Create agent
    agent = JournalistAgent(
        llm_client=mock_llm_client,
        tool_registry=mock_tool_registry,
        session=mock_db_session,
    )

    # Generate narrative (should fallback)
    narrative = await agent.generate_narrative(test_anomaly, [])

    # Assertions
    assert narrative is not None
    assert "Cause unknown" in narrative.narrative_text
    assert "BTC-USD" in narrative.narrative_text
    assert "-5.2%" in narrative.narrative_text or "5.2%" in narrative.narrative_text or "5.20%" in narrative.narrative_text
    assert len(narrative.tools_used) == 0
    assert "error" in narrative.tool_results
    assert narrative.tool_results.get("fallback") is True


@pytest.mark.asyncio
async def test_max_iterations_exceeded(
    mock_llm_client, mock_tool_registry, mock_db_session, test_anomaly
):
    """Test that agent fails after max iterations."""
    # Mock LLM to always return tool_calls (infinite loop)
    mock_llm_client.chat_completion.return_value = LLMResponse(
        finish_reason="tool_calls",
        tool_calls=[
            ToolCall(
                id="call_1",
                type="function",
                function={"name": "verify_timestamp", "arguments": "{}"},
            )
        ],
        content=None,
        usage=TokenUsage(prompt_tokens=100, completion_tokens=20, total_tokens=120),
        role=LLMRole.ASSISTANT,
        model="claude-3-5-haiku-20241022",
        id="msg_1",
        created_at=datetime.now(timezone.utc),
    )

    # Mock tool execution
    mock_tool_registry.execute_tool = AsyncMock(return_value={"success": True})

    # Create agent with low max iterations
    agent = JournalistAgent(
        llm_client=mock_llm_client,
        tool_registry=mock_tool_registry,
        session=mock_db_session,
        max_tool_iterations=3,
    )

    # Generate narrative (should create fallback)
    narrative = await agent.generate_narrative(test_anomaly, [])

    # Should generate fallback narrative
    assert narrative is not None
    assert "Cause unknown" in narrative.narrative_text


@pytest.mark.asyncio
async def test_empty_news_articles(
    mock_llm_client, mock_tool_registry, mock_db_session, test_anomaly
):
    """Test narrative generation with no news articles."""
    # Mock LLM response
    mock_llm_client.chat_completion.side_effect = [
        LLMResponse(
            finish_reason="stop",
            content="Bitcoin experienced a 5.2% price decrease. Cause unknown.",
            tool_calls=None,
            usage=TokenUsage(prompt_tokens=100, completion_tokens=15, total_tokens=115),
            role=LLMRole.ASSISTANT,
            model="claude-3-5-haiku-20241022",
            id="msg_1",
            created_at=datetime.now(timezone.utc),
        )
    ]

    # Create agent
    agent = JournalistAgent(
        llm_client=mock_llm_client,
        tool_registry=mock_tool_registry,
        session=mock_db_session,
    )

    # Generate narrative with empty news list
    narrative = await agent.generate_narrative(test_anomaly, [])

    # Should still generate narrative
    assert narrative is not None
    assert len(narrative.narrative_text) > 0


@pytest.mark.asyncio
async def test_tool_execution_error_handling(
    mock_llm_client, mock_tool_registry, mock_db_session, test_anomaly
):
    """Test that tool execution errors are handled gracefully."""
    # Mock LLM responses
    mock_llm_client.chat_completion.side_effect = [
        # First call: LLM wants to use a tool
        LLMResponse(
            finish_reason="tool_calls",
            tool_calls=[
                ToolCall(
                    id="call_1",
                    type="function",
                    function={"name": "verify_timestamp", "arguments": "{}"},
                )
            ],
            content=None,
            usage=TokenUsage(prompt_tokens=100, completion_tokens=20, total_tokens=120),
            role=LLMRole.ASSISTANT,
            model="claude-3-5-haiku-20241022",
            id="msg_1",
            created_at=datetime.now(timezone.utc),
        ),
        # Second call: LLM generates narrative despite tool error
        LLMResponse(
            finish_reason="stop",
            content="Bitcoin dropped 5.2% due to market volatility. Specific cause could not be determined.",
            tool_calls=None,
            usage=TokenUsage(prompt_tokens=150, completion_tokens=20, total_tokens=170),
            role=LLMRole.ASSISTANT,
            model="claude-3-5-haiku-20241022",
            id="msg_2",
            created_at=datetime.now(timezone.utc),
        ),
    ]

    # Mock tool to raise exception
    mock_tool_registry.execute_tool = AsyncMock(
        side_effect=Exception("Tool execution failed")
    )

    # Create agent
    agent = JournalistAgent(
        llm_client=mock_llm_client,
        tool_registry=mock_tool_registry,
        session=mock_db_session,
    )

    # Generate narrative (should handle tool error)
    narrative = await agent.generate_narrative(test_anomaly, [])

    # Should still generate narrative
    assert narrative is not None
    assert len(narrative.narrative_text) > 0
    assert "verify_timestamp" in narrative.tools_used

    # Tool results should contain error info
    assert "verify_timestamp" in narrative.tool_results
    tool_result = narrative.tool_results["verify_timestamp"][0]
    assert tool_result["success"] is False
    assert "error" in tool_result["result"]


@pytest.mark.asyncio
async def test_multiple_tool_calls_in_one_iteration(
    mock_llm_client, mock_tool_registry, mock_db_session, test_anomaly
):
    """Test handling multiple tool calls in a single iteration."""
    # Mock LLM responses
    mock_llm_client.chat_completion.side_effect = [
        # First call: LLM wants to use two tools
        LLMResponse(
            finish_reason="tool_calls",
            tool_calls=[
                ToolCall(
                    id="call_1",
                    type="function",
                    function={"name": "verify_timestamp", "arguments": "{}"},
                ),
                ToolCall(
                    id="call_2",
                    type="function",
                    function={"name": "sentiment_check", "arguments": '{"texts": ["test"]}'},
                ),
            ],
            content=None,
            usage=TokenUsage(prompt_tokens=100, completion_tokens=30, total_tokens=130),
            role=LLMRole.ASSISTANT,
            model="claude-3-5-haiku-20241022",
            id="msg_1",
            created_at=datetime.now(timezone.utc),
        ),
        # Second call: Generate narrative
        LLMResponse(
            finish_reason="stop",
            content="Bitcoin dropped 5.2% following negative news sentiment. Market reaction was swift.",
            tool_calls=None,
            usage=TokenUsage(prompt_tokens=200, completion_tokens=25, total_tokens=225),
            role=LLMRole.ASSISTANT,
            model="claude-3-5-haiku-20241022",
            id="msg_2",
            created_at=datetime.now(timezone.utc),
        ),
    ]

    # Mock tool execution
    mock_tool_registry.execute_tool = AsyncMock(
        side_effect=[
            {"success": True, "is_causal": True},
            {"success": True, "average_sentiment": -0.7},
        ]
    )

    # Create agent
    agent = JournalistAgent(
        llm_client=mock_llm_client,
        tool_registry=mock_tool_registry,
        session=mock_db_session,
    )

    # Generate narrative
    narrative = await agent.generate_narrative(test_anomaly, [])

    # Assertions
    assert narrative is not None
    assert len(narrative.tools_used) == 2
    assert "verify_timestamp" in narrative.tools_used
    assert "sentiment_check" in narrative.tools_used

    # Verify both tools were executed
    assert mock_tool_registry.execute_tool.call_count == 2


def test_fallback_narrative_format(test_anomaly):
    """Test fallback narrative has correct format."""
    agent = JournalistAgent(
        llm_client=Mock(spec=LLMClient),
        tool_registry=Mock(spec=ToolRegistry),
        session=Mock(),
    )

    error = Exception("Test error")
    fallback = agent._create_fallback_narrative(test_anomaly, error)

    # Check format
    assert "BTC-USD" in fallback
    assert "5.20%" in fallback or "5.2%" in fallback
    assert "decrease" in fallback
    assert "Cause unknown" in fallback
    assert "2024-01-15" in fallback


def test_build_metadata():
    """Test metadata aggregation."""
    agent = JournalistAgent(
        llm_client=Mock(spec=LLMClient),
        tool_registry=Mock(spec=ToolRegistry),
        session=Mock(),
    )

    response = LLMResponse(
        finish_reason="stop",
        content="Test narrative",
        tool_calls=None,
        usage=TokenUsage(prompt_tokens=100, completion_tokens=50, total_tokens=150),
        role=LLMRole.ASSISTANT,
        model="test-model",
        id="msg_1",
        created_at=datetime.now(timezone.utc),
    )

    tool_executions = [
        {
            "tool_name": "verify_timestamp",
            "arguments": {},
            "result": {"success": True},
            "success": True,
        },
        {
            "tool_name": "sentiment_check",
            "arguments": {},
            "result": {"success": True},
            "success": True,
        },
    ]

    metadata = agent._build_metadata(response, tool_executions, 1.5)

    # Check metadata
    assert set(metadata["tools_used"]) == {"verify_timestamp", "sentiment_check"}
    assert "verify_timestamp" in metadata["tool_results"]
    assert "sentiment_check" in metadata["tool_results"]
    assert metadata["generation_time"] == 1.5
    assert metadata["token_usage"]["total_tokens"] == 150
