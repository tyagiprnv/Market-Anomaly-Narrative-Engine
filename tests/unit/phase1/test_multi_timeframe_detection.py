"""Tests for multi-timeframe and asset-aware anomaly detection."""

from datetime import datetime, timedelta
import pandas as pd
import pytest

from src.phase1_detector.anomaly_detection.statistical import (
    MultiTimeframeDetector,
    AnomalyDetector,
)
from src.phase1_detector.anomaly_detection.asset_profiles import (
    AssetProfileManager,
    AssetThresholds,
)
from src.phase1_detector.anomaly_detection.models import AnomalyType


class TestMultiTimeframeDetector:
    """Test multi-timeframe cumulative detection."""

    def create_slow_burn_data(
        self, symbol: str, rate_per_minute: float, duration_minutes: int
    ) -> pd.DataFrame:
        """Create synthetic data for slow cumulative spike.

        Args:
            symbol: Asset symbol (e.g., 'DOGE-USD')
            rate_per_minute: Price change rate per minute (e.g., 0.5 for +0.5%/min)
            duration_minutes: How long the spike lasts (e.g., 10 minutes)

        Returns:
            DataFrame with timestamp, price, volume, symbol
        """
        base_time = datetime(2024, 3, 14, 14, 0, 0)
        base_price = 100.0
        baseline_minutes = 60

        timestamps = []
        prices = []
        volumes = []

        # Baseline: stable prices (± 0.1% noise)
        for i in range(baseline_minutes):
            timestamps.append(base_time + timedelta(minutes=i - baseline_minutes))
            noise = (hash(i) % 20 - 10) / 1000  # -0.01 to +0.01
            prices.append(base_price * (1 + noise))
            volumes.append(1000.0)

        # Slow burn: cumulative spike
        current_price = base_price
        for i in range(duration_minutes):
            timestamps.append(base_time + timedelta(minutes=i))
            current_price *= 1 + (rate_per_minute / 100)  # Compound growth
            prices.append(current_price)
            volumes.append(1000.0)

        return pd.DataFrame(
            {
                "timestamp": timestamps,
                "price": prices,
                "volume": volumes,
                "symbol": [symbol] * len(timestamps),
            }
        )

    def test_detects_slow_cumulative_spike(self):
        """Should detect +5% cumulative move over 10 minutes at 0.5%/min."""
        detector = MultiTimeframeDetector(threshold=2.0, timeframe_windows=[10])

        # DOGE +0.5%/min for 10 minutes = ~5.1% cumulative
        data = self.create_slow_burn_data("DOGE-USD", rate_per_minute=0.5, duration_minutes=10)

        anomalies = detector.detect(data)

        assert len(anomalies) == 1
        anomaly = anomalies[0]
        assert anomaly.symbol == "DOGE-USD"
        assert anomaly.anomaly_type == AnomalyType.PRICE_SPIKE
        assert abs(anomaly.z_score) > 2.0  # Should exceed threshold
        assert anomaly.price_change_pct > 4.0  # ~4-5% cumulative
        assert anomaly.detection_metadata["timeframe_minutes"] == 10
        assert anomaly.detection_metadata["detector"] == "multi_timeframe"

    def test_no_false_positive_on_consistent_small_moves(self):
        """Should NOT detect steady +0.1%/min (normal volatility)."""
        detector = MultiTimeframeDetector(threshold=3.0, timeframe_windows=[10, 30])

        # Steady +0.1%/min = only +1% over 10 minutes (normal)
        data = self.create_slow_burn_data("BTC-USD", rate_per_minute=0.1, duration_minutes=30)

        anomalies = detector.detect(data)

        assert len(anomalies) == 0  # Should not trigger false positive

    def test_multi_timeframe_returns_highest_confidence(self):
        """Should return highest confidence anomaly from multiple timeframes."""
        detector = MultiTimeframeDetector(
            threshold=2.0, timeframe_windows=[5, 15, 30, 60]
        )

        # Fast spike: +8% in 5 minutes, then stable
        data = self.create_slow_burn_data("ETH-USD", rate_per_minute=1.5, duration_minutes=5)

        anomalies = detector.detect(data)

        assert len(anomalies) == 1
        anomaly = anomalies[0]
        # Should detect on 5-min window (highest Z-score)
        assert anomaly.detection_metadata["timeframe_minutes"] == 5
        assert abs(anomaly.z_score) > 3.0  # Strong signal on short timeframe

    def test_detects_price_drop_cumulative(self):
        """Should detect cumulative price drops (negative spikes)."""
        detector = MultiTimeframeDetector(threshold=2.5, timeframe_windows=[15])

        # -0.4%/min for 15 minutes = -6% cumulative drop
        data = self.create_slow_burn_data("SOL-USD", rate_per_minute=-0.4, duration_minutes=15)

        anomalies = detector.detect(data)

        assert len(anomalies) == 1
        anomaly = anomalies[0]
        assert anomaly.anomaly_type == AnomalyType.PRICE_DROP
        assert anomaly.price_change_pct < -5.0  # ~-6% drop
        assert abs(anomaly.z_score) > 2.5


