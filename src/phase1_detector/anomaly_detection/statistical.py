"""Statistical anomaly detection algorithms."""

from datetime import datetime, timedelta
from typing import List, Optional
import numpy as np
from scipy import stats
import pandas as pd

from .models import DetectedAnomaly, AnomalyType
from config.settings import settings


class ZScoreDetector:
    """Detect anomalies using Z-score on price returns."""

    def __init__(self, threshold: float = 3.0, window_minutes: int = 60):
        """Initialize Z-score detector.

        Args:
            threshold: Z-score threshold for anomaly detection (default: 3.0)
            window_minutes: Lookback window in minutes (default: 60)
        """
        self.threshold = threshold
        self.window_minutes = window_minutes

    def detect(
        self, prices: pd.DataFrame, current_time: Optional[datetime] = None
    ) -> List[DetectedAnomaly]:
        """Detect price anomalies using Z-score.

        Args:
            prices: DataFrame with columns [timestamp, price, volume]
            current_time: Time to check for anomaly (default: latest)

        Returns:
            List of detected anomalies
        """
        if len(prices) < 2:
            return []

        # Calculate returns
        prices = prices.sort_values("timestamp")
        prices["returns"] = prices["price"].pct_change() * 100  # Percentage returns

        # Get window for baseline
        if current_time is None:
            current_time = prices["timestamp"].iloc[-1]

        window_start = current_time - timedelta(minutes=self.window_minutes)
        window_data = prices[
            (prices["timestamp"] >= window_start) & (prices["timestamp"] <= current_time)
        ]

        if len(window_data) < 3:
            return []

        # Calculate Z-score for latest return
        returns = window_data["returns"].dropna()
        if len(returns) < 2:
            return []

        latest_return = returns.iloc[-1]
        mean_return = returns.iloc[:-1].mean()
        std_return = returns.iloc[:-1].std()

        if std_return == 0:
            return []

        z_score = (latest_return - mean_return) / std_return

        # Check if anomaly
        if abs(z_score) > self.threshold:
            latest_idx = window_data.index[-1]
            prev_idx = window_data.index[-2]

            anomaly_type = (
                AnomalyType.PRICE_SPIKE if z_score > 0 else AnomalyType.PRICE_DROP
            )

            return [
                DetectedAnomaly(
                    symbol=prices.iloc[0].get("symbol", "UNKNOWN"),
                    detected_at=window_data.loc[latest_idx, "timestamp"],
                    anomaly_type=anomaly_type,
                    z_score=z_score,
                    price_change_pct=latest_return,
                    confidence=min(abs(z_score) / 5.0, 1.0),  # Cap at 1.0
                    baseline_window_minutes=self.window_minutes,
                    price_before=prices.loc[prev_idx, "price"],
                    price_at_detection=prices.loc[latest_idx, "price"],
                    volume_before=prices.loc[prev_idx, "volume"],
                    volume_at_detection=prices.loc[latest_idx, "volume"],
                )
            ]

        return []


