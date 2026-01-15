"""Unit tests for data ingestion clients."""

import pytest
from datetime import datetime, timedelta, UTC
from unittest.mock import AsyncMock, Mock, patch
import httpx

from src.phase1_detector.data_ingestion import (
    CoinbaseClient,
    BinanceClient,
    PriceData,
    TickerData,
)


@pytest.fixture
def mock_coinbase_ticker_response():
    """Mock Coinbase Exchange API ticker response."""
    return {
        "price": "45000.00",
        "bid": "44995.00",
        "ask": "45005.00",
    }


@pytest.fixture
def mock_coinbase_stats_response():
    """Mock Coinbase Exchange API 24h stats response."""
    return {
        "volume": "1500000000.00",
        "high": "46000.00",
        "low": "44000.00",
    }


@pytest.fixture
def mock_binance_ticker_response():
    """Mock Binance 24hr ticker API response."""
    return {
        "symbol": "BTCUSDT",
        "lastPrice": "45000.00",
        "volume": "1500000000.00",
        "highPrice": "46000.00",
        "lowPrice": "44000.00",
        "bidPrice": "44995.00",
        "askPrice": "45005.00",
    }


class TestTickerData:
    """Tests for TickerData model."""

    def test_to_price_data_conversion(self):
        """Test conversion from TickerData to PriceData."""
        ticker = TickerData(
            symbol="BTC-USD",
            price=45000.0,
            volume=1500000000.0,
            high=46000.0,
            low=44000.0,
            bid=44995.0,
            ask=45005.0,
            timestamp=datetime(2024, 1, 11, 12, 0, 0),
        )

        price_data = ticker.to_price_data(source="coinbase")

        assert price_data.symbol == "BTC-USD"
        assert price_data.price == 45000.0
        assert price_data.volume_24h == 1500000000.0
        assert price_data.high_24h == 46000.0
        assert price_data.low_24h == 44000.0
        assert price_data.bid == 44995.0
        assert price_data.ask == 45005.0
        assert price_data.source == "coinbase"
        assert price_data.timestamp == datetime(2024, 1, 11, 12, 0, 0)


class TestCoinbaseClient:
    """Tests for CoinbaseClient."""

    @pytest.mark.asyncio
    async def test_get_price_success(
        self, mock_coinbase_ticker_response, mock_coinbase_stats_response
    ):
        """Test successful price fetch from Coinbase."""
        with patch("httpx.AsyncClient") as mock_client_class:
            # Set up mock client
            mock_client = AsyncMock()
            mock_client_class.return_value = mock_client

            # Mock ticker response
            ticker_response = Mock()
            ticker_response.json.return_value = mock_coinbase_ticker_response
            ticker_response.raise_for_status = Mock()

            # Mock stats response
            stats_response = Mock()
            stats_response.json.return_value = mock_coinbase_stats_response
            stats_response.raise_for_status = Mock()

            # Configure get to return different responses
            mock_client.get.side_effect = [ticker_response, stats_response]

            # Test
            client = CoinbaseClient()
            price_data = await client.get_price("BTC-USD")

            assert price_data.symbol == "BTC-USD"
            assert price_data.price == 45000.0
            assert price_data.volume_24h == 1500000000.0
            assert price_data.source == "coinbase"

    @pytest.mark.asyncio
    async def test_get_price_invalid_symbol(self):
        """Test error handling for invalid symbol."""
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value = mock_client

            # Mock 404 response
            mock_response = Mock()
            mock_response.status_code = 404
            mock_client.get.side_effect = httpx.HTTPStatusError(
                "Not found", request=Mock(), response=mock_response
            )

            client = CoinbaseClient()

            with pytest.raises(ValueError, match="not found"):
                await client.get_price("INVALID-USD")

    @pytest.mark.asyncio
    async def test_get_prices_multiple_symbols(
        self, mock_coinbase_ticker_response, mock_coinbase_stats_response
    ):
        """Test fetching multiple symbols concurrently."""
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value = mock_client

            # Mock responses
            ticker_response = Mock()
            ticker_response.json.return_value = mock_coinbase_ticker_response
            ticker_response.raise_for_status = Mock()

            stats_response = Mock()
            stats_response.json.return_value = mock_coinbase_stats_response
            stats_response.raise_for_status = Mock()

            mock_client.get.side_effect = [
                ticker_response,
                stats_response,
                ticker_response,
                stats_response,
            ]

            client = CoinbaseClient()
            prices = await client.get_prices(["BTC-USD", "ETH-USD"])

            assert len(prices) == 2
            assert all(isinstance(p, PriceData) for p in prices)

    @pytest.mark.asyncio
    async def test_health_check_success(self):
        """Test health check with successful API response."""
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value = mock_client

            mock_response = Mock()
            mock_response.status_code = 200
            mock_client.get.return_value = mock_response

            client = CoinbaseClient()
            is_healthy = await client.health_check()

            assert is_healthy is True

    @pytest.mark.asyncio
    async def test_health_check_failure(self):
        """Test health check with failed API response."""
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value = mock_client

            mock_client.get.side_effect = Exception("Connection error")

            client = CoinbaseClient()
            is_healthy = await client.health_check()

            assert is_healthy is False

    def test_source_name(self):
        """Test source_name property."""
        client = CoinbaseClient()
        assert client.source_name == "coinbase"