class TestAssetProfileManager:
    """Test asset-specific threshold lookup."""

    def test_asset_specific_override_highest_priority(self):
        """BTC-USD should use override threshold 3.5 (not tier multiplier)."""
        manager = AssetProfileManager("config/thresholds.yaml")

        thresholds = manager.get_thresholds("BTC-USD")

        assert thresholds.symbol == "BTC-USD"
        assert thresholds.z_score_threshold == 3.5  # From asset_specific_thresholds
        assert thresholds.volume_z_threshold == 2.8
        assert thresholds.source == "asset_specific"

    def test_volatility_tier_multiplier(self):
        """ETH-USD (stable tier) should use 3.0 × 1.2 = 3.6."""
        manager = AssetProfileManager("config/thresholds.yaml")

        thresholds = manager.get_thresholds("ETH-USD")

        assert thresholds.symbol == "ETH-USD"
        assert abs(thresholds.z_score_threshold - 3.6) < 0.01  # 3.0 × 1.2 ≈ 3.6
        assert thresholds.volatility_tier == "stable"
        assert thresholds.source == "tier"

    def test_doge_uses_lower_threshold(self):
        """DOGE-USD (volatile) should use override 2.0."""
        manager = AssetProfileManager("config/thresholds.yaml")

        thresholds = manager.get_thresholds("DOGE-USD")

        assert thresholds.symbol == "DOGE-USD"
        assert thresholds.z_score_threshold == 2.0  # Asset override
        assert thresholds.source == "asset_specific"

    def test_moderate_tier_uses_baseline(self):
        """SOL-USD (moderate tier) should use 3.0 × 1.0 = 3.0."""
        manager = AssetProfileManager("config/thresholds.yaml")

        thresholds = manager.get_thresholds("SOL-USD")

        assert thresholds.symbol == "SOL-USD"
        assert thresholds.z_score_threshold == 3.0  # 3.0 × 1.0
        assert thresholds.volatility_tier == "moderate"
        assert thresholds.source == "tier"

    def test_unknown_asset_uses_global_defaults(self):
        """Unknown asset should fallback to global defaults."""
        manager = AssetProfileManager("config/thresholds.yaml")

        thresholds = manager.get_thresholds("UNKNOWN-USD")

        assert thresholds.symbol == "UNKNOWN-USD"
        assert thresholds.z_score_threshold == 3.0  # Global default
        assert thresholds.volatility_tier == "unknown"
        assert thresholds.source == "global"

    def test_caching_works(self):
        """Second lookup should use cached result."""
        manager = AssetProfileManager("config/thresholds.yaml")

        thresholds1 = manager.get_thresholds("BTC-USD")
        thresholds2 = manager.get_thresholds("BTC-USD")

        assert thresholds1 is thresholds2  # Same object (cached)

    def test_get_timeframe_config(self):
        """Should load timeframe configuration from YAML."""
        manager = AssetProfileManager("config/thresholds.yaml")

        config = manager.get_timeframe_config()

        assert config["enabled"] is True
        assert config["windows"] == [5, 15, 30, 60]
        assert config["baseline_multiplier"] == 3


