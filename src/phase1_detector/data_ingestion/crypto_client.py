"""Abstract base class for cryptocurrency exchange clients."""

from abc import ABC, abstractmethod
from datetime import datetime, timedelta, UTC
from typing import Sequence

import pandas as pd
from sqlalchemy.orm import Session
from sqlalchemy.dialects.postgresql import insert

from src.phase1_detector.data_ingestion.models import PriceData
from src.database.models import Price


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

    @abstractmethod
    async def get_historical_prices(
        self,
        symbol: str,
        start_time: datetime,
        end_time: datetime,
        granularity_seconds: int = 60,
    ) -> list[PriceData]:
        """Fetch historical price data from exchange.

        Args:
            symbol: Trading pair symbol (e.g., 'BTC-USD')
            start_time: Start of date range (UTC)
            end_time: End of date range (UTC)
            granularity_seconds: Candle interval in seconds (default: 60)

        Returns:
            List of PriceData objects for the date range

        Raises:
            ValueError: If date range invalid or symbol not supported
            ConnectionError: If API request fails

        Note:
            Implementation must handle pagination internally for large date ranges.
        """
        pass

    async def store_price(self, price_data: PriceData, session: Session) -> None:
        """Store price data to database.

        Uses INSERT ... ON CONFLICT DO NOTHING to handle duplicates gracefully.

        Args:
            price_data: Price data to store
            session: SQLAlchemy database session

        Raises:
            Exception: If database operation fails
        """
        # Convert PriceData (Pydantic) to dict for insertion
        price_dict = {
            "symbol": price_data.symbol,
            "timestamp": price_data.timestamp,
            "price": price_data.price,
            "volume_24h": price_data.volume_24h,
            "high_24h": price_data.high_24h,
            "low_24h": price_data.low_24h,
            "bid": price_data.bid,
            "ask": price_data.ask,
            "source": price_data.source,
            "created_at": datetime.now(UTC),
        }

        # Use PostgreSQL INSERT ... ON CONFLICT to handle duplicates
        stmt = insert(Price).values(**price_dict)
        # Ignore duplicates based on symbol + timestamp (unique constraint)
        stmt = stmt.on_conflict_do_nothing(index_elements=["symbol", "timestamp"])

        session.execute(stmt)
        session.commit()

    async def get_price_history(
        self,
        symbol: str,
        minutes: int,
        session: Session,
    ) -> pd.DataFrame:
        """Retrieve price history from database.

        Queries the last N minutes of price data for the given symbol.

        Args:
            symbol: Trading pair symbol (e.g., 'BTC-USD')
            minutes: Number of minutes of history to fetch
            session: SQLAlchemy database session

        Returns:
            DataFrame with columns: [timestamp, price, volume, symbol]
            Returns empty DataFrame if no data found

        Raises:
            Exception: If database query fails
        """
        # Calculate cutoff time
        cutoff_time = datetime.utcnow() - timedelta(minutes=minutes)

        # Query price history
        prices = (
            session.query(Price)
            .filter(
                Price.symbol == symbol,
                Price.timestamp >= cutoff_time,
            )
            .order_by(Price.timestamp.asc())
            .all()
        )

        # Convert to DataFrame
        if not prices:
            return pd.DataFrame(columns=["timestamp", "price", "volume", "symbol"])

        data = {
            "timestamp": [p.timestamp for p in prices],
            "price": [p.price for p in prices],
            "volume": [p.volume_24h for p in prices],
            "symbol": [p.symbol for p in prices],
        }

        return pd.DataFrame(data)

    async def store_prices_bulk(
        self,
        prices: list[PriceData],
        session: Session,
        batch_size: int = 1000,
    ) -> int:
        """Store multiple price records efficiently using bulk insert.

        Uses INSERT ... ON CONFLICT DO NOTHING for idempotent operation.

        Args:
            prices: List of PriceData objects to store
            session: SQLAlchemy database session
            batch_size: Number of records per batch (default: 1000)

        Returns:
            Number of records actually inserted (excluding duplicates)

        Raises:
            Exception: If database operation fails
        """
        if not prices:
            return 0

        # Convert PriceData objects to dicts
        price_dicts = [
            {
                "symbol": p.symbol,
                "timestamp": p.timestamp,
                "price": p.price,
                "volume_24h": p.volume_24h,
                "high_24h": p.high_24h,
                "low_24h": p.low_24h,
                "bid": p.bid,
                "ask": p.ask,
                "source": p.source,
                "created_at": datetime.now(UTC),
            }
            for p in prices
        ]

        inserted_count = 0

        # Process in batches
        for i in range(0, len(price_dicts), batch_size):
            batch = price_dicts[i : i + batch_size]

            # PostgreSQL-specific bulk insert with ON CONFLICT
            stmt = insert(Price).values(batch)
            stmt = stmt.on_conflict_do_nothing(index_elements=["symbol", "timestamp"])

            result = session.execute(stmt)
            inserted_count += result.rowcount

        session.commit()
        return inserted_count