class TestBinanceClient:
    """Tests for BinanceClient."""

    def test_symbol_conversion(self):
        """Test symbol format conversion."""
        client = BinanceClient()

        # Test conversion to Binance format
        assert client._convert_symbol("BTC-USD") == "BTCUSDT"
        assert client._convert_symbol("ETH-USD") == "ETHUSDT"
        assert client._convert_symbol("BNB-USD") == "BNBUSDT"

        # Test conversion back to standard format
        assert client._convert_symbol_back("BTCUSDT") == "BTC-USD"
        assert client._convert_symbol_back("ETHUSDT") == "ETH-USD"

    @pytest.mark.asyncio
    async def test_get_price_success(self, mock_binance_ticker_response):
        """Test successful price fetch from Binance."""
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value = mock_client

            mock_response = Mock()
            mock_response.json.return_value = mock_binance_ticker_response
            mock_response.raise_for_status = Mock()
            mock_client.get.return_value = mock_response

            client = BinanceClient()
            price_data = await client.get_price("BTC-USD")

            assert price_data.symbol == "BTC-USD"
            assert price_data.price == 45000.0
            assert price_data.volume_24h == 1500000000.0
            assert price_data.source == "binance"

    @pytest.mark.asyncio
    async def test_get_price_invalid_symbol(self):
        """Test error handling for invalid symbol."""
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value = mock_client

            mock_response = Mock()
            mock_response.status_code = 400
            mock_client.get.side_effect = httpx.HTTPStatusError(
                "Bad request", request=Mock(), response=mock_response
            )

            client = BinanceClient()

            with pytest.raises(ValueError, match="not found"):
                await client.get_price("INVALID-USD")

    @pytest.mark.asyncio
    async def test_health_check_success(self):
        """Test health check with successful API response."""
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value = mock_client

            mock_response = Mock()
            mock_response.status_code = 200
            mock_client.get.return_value = mock_response

            client = BinanceClient()
            is_healthy = await client.health_check()

            assert is_healthy is True

    def test_source_name(self):
        """Test source_name property."""
        client = BinanceClient()
        assert client.source_name == "binance"