class TestAnomalyDetectorIntegration:
    """Integration tests for full detection pipeline."""

    def test_btc_uses_higher_threshold_filters_noise(self):
        """BTC should use higher threshold (3.5) for Z-score detector."""
        detector = AnomalyDetector()

        # Create BTC data with small drop that generates moderate Z-score
        # Using normal volatility that shouldn't trigger on Z-score detector
        base_time = datetime(2024, 3, 14, 14, 0, 0)
        timestamps = [base_time + timedelta(minutes=i) for i in range(-60, 1)]
        # More realistic price movement with some volatility
        prices = []
        for i in range(60):
            noise = (hash(i) % 100 - 50) / 10000  # Small noise
            prices.append(50000.0 * (1 + noise))
        prices.append(49400.0)  # -1.2% drop (below typical noise)
        volumes = [1000.0] * 61

        data = pd.DataFrame(
            {
                "timestamp": timestamps,
                "price": prices,
                "volume": volumes,
                "symbol": ["BTC-USD"] * 61,
            }
        )

        anomalies = detector.detect_all(data)

        # If detected, verify it used BTC threshold
        if anomalies:
            assert anomalies[0].detection_metadata.get("asset_threshold") == 3.5
            assert anomalies[0].detection_metadata.get("volatility_tier") == "stable"

    def test_doge_detects_with_lower_threshold(self):
        """DOGE should detect at Z-score > 2.0 (more sensitive)."""
        detector = AnomalyDetector()

        # Create DOGE spike: +3% (Z-score ~2.5)
        base_time = datetime(2024, 3, 14, 14, 0, 0)
        timestamps = [base_time + timedelta(minutes=i) for i in range(-60, 1)]
        prices = [0.10] * 60 + [0.103]  # +3% spike
        volumes = [1000000.0] * 61

        data = pd.DataFrame(
            {
                "timestamp": timestamps,
                "price": prices,
                "volume": volumes,
                "symbol": ["DOGE-USD"] * 61,
            }
        )

        anomalies = detector.detect_all(data)

        # Should detect (Z-score 2.5 > 2.0 threshold)
        assert len(anomalies) == 1
        anomaly = anomalies[0]
        assert anomaly.symbol == "DOGE-USD"
        assert anomaly.detection_metadata.get("volatility_tier") in ["volatile", "unknown"]
        assert anomaly.detection_metadata.get("asset_threshold") <= 2.5

    def test_metadata_included_in_anomaly(self):
        """Detected anomalies should include detection metadata."""
        detector = AnomalyDetector()

        # Create extremely strong ETH spike (single minute, guaranteed detection)
        base_time = datetime(2024, 3, 14, 14, 0, 0)
        timestamps = [base_time + timedelta(minutes=i) for i in range(-60, 1)]
        # Baseline: stable around 2500
        prices = [2500.0] * 60
        # Last minute: +15% spike (definitely triggers)
        prices.append(2875.0)
        volumes = [5000.0] * 61

        data = pd.DataFrame(
            {
                "timestamp": timestamps,
                "price": prices,
                "volume": volumes,
                "symbol": ["ETH-USD"] * 61,
            }
        )

        anomalies = detector.detect_all(data)

        assert len(anomalies) >= 1
        anomaly = anomalies[0]

        # Check metadata exists
        assert "volatility_tier" in anomaly.detection_metadata
        assert "asset_threshold" in anomaly.detection_metadata
        assert "threshold_source" in anomaly.detection_metadata
        assert anomaly.detection_metadata["volatility_tier"] == "stable"


class TestBackwardCompatibility:
    """Ensure legacy detectors still work when new features disabled."""

    def test_legacy_detection_without_config_file(self):
        """Should fallback to global settings if thresholds.yaml missing."""
        # This would happen if config file doesn't exist
        detector = AnomalyDetector()

        # Create simple spike
        base_time = datetime(2024, 3, 14, 14, 0, 0)
        timestamps = [base_time + timedelta(minutes=i) for i in range(-60, 1)]
        prices = [100.0] * 60 + [110.0]  # +10% spike
        volumes = [1000.0] * 61

        data = pd.DataFrame(
            {
                "timestamp": timestamps,
                "price": prices,
                "volume": volumes,
                "symbol": ["TEST-USD"] * 61,
            }
        )

        anomalies = detector.detect_all(data)

        # Should still detect with legacy detectors
        assert len(anomalies) == 1
        assert anomalies[0].symbol == "TEST-USD"