class BollingerBandDetector:
    """Detect anomalies using Bollinger Bands."""

    def __init__(self, window: int = 20, std_multiplier: float = 2.0):
        """Initialize Bollinger Band detector.

        Args:
            window: Rolling window size for SMA (default: 20 periods)
            std_multiplier: Standard deviation multiplier (default: 2.0)
        """
        self.window = window
        self.std_multiplier = std_multiplier

    def detect(
        self, prices: pd.DataFrame, current_time: Optional[datetime] = None
    ) -> List[DetectedAnomaly]:
        """Detect price anomalies using Bollinger Bands.

        Args:
            prices: DataFrame with columns [timestamp, price, volume]
            current_time: Time to check for anomaly (default: latest)

        Returns:
            List of detected anomalies
        """
        if len(prices) < self.window:
            return []

        prices = prices.sort_values("timestamp")

        # Calculate Bollinger Bands
        prices["sma"] = prices["price"].rolling(window=self.window).mean()
        prices["std"] = prices["price"].rolling(window=self.window).std()
        prices["upper_band"] = prices["sma"] + (self.std_multiplier * prices["std"])
        prices["lower_band"] = prices["sma"] - (self.std_multiplier * prices["std"])

        # Get current price
        if current_time:
            current_data = prices[prices["timestamp"] <= current_time].iloc[-1]
        else:
            current_data = prices.iloc[-1]

        current_price = current_data["price"]
        upper_band = current_data["upper_band"]
        lower_band = current_data["lower_band"]
        sma = current_data["sma"]

        # Check for breakout
        if pd.isna(upper_band) or pd.isna(lower_band):
            return []

        anomalies = []

        if current_price > upper_band:
            # Price spike
            price_change_pct = ((current_price - sma) / sma) * 100
            anomalies.append(
                DetectedAnomaly(
                    symbol=prices.iloc[0].get("symbol", "UNKNOWN"),
                    detected_at=current_data["timestamp"],
                    anomaly_type=AnomalyType.PRICE_SPIKE,
                    z_score=(current_price - sma) / current_data["std"],
                    price_change_pct=price_change_pct,
                    confidence=min((current_price - upper_band) / upper_band, 1.0),
                    baseline_window_minutes=self.window,
                    price_before=sma,
                    price_at_detection=current_price,
                    volume_before=prices["volume"].rolling(self.window).mean().iloc[-1],
                    volume_at_detection=current_data["volume"],
                )
            )
        elif current_price < lower_band:
            # Price drop
            price_change_pct = ((current_price - sma) / sma) * 100
            anomalies.append(
                DetectedAnomaly(
                    symbol=prices.iloc[0].get("symbol", "UNKNOWN"),
                    detected_at=current_data["timestamp"],
                    anomaly_type=AnomalyType.PRICE_DROP,
                    z_score=(current_price - sma) / current_data["std"],
                    price_change_pct=price_change_pct,
                    confidence=min((lower_band - current_price) / lower_band, 1.0),
                    baseline_window_minutes=self.window,
                    price_before=sma,
                    price_at_detection=current_price,
                    volume_before=prices["volume"].rolling(self.window).mean().iloc[-1],
                    volume_at_detection=current_data["volume"],
                )
            )

        return anomalies


class VolumeSpikeDetector:
    """Detect unusual trading volume."""

    def __init__(self, threshold: float = 2.5, window_minutes: int = 60):
        """Initialize volume spike detector.

        Args:
            threshold: Z-score threshold for volume (default: 2.5)
            window_minutes: Lookback window in minutes (default: 60)
        """
        self.threshold = threshold
        self.window_minutes = window_minutes

    def detect(
        self, prices: pd.DataFrame, current_time: Optional[datetime] = None
    ) -> List[DetectedAnomaly]:
        """Detect volume anomalies.

        Args:
            prices: DataFrame with columns [timestamp, price, volume]
            current_time: Time to check for anomaly (default: latest)

        Returns:
            List of detected anomalies
        """
        if len(prices) < 2:
            return []

        prices = prices.sort_values("timestamp")

        if current_time is None:
            current_time = prices["timestamp"].iloc[-1]

        window_start = current_time - timedelta(minutes=self.window_minutes)
        window_data = prices[
            (prices["timestamp"] >= window_start) & (prices["timestamp"] <= current_time)
        ]

        if len(window_data) < 3:
            return []

        volumes = window_data["volume"].dropna()
        if len(volumes) < 2:
            return []

        current_volume = volumes.iloc[-1]
        mean_volume = volumes.iloc[:-1].mean()
        std_volume = volumes.iloc[:-1].std()

        if std_volume == 0:
            return []

        volume_z_score = (current_volume - mean_volume) / std_volume

        if volume_z_score > self.threshold:
            latest_idx = window_data.index[-1]

            return [
                DetectedAnomaly(
                    symbol=prices.iloc[0].get("symbol", "UNKNOWN"),
                    detected_at=window_data.loc[latest_idx, "timestamp"],
                    anomaly_type=AnomalyType.VOLUME_SPIKE,
                    z_score=volume_z_score,
                    price_change_pct=0.0,
                    volume_change_pct=((current_volume - mean_volume) / mean_volume) * 100,
                    confidence=min(volume_z_score / 5.0, 1.0),
                    baseline_window_minutes=self.window_minutes,
                    price_before=prices.loc[latest_idx - 1, "price"] if latest_idx > 0 else 0.0,
                    price_at_detection=prices.loc[latest_idx, "price"],
                    volume_before=mean_volume,
                    volume_at_detection=current_volume,
                )
            ]

        return []


