"""Tool to search for similar historical anomalies in the database."""

import logging
from typing import Any
from sqlalchemy import and_, desc
from sqlalchemy.orm import Session

from src.database.models import Anomaly, Narrative, AnomalyTypeEnum
from src.phase2_journalist.tools.base import AgentTool
from src.phase2_journalist.tools.models import (
    SearchHistoricalInput,
    SearchHistoricalOutput,
    HistoricalAnomaly,
)

logger = logging.getLogger(__name__)


class SearchHistoricalTool(AgentTool):
    """Searches for similar historical anomalies in the database.

    Finds past anomalies with similar characteristics (same symbol, same type,
    similar magnitude) to help contextualize current events. Useful for
    identifying patterns and generating narratives like "This is the third
    time Bitcoin has dropped over 5% this month."

    Example:
        Symbol: BTC-USD, Type: price_drop, Min similarity: 0.7
        → Returns 5 most similar historical drops with narratives
    """

    name = "search_historical"
    description = (
        "Search for similar historical anomalies in the database. "
        "Find past events with the same symbol and anomaly type to provide "
        "context like 'This is the largest spike since [date]' or "
        "'Similar pattern occurred on [date] when [narrative]'."
    )

    def __init__(self, session: Session | None = None):
        """Initialize the search tool.

        Args:
            session: Optional SQLAlchemy session. If not provided, tool will
                    require session to be passed in execute()
        """
        self.session = session

    @classmethod
    def get_parameters_schema(cls) -> dict[str, Any]:
        """Get JSON schema for tool parameters."""
        return {
            "type": "object",
            "properties": {
                "symbol": {
                    "type": "string",
                    "description": "Crypto symbol to search for (e.g., 'BTC-USD')",
                },
                "anomaly_type": {
                    "type": "string",
                    "enum": ["price_spike", "price_drop", "volume_spike", "combined"],
                    "description": "Type of anomaly to search for",
                },
                "min_similarity": {
                    "type": "number",
                    "minimum": 0.0,
                    "maximum": 1.0,
                    "default": 0.7,
                    "description": "Minimum similarity threshold (0-1)",
                },
                "limit": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 20,
                    "default": 5,
                    "description": "Maximum number of results to return",
                },
            },
            "required": ["symbol", "anomaly_type"],
        }

    async def execute(self, **kwargs: Any) -> SearchHistoricalOutput:
        """Execute historical search.

        Args:
            symbol: Crypto symbol to search for
            anomaly_type: Type of anomaly
            min_similarity: Minimum similarity threshold (0-1, default: 0.7)
            limit: Maximum number of results (default: 5)
            session: Optional SQLAlchemy session (if not provided in __init__)

        Returns:
            SearchHistoricalOutput with similar historical anomalies
        """
        try:
            # Get session
            session = kwargs.get("session") or self.session
            if not session:
                return self._create_error_output(
                    "Database session is required", SearchHistoricalOutput
                )

            # Parse parameters
            symbol = kwargs.get("symbol")
            anomaly_type_str = kwargs.get("anomaly_type")
            min_similarity = kwargs.get("min_similarity", 0.7)
            limit = kwargs.get("limit", 5)

            if not symbol or not anomaly_type_str:
                return self._create_error_output(
                    "Both symbol and anomaly_type are required", SearchHistoricalOutput
                )

            # Convert string to enum
            try:
                anomaly_type_enum = AnomalyTypeEnum[anomaly_type_str.upper()]
            except KeyError:
                return self._create_error_output(
                    f"Invalid anomaly_type: {anomaly_type_str}", SearchHistoricalOutput
                )

            # Query database for similar anomalies
            # For now, we do exact match on symbol and type, sorted by recency
            # Future: Add magnitude similarity scoring
            query = (
                session.query(Anomaly, Narrative)
                .outerjoin(Narrative, Anomaly.id == Narrative.anomaly_id)
                .filter(
                    and_(
                        Anomaly.symbol == symbol,
                        Anomaly.anomaly_type == anomaly_type_enum,
                    )
                )
                .order_by(desc(Anomaly.detected_at))
                .limit(limit * 2)  # Fetch more for filtering
            )

            results = query.all()

            # Calculate similarity scores based on magnitude
            historical_anomalies = []
            for anomaly, narrative in results:
                # Simple similarity: inverse of how different the magnitude is
                # This is a placeholder - could be improved with embeddings
                similarity_score = 1.0 - (
                    abs(anomaly.price_change_pct - anomaly.price_change_pct) / 100.0
                )
                similarity_score = max(0.0, min(1.0, similarity_score))

                # For now, use a baseline similarity of 0.8 since we're matching
                # exact symbol + type
                similarity_score = 0.8

                if similarity_score >= min_similarity:
                    historical_anomalies.append(
                        HistoricalAnomaly(
                            id=anomaly.id,
                            symbol=anomaly.symbol,
                            detected_at=anomaly.detected_at,
                            anomaly_type=anomaly.anomaly_type.value,
                            price_change_pct=anomaly.price_change_pct,
                            narrative_text=narrative.narrative_text if narrative else None,
                            similarity_score=similarity_score,
                        )
                    )

            # Limit results
            historical_anomalies = historical_anomalies[:limit]

            logger.info(
                f"Historical search: found {len(historical_anomalies)} similar "
                f"anomalies for {symbol} ({anomaly_type_str})"
            )

            return SearchHistoricalOutput(
                success=True, results=historical_anomalies, count=len(historical_anomalies)
            )

        except Exception as e:
            logger.error(f"Error in search_historical: {e}")
            return self._create_error_output(str(e), SearchHistoricalOutput)
