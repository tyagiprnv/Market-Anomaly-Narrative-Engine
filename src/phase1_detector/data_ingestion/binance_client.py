"""Binance API client for price data."""

import asyncio
from datetime import datetime, UTC
from typing import Any, Sequence
import httpx

from src.phase1_detector.data_ingestion.crypto_client import CryptoClient
from src.phase1_detector.data_ingestion.models import PriceData, TickerData


class BinanceClient(CryptoClient):
    """Client for Binance public API.

    This client uses the public Binance REST API to fetch real-time price data.
    No authentication is required for public endpoints.

    API Docs: https://binance-docs.github.io/apidocs/spot/en/

    Note: Binance uses different symbol notation (BTCUSDT vs BTC-USD).
    This client handles the conversion automatically.
    """

    BASE_URL = "https://api.binance.com/api/v3"

    def __init__(self, api_key: str | None = None, api_secret: str | None = None):
        """Initialize Binance client.

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

    def _convert_symbol(self, symbol: str) -> str:
        """Convert standard symbol format to Binance format.

        Args:
            symbol: Standard format (e.g., 'BTC-USD')

        Returns:
            Binance format (e.g., 'BTCUSDT')
        """
        # Replace USD with USDT and remove dash
        return symbol.replace("-USD", "USDT").replace("-", "")

    def _convert_symbol_back(self, binance_symbol: str) -> str:
        """Convert Binance symbol format back to standard format.

        Args:
            binance_symbol: Binance format (e.g., 'BTCUSDT')

        Returns:
            Standard format (e.g., 'BTC-USD')
        """
        # Add dash before USDT and replace with USD
        return binance_symbol.replace("USDT", "-USD")

    async def get_price(self, symbol: str) -> PriceData:
        """Get current price data for a symbol.

        Args:
            symbol: Trading pair symbol in standard format (e.g., 'BTC-USD')

        Returns:
            PriceData object with current market data

        Raises:
            ValueError: If symbol is invalid or not supported
            ConnectionError: If API request fails
        """
        binance_symbol = self._convert_symbol(symbol)

        try:
            # Get 24h ticker data (includes price, volume, high, low)
            url = f"{self.BASE_URL}/ticker/24hr"
            params = {"symbol": binance_symbol}
            response = await self._client.get(url, params=params)
            response.raise_for_status()
            data = response.json()

            # Parse response
            ticker = self._parse_ticker(symbol, data)
            return ticker.to_price_data(self.source_name)

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 400:
                raise ValueError(f"Symbol {symbol} not found on Binance")
            raise ConnectionError(f"Binance API error: {e}")
        except httpx.RequestError as e:
            raise ConnectionError(f"Failed to connect to Binance API: {e}")

    async def get_prices(self, symbols: Sequence[str]) -> list[PriceData]:
        """Get current price data for multiple symbols.

        Args:
            symbols: List of trading pair symbols in standard format

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
                print(f"Warning: Failed to fetch {symbol} from Binance: {result}")
            else:
                prices.append(result)

        return prices

    async def health_check(self) -> bool:
        """Check if the Binance API is reachable.

        Returns:
            True if API is healthy, False otherwise
        """
        try:
            # Use the ping endpoint
            url = f"{self.BASE_URL}/ping"
            response = await self._client.get(url)
            return response.status_code == 200
        except Exception:
            return False

    @property
    def source_name(self) -> str:
        """Get the name of this data source.

        Returns:
            'binance'
        """
        return "binance"

    def _parse_ticker(self, symbol: str, data: dict[str, Any]) -> TickerData:
        """Parse Binance API response into TickerData.

        Args:
            symbol: Trading pair symbol in standard format
            data: Response from Binance 24hr ticker endpoint

        Returns:
            TickerData object
        """
        return TickerData(
            symbol=symbol,
            price=float(data["lastPrice"]),
            volume=float(data["volume"]),
            high=float(data["highPrice"]),
            low=float(data["lowPrice"]),
            bid=float(data["bidPrice"]),
            ask=float(data["askPrice"]),
            timestamp=datetime.now(UTC),
        )
