"""Pydantic models for anomaly detection."""

from datetime import datetime
from pydantic import BaseModel, Field
from enum import Enum


class AnomalyType(str, Enum):
    """Types of anomalies."""

    PRICE_SPIKE = "price_spike"
    PRICE_DROP = "price_drop"
    VOLUME_SPIKE = "volume_spike"
    COMBINED = "combined"


class DetectedAnomaly(BaseModel):
    """Anomaly detection result."""

    symbol: str
    detected_at: datetime
    anomaly_type: AnomalyType

    # Statistical metrics
    z_score: float
    price_change_pct: float
    volume_change_pct: float = 0.0
    confidence: float = Field(ge=0.0, le=1.0)
    baseline_window_minutes: int

    # Price snapshot
    price_before: float
    price_at_detection: float
    volume_before: float = 0.0
    volume_at_detection: float = 0.0

    class Config:
        json_schema_extra = {
            "example": {
                "symbol": "BTC-USD",
                "detected_at": "2024-01-15T14:15:00Z",
                "anomaly_type": "price_drop",
                "z_score": -3.5,
                "price_change_pct": -5.2,
                "confidence": 0.95,
                "baseline_window_minutes": 60,
                "price_before": 45000.0,
                "price_at_detection": 42660.0,
            }
        }
