"""Statistical anomaly detection algorithms."""

from datetime import datetime, timedelta
from typing import List, Optional
import numpy as np
from scipy import stats
import pandas as pd

from .models import DetectedAnomaly, AnomalyType
from .asset_profiles import AssetProfileManager
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


class MultiTimeframeDetector:
    """Detect anomalies across multiple timeframes using cumulative returns.

    Addresses minute-by-minute myopia by:
    1. Calculating cumulative returns over multiple windows (5/15/30/60 minutes)
    2. Using adaptive baselines that exclude the current move
    3. Detecting "slow burns" that appear normal minute-by-minute
    """

    def __init__(
        self,
        threshold: float = 3.0,
        timeframe_windows: Optional[List[int]] = None,
        baseline_multiplier: int = 3,
    ):
        """Initialize multi-timeframe detector.

        Args:
            threshold: Z-score threshold for anomaly detection
            timeframe_windows: List of timeframe windows in minutes (default: [5, 15, 30, 60])
            baseline_multiplier: Baseline window = timeframe × multiplier (default: 3)
        """
        self.threshold = threshold
        self.timeframe_windows = timeframe_windows or [5, 15, 30, 60]
        self.baseline_multiplier = baseline_multiplier

    def detect(
        self, prices: pd.DataFrame, current_time: Optional[datetime] = None
    ) -> List[DetectedAnomaly]:
        """Detect cumulative anomalies across multiple timeframes.

        Algorithm (per timeframe):
        1. Calculate cumulative return over window (e.g., 10 minutes: price_t0 to price_t10)
        2. Baseline = 3× window duration, excluding current window (e.g., t-40min to t-10min)
        3. Z-score = (cumulative_return - baseline_mean) / baseline_std
        4. Detect if Z-score > asset_threshold

        Args:
            prices: DataFrame with columns [timestamp, price, volume, symbol]
            current_time: Time to check for anomaly (default: latest)

        Returns:
            List with single highest-confidence anomaly (if any)
        """
        if len(prices) < 5:
            return []

        prices = prices.sort_values("timestamp")

        if current_time is None:
            current_time = prices["timestamp"].iloc[-1]

        # Try each timeframe, collect anomalies
        anomalies = []
        for window_minutes in self.timeframe_windows:
            anomaly = self._detect_for_timeframe(prices, current_time, window_minutes)
            if anomaly:
                anomalies.append(anomaly)

        # Return highest confidence anomaly
        if anomalies:
            return [max(anomalies, key=lambda a: a.confidence)]

        return []

    def _detect_for_timeframe(
        self, prices: pd.DataFrame, current_time: datetime, window_minutes: int
    ) -> Optional[DetectedAnomaly]:
        """Detect anomaly for a specific timeframe window.

        Args:
            prices: DataFrame with price data
            current_time: Current timestamp
            window_minutes: Timeframe window size in minutes

        Returns:
            DetectedAnomaly if detected, None otherwise
        """
        # Calculate window boundaries
        window_start = current_time - timedelta(minutes=window_minutes)
        baseline_window = window_minutes * self.baseline_multiplier
        baseline_start = current_time - timedelta(minutes=baseline_window)
        baseline_end = window_start  # Exclude current move from baseline

        # Get data for current window and baseline
        current_window_data = prices[
            (prices["timestamp"] >= window_start) & (prices["timestamp"] <= current_time)
        ]
        baseline_data = prices[
            (prices["timestamp"] >= baseline_start) & (prices["timestamp"] < baseline_end)
        ]

        # Need at least 3 periods in current window and sufficient baseline data
        if len(current_window_data) < 3 or len(baseline_data) < window_minutes:
            return None

        # Calculate cumulative return for current window
        price_at_start = current_window_data["price"].iloc[0]
        price_at_end = current_window_data["price"].iloc[-1]
        cumulative_return = ((price_at_end - price_at_start) / price_at_start) * 100

        # Calculate baseline cumulative returns (rolling windows)
        baseline_returns = []
        for i in range(len(baseline_data) - window_minutes + 1):
            window_slice = baseline_data.iloc[i : i + window_minutes]
            if len(window_slice) >= 2:
                start_price = window_slice["price"].iloc[0]
                end_price = window_slice["price"].iloc[-1]
                ret = ((end_price - start_price) / start_price) * 100
                baseline_returns.append(ret)

        if len(baseline_returns) < 2:
            return None

        # Calculate Z-score
        baseline_mean = np.mean(baseline_returns)
        baseline_std = np.std(baseline_returns)

        if baseline_std == 0:
            return None

        z_score = (cumulative_return - baseline_mean) / baseline_std

        # Check if anomaly
        if abs(z_score) > self.threshold:
            symbol = prices.iloc[0].get("symbol", "UNKNOWN")
            anomaly_type = AnomalyType.PRICE_SPIKE if z_score > 0 else AnomalyType.PRICE_DROP

            # Calculate average volume change over window
            baseline_avg_volume = baseline_data["volume"].mean()
            current_avg_volume = current_window_data["volume"].mean()
            volume_change_pct = (
                ((current_avg_volume - baseline_avg_volume) / baseline_avg_volume) * 100
                if baseline_avg_volume > 0
                else 0.0
            )

            return DetectedAnomaly(
                symbol=symbol,
                detected_at=current_time,
                anomaly_type=anomaly_type,
                z_score=z_score,
                price_change_pct=cumulative_return,
                volume_change_pct=volume_change_pct,
                confidence=min(abs(z_score) / 5.0, 1.0),
                baseline_window_minutes=baseline_window,
                price_before=price_at_start,
                price_at_detection=price_at_end,
                volume_before=baseline_avg_volume,
                volume_at_detection=current_avg_volume,
                detection_metadata={
                    "timeframe_minutes": window_minutes,
                    "cumulative_return": round(cumulative_return, 2),
                    "baseline_mean": round(baseline_mean, 2),
                    "baseline_std": round(baseline_std, 2),
                    "detector": "multi_timeframe",
                },
            )

        return None


