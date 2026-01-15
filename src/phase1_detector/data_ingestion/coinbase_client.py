"""Coinbase Advanced Trade API client for price data."""

import asyncio
from datetime import datetime, timedelta, UTC
from typing import Any, Sequence
import httpx

from src.phase1_detector.data_ingestion.crypto_client import CryptoClient
from src.phase1_detector.data_ingestion.models import PriceData, TickerData


class CoinbaseClient(CryptoClient):
    """Client for Coinbase Advanced Trade API.

    This client uses the public Coinbase Advanced Trade REST API to fetch
    real-time price data. No authentication is required for public endpoints.

    API Docs: https://docs.cloud.coinbase.com/advanced-trade-api/docs/
    """

    # Using the public Coinbase Exchange API (formerly GDAX)
    BASE_URL = "https://api.exchange.coinbase.com"

    def __init__(self, api_key: str | None = None, api_secret: str | None = None):
        """Initialize Coinbase client.

        Args:
            api_key: API key (optional, not required for public endpoints)
            api_secret: API secret (optional, not required for public endpoints)
        """
        super().__init__(api_key, api_secret)
        self._client = httpx.AsyncClient(timeout=10.0)

    async def __aenter__(self):
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self._client.aclose()

    async def close(self):
        """Close the HTTP client."""
        await self._client.aclose()

    async def get_price(self, symbol: str) -> PriceData:
        """Get current price data for a symbol.

        Args:
            symbol: Trading pair symbol (e.g., 'BTC-USD')

        Returns:
            PriceData object with current market data

        Raises:
            ValueError: If symbol is invalid or not supported
            ConnectionError: If API request fails
        """
        try:
            # Get ticker data (includes price and best bid/ask)
            ticker_url = f"{self.BASE_URL}/products/{symbol}/ticker"
            response = await self._client.get(ticker_url)
            response.raise_for_status()
            ticker_data = response.json()

            # Get 24h stats (includes volume, high, low)
            stats_url = f"{self.BASE_URL}/products/{symbol}/stats"
            stats_response = await self._client.get(stats_url)
            stats_response.raise_for_status()
            stats_data = stats_response.json()

            # Parse response
            ticker = self._parse_ticker(symbol, ticker_data, stats_data)
            return ticker.to_price_data(self.source_name)

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                raise ValueError(f"Symbol {symbol} not found on Coinbase")
            raise ConnectionError(f"Coinbase API error: {e}")
        except httpx.RequestError as e:
            raise ConnectionError(f"Failed to connect to Coinbase API: {e}")

    async def get_prices(self, symbols: Sequence[str]) -> list[PriceData]:
        """Get current price data for multiple symbols.

        Args:
            symbols: List of trading pair symbols

        Returns:
            List of PriceData objects

        Raises:
            ValueError: If any symbol is invalid
            ConnectionError: If API request fails
        """
        # Fetch all symbols concurrently
        tasks = [self.get_price(symbol) for symbol in symbols]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Separate successful results from errors
        prices = []
        for symbol, result in zip(symbols, results):
            if isinstance(result, Exception):
                print(f"Warning: Failed to fetch {symbol} from Coinbase: {result}")
            else:
                prices.append(result)

        return prices

    async def health_check(self) -> bool:
        """Check if the Coinbase API is reachable.

        Returns:
            True if API is healthy, False otherwise
        """
        try:
            # Try to fetch BTC-USD as a health check
            url = f"{self.BASE_URL}/products/BTC-USD/ticker"
            response = await self._client.get(url)
            return response.status_code == 200
        except Exception:
            return False

    @property
    def source_name(self) -> str:
        """Get the name of this data source.

        Returns:
            'coinbase'
        """
        return "coinbase"

    async def get_historical_prices(
        self,
        symbol: str,
        start_time: datetime,
        end_time: datetime,
        granularity_seconds: int = 60,
    ) -> list[PriceData]:
        """Fetch historical price data from Coinbase candles endpoint.

        Coinbase API details:
        - Endpoint: /products/{symbol}/candles
        - Max 300 candles per request
        - Granularity options: 60, 300, 900, 3600, 21600, 86400 seconds
        - Returns: [timestamp, low, high, open, close, volume]
        """
        # Validate granularity
        valid_granularities = [60, 300, 900, 3600, 21600, 86400]
        if granularity_seconds not in valid_granularities:
            raise ValueError(
                f"Invalid granularity {granularity_seconds}. "
                f"Must be one of {valid_granularities}"
            )

        all_prices = []

        # Coinbase max is 300 candles per request
        max_candles = 300
        window_seconds = max_candles * granularity_seconds

        # Pagination: Split date range into chunks
        current_start = start_time

        while current_start < end_time:
            current_end = min(
                current_start + timedelta(seconds=window_seconds), end_time
            )

            try:
                # Convert to ISO 8601 format
                start_iso = current_start.isoformat()
                end_iso = current_end.isoformat()

                url = f"{self.BASE_URL}/products/{symbol}/candles"
                params = {
                    "start": start_iso,
                    "end": end_iso,
                    "granularity": granularity_seconds,
                }

                response = await self._client.get(url, params=params)
                response.raise_for_status()
                candles = response.json()

                # Parse candles: [timestamp, low, high, open, close, volume]
                for candle in candles:
                    timestamp = datetime.fromtimestamp(candle[0], tz=UTC)

                    price_data = PriceData(
                        symbol=symbol,
                        timestamp=timestamp,
                        price=float(candle[4]),  # close price
                        volume_24h=float(candle[5]),  # volume
                        high_24h=float(candle[2]),  # high
                        low_24h=float(candle[1]),  # low
                        bid=None,  # Not available in candles
                        ask=None,  # Not available in candles
                        source=self.source_name,
                    )
                    all_prices.append(price_data)

                # Move to next window
                current_start = current_end

                # Rate limit protection (Coinbase public API: 10 req/sec)
                await asyncio.sleep(0.1)

            except httpx.HTTPStatusError as e:
                if e.response.status_code == 404:
                    raise ValueError(f"Symbol {symbol} not found on Coinbase")
                raise ConnectionError(f"Coinbase API error: {e}")
            except httpx.RequestError as e:
                raise ConnectionError(f"Failed to connect to Coinbase API: {e}")

        return all_prices

    def _parse_ticker(
        self, symbol: str, ticker_data: dict[str, Any], stats_data: dict[str, Any]
    ) -> TickerData:
        """Parse Coinbase API response into TickerData.

        Args:
            symbol: Trading pair symbol
            ticker_data: Response from ticker endpoint
            stats_data: Response from stats endpoint

        Returns:
            TickerData object
        """
        # Extract from ticker response
        price = float(ticker_data.get("price", 0))
        best_bid = float(ticker_data.get("bid", price))
        best_ask = float(ticker_data.get("ask", price))

        # Extract from stats response (24h data)
        volume_24h = float(stats_data.get("volume", 0))
        high_24h = float(stats_data.get("high", price))
        low_24h = float(stats_data.get("low", price))

        return TickerData(
            symbol=symbol,
            price=price,
            volume=volume_24h,
            high=high_24h,
            low=low_24h,
            bid=best_bid,
            ask=best_ask,
            timestamp=datetime.now(UTC),
        )
