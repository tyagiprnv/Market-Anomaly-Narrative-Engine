"""Abstract base class for cryptocurrency exchange clients."""

from abc import ABC, abstractmethod
from typing import Sequence

from src.phase1_detector.data_ingestion.models import PriceData


class CryptoClient(ABC):
    """Abstract base class for crypto exchange API clients.

    All exchange clients (Coinbase, Binance, etc.) should inherit from this class
    and implement the required methods.
    """

    def __init__(self, api_key: str | None = None, api_secret: str | None = None):
        """Initialize the crypto client.

        Args:
            api_key: API key for the exchange (optional for public endpoints)
            api_secret: API secret for the exchange (optional for public endpoints)
        """
        self.api_key = api_key
        self.api_secret = api_secret

    @abstractmethod
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
        pass

    @abstractmethod
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
        pass

    @abstractmethod
    async def health_check(self) -> bool:
        """Check if the exchange API is reachable and healthy.

        Returns:
            True if API is healthy, False otherwise
        """
        pass

    @property
    @abstractmethod
    def source_name(self) -> str:
        """Get the name of this data source.

        Returns:
            Source name (e.g., 'coinbase', 'binance')
        """
        pass
