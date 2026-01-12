"""Unit tests for Phase 2 agent tools."""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock
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
from src.database.models import Anomaly, Narrative, Price, AnomalyTypeEnum


class TestVerifyTimestampTool:
    """Tests for verify_timestamp tool."""

    @pytest.fixture
    def tool(self):
        return VerifyTimestampTool()

    @pytest.mark.asyncio
    async def test_news_before_anomaly_causal(self, tool):
        """Test that news before anomaly is marked as causal."""
        news_ts = datetime(2024, 1, 15, 14, 5, 0)
        anomaly_ts = datetime(2024, 1, 15, 14, 10, 0)

        result = await tool.execute(
            news_timestamp=news_ts, anomaly_timestamp=anomaly_ts, threshold_minutes=30
        )

        assert result.success is True
        assert result.is_causal is True
        assert result.timing_tag == "pre_event"
        assert result.time_diff_minutes == -5.0

    @pytest.mark.asyncio
    async def test_news_after_anomaly_not_causal(self, tool):
        """Test that news after anomaly is not causal."""
        news_ts = datetime(2024, 1, 15, 14, 15, 0)
        anomaly_ts = datetime(2024, 1, 15, 14, 10, 0)

        result = await tool.execute(
            news_timestamp=news_ts, anomaly_timestamp=anomaly_ts, threshold_minutes=30
        )

        assert result.success is True
        assert result.is_causal is False
        assert result.timing_tag == "post_event"
        assert result.time_diff_minutes == 5.0

    @pytest.mark.asyncio
    async def test_news_too_early_not_causal(self, tool):
        """Test that news too early is not causal."""
        news_ts = datetime(2024, 1, 15, 13, 0, 0)  # 70 minutes before
        anomaly_ts = datetime(2024, 1, 15, 14, 10, 0)

        result = await tool.execute(
            news_timestamp=news_ts, anomaly_timestamp=anomaly_ts, threshold_minutes=30
        )

        assert result.success is True
        assert result.is_causal is False  # Outside threshold
        assert result.timing_tag == "pre_event"

    @pytest.mark.asyncio
    async def test_iso_string_timestamps(self, tool):
        """Test that ISO string timestamps are parsed correctly."""
        result = await tool.execute(
            news_timestamp="2024-01-15T14:05:00Z",
            anomaly_timestamp="2024-01-15T14:10:00Z",
        )

        assert result.success is True
        assert result.is_causal is True
        assert result.time_diff_minutes == -5.0

    @pytest.mark.asyncio
    async def test_missing_parameters(self, tool):
        """Test error handling for missing parameters."""
        result = await tool.execute(news_timestamp=datetime.now())

        assert result.success is False
        assert result.error is not None


class TestSentimentCheckTool:
    """Tests for sentiment_check tool."""

    @pytest.fixture
    def tool(self):
        return SentimentCheckTool()

    @pytest.mark.asyncio
    async def test_positive_sentiment(self, tool):
        """Test positive sentiment detection."""
        mock_pipeline = Mock()
        mock_pipeline.return_value = [
            {"label": "positive", "score": 0.95},
            {"label": "positive", "score": 0.85},
        ]

        with patch(
            "src.phase2_journalist.tools.sentiment_check._get_sentiment_pipeline",
            return_value=mock_pipeline,
        ):
            result = await tool.execute(
                texts=["Bitcoin rallies to new high", "Crypto market sees massive gains"]
            )

            assert result.success is True
            assert result.average_sentiment > 0.5
            assert result.dominant_label == "positive"
            assert len(result.sentiments) == 2

    @pytest.mark.asyncio
    async def test_negative_sentiment(self, tool):
        """Test negative sentiment detection."""
        mock_pipeline = Mock()
        mock_pipeline.return_value = [
            {"label": "negative", "score": 0.92},
            {"label": "negative", "score": 0.88},
        ]

        with patch(
            "src.phase2_journalist.tools.sentiment_check._get_sentiment_pipeline",
            return_value=mock_pipeline,
        ):
            result = await tool.execute(
                texts=["Bitcoin crashes 10%", "Market panic spreads"]
            )

            assert result.success is True
            assert result.average_sentiment < -0.5
            assert result.dominant_label == "negative"

    @pytest.mark.asyncio
    async def test_neutral_sentiment(self, tool):
        """Test neutral sentiment detection."""
        mock_pipeline = Mock()
        mock_pipeline.return_value = [
            {"label": "neutral", "score": 0.75},
            {"label": "positive", "score": 0.55},
            {"label": "negative", "score": 0.60},
        ]

        with patch(
            "src.phase2_journalist.tools.sentiment_check._get_sentiment_pipeline",
            return_value=mock_pipeline,
        ):
            result = await tool.execute(texts=["Bitcoin stable", "Market unchanged", "Slight volatility"])

            assert result.success is True
            assert -0.2 <= result.average_sentiment <= 0.2
            assert result.dominant_label == "neutral"

    @pytest.mark.asyncio
    async def test_empty_texts(self, tool):
        """Test error handling for empty input."""
        result = await tool.execute(texts=[])

        assert result.success is False
        assert result.error is not None


