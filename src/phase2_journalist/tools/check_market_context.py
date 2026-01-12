"""Tool to check if an anomaly is part of a broader market movement."""

import logging
from datetime import timedelta
from typing import Any
from sqlalchemy import and_
from sqlalchemy.orm import Session

from src.database.models import Price
from src.phase2_journalist.tools.base import AgentTool
from src.phase2_journalist.tools.models import (
    CheckMarketContextInput,
    CheckMarketContextOutput,
    MarketContext,
)

logger = logging.getLogger(__name__)


class CheckMarketContextTool(AgentTool):
    """Checks if an anomaly is isolated or part of a market-wide movement.

    Compares the target asset's price movement to reference assets (typically
    BTC and ETH) to determine if this is an asset-specific event or part of
    broader market movement.

    Example:
        SOL-USD drops 8%, BTC-USD drops 7%, ETH-USD drops 6%
        → "Market-wide correction, not isolated to SOL"

        DOGE-USD spikes 15%, BTC/ETH flat
        → "Isolated movement in DOGE, not market-wide"
    """

    name = "check_market_context"
    description = (
        "Check if other major cryptocurrencies (BTC, ETH) are also moving. "
        "Determines if the anomaly is asset-specific or part of a broader "
        "market movement. Helps distinguish 'Bitcoin drops 5%' from "
        "'Entire crypto market drops 5%'."
    )

    def __init__(self, session: Session | None = None):
        """Initialize the market context checker.

        Args:
            session: Optional SQLAlchemy session
        """
        self.session = session

    @classmethod
    def get_parameters_schema(cls) -> dict[str, Any]:
        """Get JSON schema for tool parameters."""
        return {
            "type": "object",
            "properties": {
                "target_symbol": {
                    "type": "string",
                    "description": "Symbol to check context for (e.g., 'SOL-USD')",
                },
                "reference_symbols": {
                    "type": "array",
                    "items": {"type": "string"},
                    "default": ["BTC-USD", "ETH-USD"],
                    "description": "Reference symbols to compare against (default: BTC, ETH)",
                },
                "timestamp": {
                    "type": "string",
                    "format": "date-time",
                    "description": "Timestamp to check market context around",
                },
                "window_minutes": {
                    "type": "integer",
                    "default": 10,
                    "description": "Time window around timestamp in minutes",
                },
            },
            "required": ["target_symbol", "timestamp"],
        }

    async def execute(self, **kwargs: Any) -> CheckMarketContextOutput:
        """Execute market context check.

        Args:
            target_symbol: Symbol to check context for
            reference_symbols: Symbols to compare against (default: ['BTC-USD', 'ETH-USD'])
            timestamp: Timestamp to check
            window_minutes: Time window around timestamp (default: 10)
            session: Optional SQLAlchemy session

        Returns:
            CheckMarketContextOutput with market correlation analysis
        """
        try:
            # Get session
            session = kwargs.get("session") or self.session
            if not session:
                return self._create_error_output(
                    "Database session is required", CheckMarketContextOutput
                )

            # Parse parameters
            target_symbol = kwargs.get("target_symbol")
            reference_symbols = kwargs.get("reference_symbols", ["BTC-USD", "ETH-USD"])
            timestamp = kwargs.get("timestamp")
            window_minutes = kwargs.get("window_minutes", 10)

            if not target_symbol or not timestamp:
                return self._create_error_output(
                    "symbol and timestamp are required", CheckMarketContextOutput
                )

            # Convert string timestamp if needed
            if isinstance(timestamp, str):
                from datetime import datetime

                timestamp = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))

            # Query price data around the timestamp
            start_time = timestamp - timedelta(minutes=window_minutes)
            end_time = timestamp + timedelta(minutes=window_minutes)

            # Helper function to get price change for a symbol
            def get_price_change(symbol: str) -> MarketContext:
                """Get price change for a symbol in the time window."""
                prices = (
                    session.query(Price)
                    .filter(
                        and_(
                            Price.symbol == symbol,
                            Price.timestamp >= start_time,
                            Price.timestamp <= end_time,
                        )
                    )
                    .order_by(Price.timestamp)
                    .all()
                )

                if len(prices) < 2:
                    return MarketContext(
                        symbol=symbol,
                        price_change_pct=None,
                        is_moving=False,
                        direction=None
                    )

                # Calculate price change
                first_price = prices[0].price
                last_price = prices[-1].price
                change_pct = ((last_price - first_price) / first_price) * 100

                # Determine if "moving" (> 1% change)
                is_moving = abs(change_pct) > 1.0
                direction = "up" if change_pct > 0 else "down" if change_pct < 0 else None

                return MarketContext(
                    symbol=symbol,
                    price_change_pct=change_pct,
                    is_moving=is_moving,
                    direction=direction
                )

            # Get price changes for all symbols
            target_context = get_price_change(target_symbol)
            reference_contexts = [get_price_change(ref_sym) for ref_sym in reference_symbols]

            # Determine if market-wide movement
            moving_references = [ctx for ctx in reference_contexts if ctx.is_moving]
            is_market_wide = len(moving_references) >= len(reference_symbols) / 2

            # Generate description
            if not target_context.is_moving:
                correlation_description = f"{target_symbol} not showing significant movement"
            elif is_market_wide:
                directions = [ctx.direction for ctx in moving_references if ctx.direction]
                same_direction = all(d == target_context.direction for d in directions)
                if same_direction:
                    correlation_description = (
                        f"Market-wide {target_context.direction}ward movement detected "
                        f"({', '.join(ctx.symbol for ctx in moving_references)} also moving)"
                    )
                else:
                    correlation_description = "Mixed market signals - some assets moving opposite directions"
            else:
                correlation_description = f"Isolated movement in {target_symbol}, reference assets stable"

            logger.info(f"Market context: {correlation_description}")

            return CheckMarketContextOutput(
                success=True,
                target_context=target_context,
                reference_contexts=reference_contexts,
                is_market_wide=is_market_wide,
                correlation_description=correlation_description,
            )

        except Exception as e:
            logger.error(f"Error in check_market_context: {e}")
            return self._create_error_output(str(e), CheckMarketContextOutput)
