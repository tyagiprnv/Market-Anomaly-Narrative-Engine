"""Application settings using Pydantic."""

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Literal


class DatabaseSettings(BaseSettings):
    """Database connection settings."""

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

    provider: Literal["openai", "anthropic", "ollama"] = "anthropic"
    model: str = "claude-3-5-haiku-20241022"
    temperature: float = 0.3
    max_tokens: int = 500

    # API keys (loaded from environment)
    openai_api_key: str | None = None
    anthropic_api_key: str | None = None
    ollama_api_base: str = "http://localhost:11434"


class DetectionSettings(BaseSettings):
    """Anomaly detection configuration."""

    # Thresholds
    z_score_threshold: float = 3.0
    volume_z_threshold: float = 2.5
    bollinger_std_multiplier: float = 2.0

    # Time windows
    lookback_window_minutes: int = 60
    news_window_minutes: int = 30

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


class NewsSettings(BaseSettings):
    """News API configuration."""

    # API Keys
    cryptopanic_api_key: str
    newsapi_api_key: str | None = None
    reddit_client_id: str
    reddit_client_secret: str
    reddit_user_agent: str = "MarketAnomalyEngine/0.1.0"


class ClusteringSettings(BaseSettings):
    """News clustering configuration."""

    embedding_model: str = "all-MiniLM-L6-v2"
    min_cluster_size: int = 2
    clustering_algorithm: Literal["hdbscan", "dbscan"] = "hdbscan"


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
    news: NewsSettings = Field(default_factory=NewsSettings)
    clustering: ClusteringSettings = Field(default_factory=ClusteringSettings)

    # Scheduler
    poll_interval_seconds: int = 60

    # Logging
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"


# Global settings instance
settings = Settings()