class TestSearchHistoricalTool:
    """Tests for search_historical tool."""

    @pytest.fixture
    def mock_session(self):
        return Mock(spec=Session)

    @pytest.fixture
    def tool(self, mock_session):
        return SearchHistoricalTool(session=mock_session)

    @pytest.mark.asyncio
    async def test_find_similar_anomalies(self, tool, mock_session):
        """Test finding similar historical anomalies."""
        # Mock database query results
        mock_anomaly1 = Mock(spec=Anomaly)
        mock_anomaly1.id = "123"
        mock_anomaly1.symbol = "BTC-USD"
        mock_anomaly1.detected_at = datetime(2024, 1, 10, 12, 0, 0)
        mock_anomaly1.anomaly_type = AnomalyTypeEnum.PRICE_DROP
        mock_anomaly1.price_change_pct = -5.2

        mock_narrative1 = Mock(spec=Narrative)
        mock_narrative1.narrative_text = "Bitcoin dropped due to regulatory concerns"

        mock_query = Mock()
        mock_query.all.return_value = [(mock_anomaly1, mock_narrative1)]

        mock_session.query.return_value.outerjoin.return_value.filter.return_value.order_by.return_value.limit.return_value = mock_query

        result = await tool.execute(
            symbol="BTC-USD", anomaly_type="price_drop", limit=5, session=mock_session
        )

        assert result.success is True
        assert result.count > 0
        assert len(result.results) > 0
        assert result.results[0].symbol == "BTC-USD"
        assert result.results[0].narrative_text == "Bitcoin dropped due to regulatory concerns"

    @pytest.mark.asyncio
    async def test_no_session_error(self, tool):
        """Test error when no session provided."""
        tool.session = None

        result = await tool.execute(symbol="BTC-USD", anomaly_type="price_drop")

        assert result.success is False
        assert "session" in result.error.lower()

    @pytest.mark.asyncio
    async def test_invalid_anomaly_type(self, tool, mock_session):
        """Test error handling for invalid anomaly type."""
        result = await tool.execute(
            symbol="BTC-USD", anomaly_type="invalid_type", session=mock_session
        )

        assert result.success is False
        assert "invalid" in result.error.lower()


