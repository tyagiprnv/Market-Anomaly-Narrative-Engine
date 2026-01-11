"""Pydantic models for data ingestion."""

from datetime import datetime, UTC
from pydantic import BaseModel, ConfigDict, Field


class PriceData(BaseModel):
    """Price data from crypto exchanges."""

    symbol: str = Field(..., description="Trading pair symbol (e.g., BTC-USD)")
    timestamp: datetime = Field(..., description="Time of price snapshot")
    price: float = Field(..., description="Current price")
    volume_24h: float | None = Field(None, description="24-hour trading volume")
    high_24h: float | None = Field(None, description="24-hour high price")
    low_24h: float | None = Field(None, description="24-hour low price")
    bid: float | None = Field(None, description="Best bid price")
    ask: float | None = Field(None, description="Best ask price")
    source: str = Field(..., description="Data source (coinbase, binance)")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "symbol": "BTC-USD",
                "timestamp": "2024-01-11T12:00:00Z",
                "price": 45000.0,
                "volume_24h": 1500000000.0,
                "high_24h": 46000.0,
                "low_24h": 44000.0,
                "bid": 44995.0,
                "ask": 45005.0,
                "source": "coinbase",
            }
        }
    )


class TickerData(BaseModel):
    """Raw ticker data from exchange API."""

    symbol: str
    price: float
    volume: float | None = None
    high: float | None = None
    low: float | None = None
    bid: float | None = None
    ask: float | None = None
    timestamp: datetime | None = None

    def to_price_data(self, source: str) -> PriceData:
        """Convert to standardized PriceData.

        Args:
            source: Name of the data source (e.g., 'coinbase', 'binance')

        Returns:
            Standardized PriceData object
        """
        return PriceData(
            symbol=self.symbol,
            timestamp=self.timestamp or datetime.now(UTC),
            price=self.price,
            volume_24h=self.volume,
            high_24h=self.high,
            low_24h=self.low,
            bid=self.bid,
            ask=self.ask,
            source=source,
        )