class AnomalyDetector:
    """Main anomaly detector orchestrating multiple detection strategies.

    Features:
    - Multi-timeframe detection (cumulative returns across 5/15/30/60 minutes)
    - Asset-aware thresholds (BTC vs DOGE use different thresholds)
    - Backward compatible with legacy detectors
    """

    def __init__(self):
        """Initialize detector with settings from config."""
        # Load asset profile manager for threshold lookup
        self.profile_manager = None
        if settings.detection.use_asset_specific_thresholds:
            try:
                self.profile_manager = AssetProfileManager(
                    settings.detection.thresholds_config_path
                )
            except Exception as e:
                print(f"Warning: Failed to load asset profiles: {e}")
                self.profile_manager = None

        # Initialize multi-timeframe detector (if enabled)
        self.multi_timeframe_detector = None
        if settings.detection.enable_multi_timeframe and self.profile_manager:
            tf_config = self.profile_manager.get_timeframe_config()
            if tf_config["enabled"]:
                self.multi_timeframe_detector = MultiTimeframeDetector(
                    threshold=settings.detection.z_score_threshold,
                    timeframe_windows=tf_config["windows"],
                    baseline_multiplier=tf_config["baseline_multiplier"],
                )

        # Legacy detectors (backward compatibility)
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

        Priority detection order:
        1. MultiTimeframeDetector (if enabled) - detects slow burns
        2. CombinedDetector (price + volume) - highest confidence
        3. Individual detectors (Z-score, Bollinger, Volume) - fallback

        Asset-specific thresholds are applied dynamically based on symbol.

        Args:
            prices: DataFrame with columns [timestamp, price, volume, symbol]
            current_time: Time to check for anomaly (default: latest)

        Returns:
            List of detected anomalies (deduplicated, single highest confidence)
        """
        # Extract symbol from DataFrame
        symbol = prices.iloc[0].get("symbol", "UNKNOWN") if len(prices) > 0 else "UNKNOWN"

        # Get asset-specific thresholds
        asset_thresholds = None
        if self.profile_manager:
            asset_thresholds = self.profile_manager.get_thresholds(symbol)

        # Priority 1: Multi-timeframe detector (if enabled)
        if self.multi_timeframe_detector and asset_thresholds:
            # Update threshold dynamically
            self.multi_timeframe_detector.threshold = asset_thresholds.z_score_threshold
            multi_tf = self.multi_timeframe_detector.detect(prices, current_time)
            if multi_tf:
                # Enrich with asset metadata
                anomaly = multi_tf[0]
                anomaly.detection_metadata.update(
                    {
                        "volatility_tier": asset_thresholds.volatility_tier,
                        "asset_threshold": asset_thresholds.z_score_threshold,
                        "threshold_source": asset_thresholds.source,
                    }
                )
                return [anomaly]

        # Priority 2: Combined detector (price + volume)
        if asset_thresholds:
            # Update thresholds dynamically
            self.combined_detector.price_detector.threshold = asset_thresholds.z_score_threshold
            self.combined_detector.volume_detector.threshold = asset_thresholds.volume_z_threshold

        combined = self.combined_detector.detect(prices, current_time)
        if combined:
            anomaly = combined[0]
            if asset_thresholds:
                anomaly.detection_metadata = {
                    "volatility_tier": asset_thresholds.volatility_tier,
                    "asset_threshold": asset_thresholds.z_score_threshold,
                    "threshold_source": asset_thresholds.source,
                    "detector": "combined",
                }
            return combined

        # Priority 3: Individual detectors
        if asset_thresholds:
            self.z_score_detector.threshold = asset_thresholds.z_score_threshold
            self.volume_detector.threshold = asset_thresholds.volume_z_threshold
            # Note: Bollinger uses std_multiplier, not z_score threshold directly

        anomalies = []
        anomalies.extend(self.z_score_detector.detect(prices, current_time))

        # Only include Bollinger if Z-score meets asset threshold
        bollinger_anomalies = self.bollinger_detector.detect(prices, current_time)
        if bollinger_anomalies and asset_thresholds:
            # Filter Bollinger anomalies by asset threshold
            filtered_bollinger = [
                a for a in bollinger_anomalies
                if abs(a.z_score) >= asset_thresholds.z_score_threshold
            ]
            anomalies.extend(filtered_bollinger)
        else:
            anomalies.extend(bollinger_anomalies)

        anomalies.extend(self.volume_detector.detect(prices, current_time))

        # Enrich with asset metadata and return highest confidence
        if anomalies:
            anomaly = max(anomalies, key=lambda a: a.confidence)
            if asset_thresholds:
                anomaly.detection_metadata = {
                    "volatility_tier": asset_thresholds.volatility_tier,
                    "asset_threshold": asset_thresholds.z_score_threshold,
                    "threshold_source": asset_thresholds.source,
                    "detector": anomaly.anomaly_type.value,
                }
            return [anomaly]

        return []