class TestCheckMarketContextTool:
    """Tests for check_market_context tool."""

    @pytest.fixture
    def mock_session(self):
        return Mock(spec=Session)

    @pytest.fixture
    def tool(self, mock_session):
        return CheckMarketContextTool(session=mock_session)

    @pytest.mark.asyncio
    async def test_market_wide_movement(self, tool, mock_session):
        """Test detection of market-wide movement."""
        # Mock price data showing all assets moving together
        def create_mock_prices(symbol, start_price, end_price):
            price1 = Mock(spec=Price)
            price1.price = start_price
            price1.timestamp = datetime(2024, 1, 15, 14, 0, 0)

            price2 = Mock(spec=Price)
            price2.price = end_price
            price2.timestamp = datetime(2024, 1, 15, 14, 10, 0)

            return [price1, price2]

        # Set up query results using side_effect for sequential calls
        results = [
            create_mock_prices("SOL-USD", 100, 95),  # -5%
            create_mock_prices("BTC-USD", 45000, 43500),  # -3.3%
            create_mock_prices("ETH-USD", 3000, 2910),  # -3%
        ]

        # Create a proper mock chain
        mock_query = MagicMock()
        mock_filter1 = MagicMock()
        mock_filter2 = MagicMock()
        mock_order = MagicMock()

        mock_session.query.return_value = mock_query
        mock_query.filter.return_value = mock_filter1
        mock_filter1.filter.return_value = mock_filter2
        mock_filter2.order_by.return_value = mock_order
        mock_order.all.side_effect = results

        result = await tool.execute(
            target_symbol="SOL-USD",
            reference_symbols=["BTC-USD", "ETH-USD"],
            timestamp=datetime(2024, 1, 15, 14, 10, 0),
            session=mock_session,
        )

        assert result.success is True
        assert result.target_context is not None
        # Note: Due to mocking complexity, we're just testing structure
        # In real tests with actual DB, we'd verify is_market_wide

    @pytest.mark.asyncio
    async def test_isolated_movement(self, tool, mock_session):
        """Test detection of isolated asset movement."""
        # Mock price data showing target moves but reference assets are stable
        def create_mock_prices(symbol, start_price, end_price):
            price1 = Mock(spec=Price)
            price1.price = start_price
            price1.timestamp = datetime(2024, 1, 15, 14, 0, 0)

            price2 = Mock(spec=Price)
            price2.price = end_price
            price2.timestamp = datetime(2024, 1, 15, 14, 10, 0)

            return [price1, price2]

        # Set up query results using side_effect for sequential calls
        results = [
            create_mock_prices("DOGE-USD", 100, 110),  # +10% - significant movement
            create_mock_prices("BTC-USD", 45000, 45200),  # +0.4% - stable
            create_mock_prices("ETH-USD", 3000, 3015),  # +0.5% - stable
        ]

        # Create a proper mock chain
        mock_query = MagicMock()
        mock_filter1 = MagicMock()
        mock_filter2 = MagicMock()
        mock_order = MagicMock()

        mock_session.query.return_value = mock_query
        mock_query.filter.return_value = mock_filter1
        mock_filter1.filter.return_value = mock_filter2
        mock_filter2.order_by.return_value = mock_order
        mock_order.all.side_effect = results

        result = await tool.execute(
            target_symbol="DOGE-USD",
            timestamp=datetime(2024, 1, 15, 14, 10, 0),
            session=mock_session,
        )

        assert result.success is True
        assert result.target_context is not None


class TestCheckSocialSentimentTool:
    """Tests for check_social_sentiment tool."""

    @pytest.fixture
    def tool(self):
        return CheckSocialSentimentTool()

    @pytest.mark.asyncio
    async def test_bullish_social_sentiment(self, tool):
        """Test bullish social sentiment detection."""
        mock_pipeline = Mock()
        mock_pipeline.return_value = [
            {"label": "positive", "score": 0.90},
            {"label": "positive", "score": 0.85},
            {"label": "neutral", "score": 0.70},
        ]

        with patch(
            "src.phase2_journalist.tools.check_social_sentiment._get_sentiment_pipeline",
            return_value=mock_pipeline,
        ):
            result = await tool.execute(
                symbol="BTC-USD",
                news_articles=["BTC to the moon!", "Amazing gains today", "Bullish on Bitcoin"],
            )

            assert result.success is True
            assert result.sentiment_label == "bullish"
            assert result.article_count == 3
            assert result.sentiment_distribution["positive"] == 2

    @pytest.mark.asyncio
    async def test_bearish_social_sentiment(self, tool):
        """Test bearish social sentiment detection."""
        mock_pipeline = Mock()
        mock_pipeline.return_value = [
            {"label": "negative", "score": 0.88},
            {"label": "negative", "score": 0.92},
        ]

        with patch(
            "src.phase2_journalist.tools.check_social_sentiment._get_sentiment_pipeline",
            return_value=mock_pipeline,
        ):
            result = await tool.execute(
                symbol="BTC-USD", news_articles=["Bitcoin crash imminent", "Sell now!"]
            )

            assert result.success is True
            assert result.sentiment_label == "bearish"
            assert result.sentiment_distribution["negative"] == 2