class CombinedDetector:
    """Combine price and volume anomalies for higher confidence."""

    def __init__(
        self,
        price_threshold: float = 2.0,
        volume_threshold: float = 2.0,
        window_minutes: int = 60,
    ):
        """Initialize combined detector.

        Args:
            price_threshold: Z-score threshold for price (default: 2.0)
            volume_threshold: Z-score threshold for volume (default: 2.0)
            window_minutes: Lookback window in minutes (default: 60)
        """
        self.price_detector = ZScoreDetector(price_threshold, window_minutes)
        self.volume_detector = VolumeSpikeDetector(volume_threshold, window_minutes)

    def detect(
        self, prices: pd.DataFrame, current_time: Optional[datetime] = None
    ) -> List[DetectedAnomaly]:
        """Detect combined price + volume anomalies.

        Args:
            prices: DataFrame with columns [timestamp, price, volume]
            current_time: Time to check for anomaly (default: latest)

        Returns:
            List of detected anomalies
        """
        price_anomalies = self.price_detector.detect(prices, current_time)
        volume_anomalies = self.volume_detector.detect(prices, current_time)

        # If both price and volume anomalies detected, merge them
        if price_anomalies and volume_anomalies:
            price_anom = price_anomalies[0]
            volume_anom = volume_anomalies[0]

            # Create combined anomaly with higher confidence
            return [
                DetectedAnomaly(
                    symbol=price_anom.symbol,
                    detected_at=price_anom.detected_at,
                    anomaly_type=AnomalyType.COMBINED,
                    z_score=price_anom.z_score,
                    price_change_pct=price_anom.price_change_pct,
                    volume_change_pct=volume_anom.volume_change_pct,
                    confidence=min((price_anom.confidence + volume_anom.confidence) / 2 * 1.5, 1.0),
                    baseline_window_minutes=price_anom.baseline_window_minutes,
                    price_before=price_anom.price_before,
                    price_at_detection=price_anom.price_at_detection,
                    volume_before=volume_anom.volume_before,
                    volume_at_detection=volume_anom.volume_at_detection,
                )
            ]

        return []


class AnomalyDetector:
    """Main anomaly detector orchestrating multiple detection strategies."""

    def __init__(self):
        """Initialize detector with settings from config."""
        self.z_score_detector = ZScoreDetector(
            threshold=settings.detection.z_score_threshold,
            window_minutes=settings.detection.lookback_window_minutes,
        )
        self.bollinger_detector = BollingerBandDetector(
            window=20, std_multiplier=settings.detection.bollinger_std_multiplier
        )
        self.volume_detector = VolumeSpikeDetector(
            threshold=settings.detection.volume_z_threshold,
            window_minutes=settings.detection.lookback_window_minutes,
        )
        self.combined_detector = CombinedDetector(
            price_threshold=2.0,
            volume_threshold=2.0,
            window_minutes=settings.detection.lookback_window_minutes,
        )

    def detect_all(
        self, prices: pd.DataFrame, current_time: Optional[datetime] = None
    ) -> List[DetectedAnomaly]:
        """Run all detectors and return unique anomalies.

        Args:
            prices: DataFrame with columns [timestamp, price, volume]
            current_time: Time to check for anomaly (default: latest)

        Returns:
            List of detected anomalies (deduplicated, prioritizing combined)
        """
        # Check combined first (highest confidence)
        combined = self.combined_detector.detect(prices, current_time)
        if combined:
            return combined

        # Check individual detectors
        anomalies = []
        anomalies.extend(self.z_score_detector.detect(prices, current_time))
        anomalies.extend(self.bollinger_detector.detect(prices, current_time))
        anomalies.extend(self.volume_detector.detect(prices, current_time))

        # Return highest confidence anomaly
        if anomalies:
            return [max(anomalies, key=lambda a: a.confidence)]

        return []