class TestHistoricalDataFetching:
    """Tests for get_historical_prices methods."""

    @pytest.mark.asyncio
    async def test_coinbase_historical_fetch(self):
        """Test Coinbase historical data fetching with pagination."""
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value = mock_client

            # Mock candle responses (format: [time, low, high, open, close, volume])
            mock_candles = [
                [1704974400, 44000.0, 46000.0, 45000.0, 45500.0, 1500000000.0],
                [1704974460, 44500.0, 46500.0, 45500.0, 46000.0, 1600000000.0],
            ]

            mock_response = Mock()
            mock_response.json.return_value = mock_candles
            mock_response.raise_for_status = Mock()
            mock_client.get.return_value = mock_response

            client = CoinbaseClient()

            start = datetime(2024, 1, 11, 0, 0, 0, tzinfo=UTC)
            end = datetime(2024, 1, 11, 1, 0, 0, tzinfo=UTC)

            prices = await client.get_historical_prices(
                symbol="BTC-USD",
                start_time=start,
                end_time=end,
                granularity_seconds=60,
            )

            assert len(prices) == 2
            assert all(isinstance(p, PriceData) for p in prices)
            assert prices[0].symbol == "BTC-USD"
            assert prices[0].source == "coinbase"
            assert prices[0].price == 45500.0

    @pytest.mark.asyncio
    async def test_binance_historical_fetch(self):
        """Test Binance historical data fetching with pagination."""
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value = mock_client

            # Mock kline responses
            # [Open time, Open, High, Low, Close, Volume, Close time, ...]
            mock_klines = [
                [
                    1704974400000,
                    "45000.0",
                    "46000.0",
                    "44000.0",
                    "45500.0",
                    "1500000000.0",
                    1704974459999,
                ],
                [
                    1704974460000,
                    "45500.0",
                    "46500.0",
                    "44500.0",
                    "46000.0",
                    "1600000000.0",
                    1704974519999,
                ],
            ]

            mock_response = Mock()
            mock_response.json.return_value = mock_klines
            mock_response.raise_for_status = Mock()
            mock_client.get.return_value = mock_response

            client = BinanceClient()

            start = datetime(2024, 1, 11, 0, 0, 0, tzinfo=UTC)
            end = datetime(2024, 1, 11, 1, 0, 0, tzinfo=UTC)

            prices = await client.get_historical_prices(
                symbol="BTC-USD",
                start_time=start,
                end_time=end,
                granularity_seconds=60,
            )

            assert len(prices) == 2
            assert all(isinstance(p, PriceData) for p in prices)
            assert prices[0].symbol == "BTC-USD"
            assert prices[0].source == "binance"
            assert prices[0].price == 45500.0

    @pytest.mark.asyncio
    async def test_invalid_granularity_coinbase(self):
        """Test error handling for invalid granularity."""
        client = CoinbaseClient()

        start = datetime(2024, 1, 11, 0, 0, 0, tzinfo=UTC)
        end = datetime(2024, 1, 11, 1, 0, 0, tzinfo=UTC)

        with pytest.raises(ValueError, match="Invalid granularity"):
            await client.get_historical_prices(
                symbol="BTC-USD",
                start_time=start,
                end_time=end,
                granularity_seconds=999,  # Invalid
            )

    @pytest.mark.asyncio
    async def test_invalid_granularity_binance(self):
        """Test error handling for invalid granularity."""
        client = BinanceClient()

        start = datetime(2024, 1, 11, 0, 0, 0, tzinfo=UTC)
        end = datetime(2024, 1, 11, 1, 0, 0, tzinfo=UTC)

        with pytest.raises(ValueError, match="Invalid granularity"):
            await client.get_historical_prices(
                symbol="BTC-USD",
                start_time=start,
                end_time=end,
                granularity_seconds=999,  # Invalid
            )


class TestBulkStorage:
    """Tests for store_prices_bulk method."""

    @pytest.mark.asyncio
    async def test_bulk_insert_success(self):
        """Test bulk insertion of price data."""
        mock_session = Mock()
        mock_result = Mock()
        mock_result.rowcount = 100
        mock_session.execute.return_value = mock_result

        # Create test data
        base_time = datetime(2024, 1, 11, 12, 0, 0, tzinfo=UTC)
        prices = [
            PriceData(
                symbol="BTC-USD",
                timestamp=base_time + timedelta(seconds=i),
                price=45000.0 + i,
                volume_24h=1500000000.0,
                high_24h=46000.0,
                low_24h=44000.0,
                bid=None,
                ask=None,
                source="coinbase",
            )
            for i in range(100)
        ]

        client = CoinbaseClient()
        inserted = await client.store_prices_bulk(prices, mock_session)

        assert inserted == 100
        assert mock_session.execute.called
        assert mock_session.commit.called

    @pytest.mark.asyncio
    async def test_bulk_insert_batching(self):
        """Test that bulk insert respects batch size."""
        mock_session = Mock()
        mock_result = Mock()
        mock_result.rowcount = 50
        mock_session.execute.return_value = mock_result

        # Create 1500 records (should be split into 2 batches of 1000 and 500)
        base_time = datetime(2024, 1, 11, 12, 0, 0, tzinfo=UTC)
        prices = [
            PriceData(
                symbol="BTC-USD",
                timestamp=base_time + timedelta(seconds=i),
                price=45000.0 + i,
                volume_24h=1500000000.0,
                high_24h=46000.0,
                low_24h=44000.0,
                bid=None,
                ask=None,
                source="coinbase",
            )
            for i in range(1500)
        ]

        client = CoinbaseClient()
        await client.store_prices_bulk(prices, mock_session, batch_size=1000)

        # Should be called twice (once per batch)
        assert mock_session.execute.call_count == 2

    @pytest.mark.asyncio
    async def test_bulk_insert_empty_list(self):
        """Test bulk insert with empty list."""
        mock_session = Mock()
        client = CoinbaseClient()

        inserted = await client.store_prices_bulk([], mock_session)

        assert inserted == 0
        assert not mock_session.execute.called