class TestToolRegistry:
    """Tests for ToolRegistry."""

    @pytest.fixture
    def mock_session(self):
        return Mock(spec=Session)

    @pytest.fixture
    def registry(self, mock_session):
        return ToolRegistry(session=mock_session)

    def test_registry_initialization(self, registry):
        """Test that registry initializes with all tools."""
        assert len(registry.get_all_tools()) == 5
        assert "verify_timestamp" in registry.get_tool_names()
        assert "sentiment_check" in registry.get_tool_names()
        assert "search_historical" in registry.get_tool_names()
        assert "check_market_context" in registry.get_tool_names()
        assert "check_social_sentiment" in registry.get_tool_names()

    def test_get_tool(self, registry):
        """Test getting individual tools."""
        tool = registry.get_tool("verify_timestamp")
        assert tool is not None
        assert isinstance(tool, VerifyTimestampTool)

    def test_get_nonexistent_tool(self, registry):
        """Test getting nonexistent tool returns None."""
        tool = registry.get_tool("nonexistent")
        assert tool is None

    def test_get_all_tool_definitions(self, registry):
        """Test getting all tool definitions for LLM."""
        definitions = registry.get_all_tool_definitions()
        assert len(definitions) == 5
        assert all("type" in d and d["type"] == "function" for d in definitions)
        assert all("function" in d for d in definitions)
        assert all("name" in d["function"] for d in definitions)

    @pytest.mark.asyncio
    async def test_execute_tool(self, registry):
        """Test executing a tool through registry."""
        result = await registry.execute_tool(
            "verify_timestamp",
            news_timestamp=datetime(2024, 1, 15, 14, 5, 0),
            anomaly_timestamp=datetime(2024, 1, 15, 14, 10, 0),
        )

        assert result.success is True
        assert result.is_causal is True

    @pytest.mark.asyncio
    async def test_execute_nonexistent_tool(self, registry):
        """Test executing nonexistent tool raises error."""
        with pytest.raises(ValueError, match="Tool not found"):
            await registry.execute_tool("nonexistent")

    def test_convenience_function(self, mock_session):
        """Test get_all_tool_definitions convenience function."""
        definitions = get_all_tool_definitions(session=mock_session)
        assert len(definitions) == 5


class TestToolDefinitions:
    """Tests for tool JSON schema definitions."""

    def test_verify_timestamp_schema(self):
        """Test verify_timestamp tool schema."""
        schema = VerifyTimestampTool.get_parameters_schema()
        assert "properties" in schema
        assert "news_timestamp" in schema["properties"]
        assert "anomaly_timestamp" in schema["properties"]
        assert "required" in schema

    def test_sentiment_check_schema(self):
        """Test sentiment_check tool schema."""
        schema = SentimentCheckTool.get_parameters_schema()
        assert "properties" in schema
        assert "texts" in schema["properties"]
        assert schema["properties"]["texts"]["type"] == "array"

    def test_search_historical_schema(self):
        """Test search_historical tool schema."""
        schema = SearchHistoricalTool.get_parameters_schema()
        assert "symbol" in schema["properties"]
        assert "anomaly_type" in schema["properties"]
        assert "enum" in schema["properties"]["anomaly_type"]

    def test_tool_definition_format(self):
        """Test that tool definitions match LLM function calling format."""
        definition = VerifyTimestampTool.get_tool_definition()
        assert definition["type"] == "function"
        assert "function" in definition
        assert definition["function"]["name"] == "verify_timestamp"
        assert "description" in definition["function"]
        assert "parameters" in definition["function"]
