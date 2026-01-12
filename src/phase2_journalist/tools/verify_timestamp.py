"""Tool to verify if news could have caused an anomaly based on timing."""

import logging
from datetime import datetime
from typing import Any

from src.phase2_journalist.tools.base import AgentTool
from src.phase2_journalist.tools.models import VerifyTimestampInput, VerifyTimestampOutput

logger = logging.getLogger(__name__)


class VerifyTimestampTool(AgentTool):
    """Verifies if news timing is consistent with causality.

    Checks whether a news article was published before or after an anomaly,
    helping determine if the news could have caused the price movement or
    merely reported on it after the fact.

    Example:
        News at 14:05, anomaly at 14:10 → causal (pre_event)
        News at 14:15, anomaly at 14:10 → not causal (post_event)
    """

    name = "verify_timestamp"
    description = (
        "Verify if news timing is consistent with causality. "
        "Checks if news was published BEFORE the anomaly (could have caused it) "
        "or AFTER (merely reporting on it). Returns timing relationship and "
        "time difference in minutes."
    )

    @classmethod
    def get_parameters_schema(cls) -> dict[str, Any]:
        """Get JSON schema for tool parameters."""
        return {
            "type": "object",
            "properties": {
                "news_timestamp": {
                    "type": "string",
                    "format": "date-time",
                    "description": "ISO 8601 timestamp when the news was published",
                },
                "anomaly_timestamp": {
                    "type": "string",
                    "format": "date-time",
                    "description": "ISO 8601 timestamp when the anomaly was detected",
                },
                "threshold_minutes": {
                    "type": "integer",
                    "description": "Maximum minutes before anomaly to consider causal (default: 30)",
                    "default": 30,
                },
            },
            "required": ["news_timestamp", "anomaly_timestamp"],
        }

    async def execute(self, **kwargs: Any) -> VerifyTimestampOutput:
        """Execute timestamp verification.

        Args:
            news_timestamp: When news was published (str or datetime)
            anomaly_timestamp: When anomaly was detected (str or datetime)
            threshold_minutes: Time window to consider causal (default: 30)

        Returns:
            VerifyTimestampOutput with timing analysis
        """
        try:
            # Parse input parameters
            news_ts = kwargs.get("news_timestamp")
            anomaly_ts = kwargs.get("anomaly_timestamp")
            threshold_minutes = kwargs.get("threshold_minutes", 30)

            # Convert strings to datetime if needed
            if isinstance(news_ts, str):
                news_ts = datetime.fromisoformat(news_ts.replace("Z", "+00:00"))
            if isinstance(anomaly_ts, str):
                anomaly_ts = datetime.fromisoformat(anomaly_ts.replace("Z", "+00:00"))

            if not news_ts or not anomaly_ts:
                return self._create_error_output(
                    "Both news_timestamp and anomaly_timestamp are required",
                    VerifyTimestampOutput,
                )

            # Calculate time difference (negative = news before anomaly)
            time_diff = (news_ts - anomaly_ts).total_seconds() / 60.0

            # Determine causality
            # News published BEFORE anomaly = could have caused it
            # News published AFTER anomaly = merely reporting
            is_causal = time_diff < 0 and abs(time_diff) <= threshold_minutes

            # Determine timing tag
            timing_tag = "pre_event" if time_diff < 0 else "post_event"

            logger.info(
                f"Timestamp verification: news {time_diff:.1f}m relative to anomaly "
                f"(causal={is_causal}, tag={timing_tag})"
            )

            return VerifyTimestampOutput(
                success=True,
                is_causal=is_causal,
                time_diff_minutes=time_diff,
                timing_tag=timing_tag,
            )

        except Exception as e:
            logger.error(f"Error in verify_timestamp: {e}")
            return self._create_error_output(str(e), VerifyTimestampOutput)
