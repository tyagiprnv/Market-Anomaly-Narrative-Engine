"""Asset profile manager for volatility-aware threshold lookup."""

from dataclasses import dataclass
from pathlib import Path
from typing import Optional
import yaml

from config.settings import settings


@dataclass
class AssetThresholds:
    """Thresholds for a specific asset."""

    symbol: str
    z_score_threshold: float
    volume_z_threshold: float
    bollinger_std_multiplier: float
    min_absolute_return_threshold: float  # Minimum % move to flag (prevents noise)
    volatility_tier: str
    source: str  # 'asset_specific', 'tier', or 'global'


class AssetProfileManager:
    """Manages asset-specific threshold lookup with 3-tier priority.

    Priority order:
    1. Asset-specific override (e.g., BTC-USD: 3.5)
    2. Volatility tier (e.g., stable: 3.0 × 1.2 = 3.6)
    3. Global defaults (settings.py fallback)
    """

    def __init__(self, config_path: Optional[str] = None):
        """Initialize profile manager.

        Args:
            config_path: Path to thresholds.yaml (default: config/thresholds.yaml)
        """
        self.config_path = config_path or "config/thresholds.yaml"
        self._cache: dict[str, AssetThresholds] = {}
        self._config: Optional[dict] = None
        self._load_config()

    def _load_config(self) -> None:
        """Load YAML configuration file."""
        config_file = Path(self.config_path)
        if not config_file.exists():
            # Config missing, will use global defaults
            self._config = None
            return

        with open(config_file, "r") as f:
            self._config = yaml.safe_load(f)

    def get_thresholds(self, symbol: str) -> AssetThresholds:
        """Get thresholds for a symbol with 3-tier lookup.

        Args:
            symbol: Asset symbol (e.g., 'BTC-USD')

        Returns:
            AssetThresholds with appropriate thresholds
        """
        # Check cache
        if symbol in self._cache:
            return self._cache[symbol]

        # Perform lookup
        thresholds = self._lookup_thresholds(symbol)
        self._cache[symbol] = thresholds
        return thresholds

    def _lookup_thresholds(self, symbol: str) -> AssetThresholds:
        """Perform 3-tier threshold lookup.

        Priority:
        1. Asset-specific overrides
        2. Volatility tier multipliers
        3. Global defaults
        """
        # Fallback: Global defaults from settings
        global_z = settings.detection.z_score_threshold
        global_vol = settings.detection.volume_z_threshold
        global_bb = settings.detection.bollinger_std_multiplier
        global_min_return = settings.detection.min_absolute_return_threshold

        # No config file, use global defaults
        if not self._config:
            return AssetThresholds(
                symbol=symbol,
                z_score_threshold=global_z,
                volume_z_threshold=global_vol,
                bollinger_std_multiplier=global_bb,
                min_absolute_return_threshold=global_min_return,
                volatility_tier="unknown",
                source="global",
            )

        # Priority 1: Asset-specific overrides
        asset_specific = self._config.get("asset_specific_thresholds", {})
        yaml_global = self._config.get("global_defaults", {})
        yaml_min_return = yaml_global.get("min_absolute_return_threshold", global_min_return)

        if symbol in asset_specific:
            overrides = asset_specific[symbol]
            return AssetThresholds(
                symbol=symbol,
                z_score_threshold=overrides.get("z_score_threshold", global_z),
                volume_z_threshold=overrides.get("volume_z_threshold", global_vol),
                bollinger_std_multiplier=overrides.get("bollinger_std_multiplier", global_bb),
                min_absolute_return_threshold=overrides.get("min_absolute_return_threshold", yaml_min_return),
                volatility_tier=self._get_tier_name(symbol),
                source="asset_specific",
            )

        # Priority 2: Volatility tier multipliers
        tier_name, tier_config = self._find_tier(symbol)
        if tier_config:
            multiplier = tier_config.get("multiplier", 1.0)
            # Apply multiplier to global defaults from YAML or settings
            yaml_global = self._config.get("global_defaults", {})
            base_z = yaml_global.get("z_score_threshold", global_z)
            base_vol = yaml_global.get("volume_z_threshold", global_vol)
            base_bb = yaml_global.get("bollinger_std_multiplier", global_bb)
            base_min_return = tier_config.get("min_absolute_return", yaml_min_return)

            return AssetThresholds(
                symbol=symbol,
                z_score_threshold=base_z * multiplier,
                volume_z_threshold=base_vol * multiplier,
                bollinger_std_multiplier=base_bb,
                min_absolute_return_threshold=base_min_return,
                volatility_tier=tier_name,
                source="tier",
            )

        # Priority 3: Global defaults
        yaml_global = self._config.get("global_defaults", {})
        return AssetThresholds(
            symbol=symbol,
            z_score_threshold=yaml_global.get("z_score_threshold", global_z),
            volume_z_threshold=yaml_global.get("volume_z_threshold", global_vol),
            bollinger_std_multiplier=yaml_global.get("bollinger_std_multiplier", global_bb),
            min_absolute_return_threshold=yaml_global.get("min_absolute_return_threshold", global_min_return),
            volatility_tier="unknown",
            source="global",
        )

    def _find_tier(self, symbol: str) -> tuple[str, Optional[dict]]:
        """Find volatility tier for a symbol.

        Returns:
            Tuple of (tier_name, tier_config) or ('unknown', None)
        """
        if not self._config:
            return ("unknown", None)

        tiers = self._config.get("volatility_tiers", {})
        for tier_name, tier_config in tiers.items():
            assets = tier_config.get("assets", [])
            if symbol in assets:
                return (tier_name, tier_config)

        return ("unknown", None)

    def _get_tier_name(self, symbol: str) -> str:
        """Get tier name for a symbol."""
        tier_name, _ = self._find_tier(symbol)
        return tier_name

    def get_timeframe_config(self) -> dict:
        """Get multi-timeframe configuration.

        Returns:
            Dict with timeframe settings:
            {
                'enabled': bool,
                'windows': list[int],
                'baseline_multiplier': int
            }
        """
        if not self._config:
            return {
                "enabled": False,
                "windows": [5, 15, 30, 60],
                "baseline_multiplier": 3,
            }

        tf_config = self._config.get("timeframes", {})
        return {
            "enabled": tf_config.get("enabled", False),
            "windows": tf_config.get("windows", [5, 15, 30, 60]),
            "baseline_multiplier": tf_config.get("baseline_multiplier", 3),
        }

    def get_cumulative_config(self) -> dict:
        """Get cumulative detection configuration.

        Returns:
            Dict with cumulative settings:
            {
                'enabled': bool,
                'min_periods': int
            }
        """
        if not self._config:
            return {"enabled": False, "min_periods": 3}

        cum_config = self._config.get("cumulative", {})
        return {
            "enabled": cum_config.get("enabled", False),
            "min_periods": cum_config.get("min_periods", 3),
        }

    def clear_cache(self) -> None:
        """Clear cached thresholds (e.g., after config reload)."""
        self._cache.clear()

    def reload_config(self) -> None:
        """Reload configuration from disk and clear cache."""
        self._load_config()
        self.clear_cache()
