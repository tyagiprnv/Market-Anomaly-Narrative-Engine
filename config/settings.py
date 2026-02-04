"""Application settings using Pydantic."""

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Literal
from pathlib import Path
import yaml


class DatabaseSettings(BaseSettings):
    """Database connection settings."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_prefix="DATABASE__",
        extra="ignore",
    )

    host: str = "localhost"
    port: int = 5432
    database: str = "mane_db"
    username: str = "postgres"
    password: str

    @property
    def url(self) -> str:
        """Get SQLAlchemy database URL."""
        return f"postgresql://{self.username}:{self.password}@{self.host}:{self.port}/{self.database}"


class LLMSettings(BaseSettings):
    """LLM configuration."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_prefix="LLM__",
        extra="ignore",
    )

    provider: Literal["openai", "anthropic", "ollama", "deepseek"] = "anthropic"
    model: str = "claude-3-5-haiku-20241022"
    temperature: float = 0.3
    max_tokens: int = 500

    # API keys (loaded from environment)
    openai_api_key: str | None = None
    anthropic_api_key: str | None = None
    deepseek_api_key: str | None = None
    ollama_api_base: str = "http://localhost:11434"


class DetectionSettings(BaseSettings):
    """Anomaly detection configuration."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_prefix="DETECTION__",
        extra="ignore",
    )

    # Thresholds
    z_score_threshold: float = 3.0
    volume_z_threshold: float = 2.5
    bollinger_std_multiplier: float = 2.0

    # Time windows
    lookback_window_minutes: int = 60
    news_window_minutes: int = 30

    # Asset-aware detection
    use_asset_specific_thresholds: bool = True
    thresholds_config_path: str = "config/thresholds.yaml"

    # Multi-timeframe detection
    enable_multi_timeframe: bool = True
    timeframe_windows: list[int] = Field(default=[5, 15, 30, 60])

    # Cumulative detection
    enable_cumulative_detection: bool = True
    cumulative_min_periods: int = 3

    # Crypto assets to monitor
    symbols: list[str] = Field(
        default=[
            "BTC-USD",
            "ETH-USD",
            "BNB-USD",
            "SOL-USD",
            "XRP-USD",
            "ADA-USD",
            "DOGE-USD",
            "AVAX-USD",
            "DOT-USD",
            "MATIC-USD",
            "LINK-USD",
            "UNI-USD",
            "ATOM-USD",
            "LTC-USD",
            "ETC-USD",
            "XLM-USD",
            "ALGO-USD",
            "VET-USD",
            "ICP-USD",
            "FIL-USD",
        ]
    )

    def load_thresholds_config(self) -> dict | None:
        """Load YAML thresholds configuration.

        Returns:
            Dict with threshold config or None if file doesn't exist
        """
        config_file = Path(self.thresholds_config_path)
        if not config_file.exists():
            return None

        with open(config_file, "r") as f:
            return yaml.safe_load(f)


class DataIngestionSettings(BaseSettings):
    """Data ingestion configuration."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_prefix="DATA_INGESTION__",
        extra="ignore",
    )

    # Primary and backup sources
    primary_source: Literal["coinbase", "binance"] = "coinbase"

    # API Keys (optional for public endpoints)
    coinbase_api_key: str | None = None
    coinbase_api_secret: str | None = None
    binance_api_key: str | None = None
    binance_api_secret: str | None = None

    # Polling configuration
    poll_interval_seconds: int = 60
    request_timeout_seconds: int = 10


class NewsSettings(BaseSettings):
    """News API configuration."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_prefix="NEWS__",
        extra="ignore",
    )

    # Mode configuration: live, replay, or hybrid
    mode: Literal["live", "replay", "hybrid"] = "live"

    # RSS feed URLs (free sources)
    rss_feeds: list[str] = Field(
        default=[
            "https://www.coindesk.com/arc/outboundfeeds/rss/",
            "https://cointelegraph.com/rss",
            "https://decrypt.co/feed",
            "https://bitcoinmagazine.com/feed",
            "https://www.theblock.co/rss.xml",
        ]
    )

    # Historical replay configuration
    replay_dataset_path: str = "datasets/news/"

    # API Keys (now optional for paid providers)
    cryptopanic_api_key: str | None = None
    newsapi_api_key: str | None = None
    grok_api_key: str | None = None


class ClusteringSettings(BaseSettings):
    """News clustering configuration."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_prefix="CLUSTERING__",
        extra="ignore",
    )

    embedding_model: str = "all-MiniLM-L6-v2"
    min_cluster_size: int = 2
    clustering_algorithm: Literal["hdbscan", "dbscan"] = "hdbscan"


class ValidationSettings(BaseSettings):
    """Phase 3 validation configuration."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_prefix="VALIDATION__",
        extra="ignore",
    )

    # Overall threshold for passing validation
    pass_threshold: float = 0.65

    # Validator weights (relative importance, higher = more impact)
    sentiment_match_weight: float = 1.2
    timing_coherence_weight: float = 1.5  # Most critical validator
    magnitude_coherence_weight: float = 0.8
    tool_consistency_weight: float = 1.0
    narrative_quality_weight: float = 0.5
    judge_llm_weight: float = 1.5

    # Rule-based validator thresholds
    sentiment_alignment_threshold: float = 0.7
    sentiment_neutral_range_lower: float = -0.2
    sentiment_neutral_range_upper: float = 0.2
    max_news_time_before_minutes: int = 30
    min_causal_news_ratio: float = 0.8
    min_tools_used: int = 2
    z_score_small: float = 3.5
    z_score_large: float = 5.0
    max_sentence_count: int = 2
    hedging_keywords: list[str] = Field(
        default=[
            "possibly",
            "might have",
            "unclear",
            "potentially",
            "may have",
            "could be",
        ]
    )

    # Judge LLM configuration
    judge_llm_enabled: bool = True
    judge_llm_min_trigger_score: float = 0.5  # Only run if rules pass this score
    judge_llm_min_score: float = 3.0  # Minimum score (out of 5) to pass
    judge_llm_model: str | None = None  # Use default LLM if None
    judge_llm_temperature: float = 0.2  # Low temp for consistent evaluation

    # Execution settings
    parallel_validation: bool = True  # Run rule validators in parallel
    consistency_threshold: float = 0.8  # For tool consistency checks


class OrchestrationSettings(BaseSettings):
    """Orchestration and scheduling settings."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_prefix="ORCHESTRATION__",
        extra="ignore",
    )

    # Idempotency
    duplicate_window_minutes: int = Field(
        default=5,
        description="Window for checking duplicate anomalies (minutes)",
    )

    # Price history
    price_history_lookback_minutes: int = Field(
        default=60,
        description="Minutes of price history to fetch for detection",
    )

    min_price_points: int = Field(
        default=30,
        description="Minimum price data points required for detection",
    )

    # Retry policy
    max_retries_per_symbol: int = Field(
        default=3,
        description="Max retry attempts for failed symbol processing",
    )

    retry_delay_seconds: int = Field(
        default=10,
        description="Delay between retry attempts (seconds)",
    )

    # Resource limits
    max_concurrent_llm_calls: int = Field(
        default=2,
        description="Max concurrent LLM API calls (rate limiting)",
    )


class Settings(BaseSettings):
    """Main application settings."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_nested_delimiter="__",
        extra="ignore",
    )

    # Sub-settings
    database: DatabaseSettings = Field(default_factory=DatabaseSettings)
    llm: LLMSettings = Field(default_factory=LLMSettings)
    detection: DetectionSettings = Field(default_factory=DetectionSettings)
    data_ingestion: DataIngestionSettings = Field(default_factory=DataIngestionSettings)
    news: NewsSettings = Field(default_factory=NewsSettings)
    clustering: ClusteringSettings = Field(default_factory=ClusteringSettings)
    validation: ValidationSettings = Field(default_factory=ValidationSettings)
    orchestration: OrchestrationSettings = Field(default_factory=OrchestrationSettings)

    # Scheduler
    poll_interval_seconds: int = 60

    # Logging
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"


# Global settings instance
settings = Settings()
