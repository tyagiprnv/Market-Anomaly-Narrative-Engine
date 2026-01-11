"""SQLAlchemy database models for Market Anomaly Narrative Engine."""

from datetime import datetime
from enum import Enum as PyEnum
import uuid

from sqlalchemy import (
    Column,
    String,
    Float,
    Integer,
    DateTime,
    Text,
    ForeignKey,
    Enum,
    JSON,
    Boolean,
    Index,
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()


class AnomalyTypeEnum(PyEnum):
    """Types of market anomalies."""

    PRICE_SPIKE = "price_spike"
    PRICE_DROP = "price_drop"
    VOLUME_SPIKE = "volume_spike"
    COMBINED = "combined"


class Price(Base):
    """Time-series price data from crypto exchanges."""

    __tablename__ = "prices"

    id = Column(Integer, primary_key=True, autoincrement=True)
    symbol = Column(String(20), nullable=False, index=True)
    timestamp = Column(DateTime, nullable=False, index=True)
    price = Column(Float, nullable=False)
    volume_24h = Column(Float)
    high_24h = Column(Float)
    low_24h = Column(Float)
    bid = Column(Float)
    ask = Column(Float)
    source = Column(String(20))  # coinbase, binance
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (Index("idx_symbol_timestamp", "symbol", "timestamp"),)

    def __repr__(self):
        return f"<Price(symbol={self.symbol}, price={self.price}, timestamp={self.timestamp})>"


class Anomaly(Base):
    """Detected price anomalies with statistical metrics."""

    __tablename__ = "anomalies"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    symbol = Column(String(20), nullable=False, index=True)
    detected_at = Column(DateTime, nullable=False, index=True)
    anomaly_type = Column(Enum(AnomalyTypeEnum), nullable=False)

    # Statistical metrics
    z_score = Column(Float)
    price_change_pct = Column(Float)
    volume_change_pct = Column(Float)
    confidence = Column(Float)
    baseline_window_minutes = Column(Integer)

    # Price snapshot
    price_before = Column(Float)
    price_at_detection = Column(Float)
    volume_before = Column(Float)
    volume_at_detection = Column(Float)

    # Relationships
    news_articles = relationship("NewsArticle", back_populates="anomaly", cascade="all, delete-orphan")
    narrative = relationship("Narrative", back_populates="anomaly", uselist=False, cascade="all, delete-orphan")
    news_clusters = relationship("NewsCluster", back_populates="anomaly", cascade="all, delete-orphan")

    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (Index("idx_symbol_detected", "symbol", "detected_at"),)

    def __repr__(self):
        return f"<Anomaly(symbol={self.symbol}, type={self.anomaly_type.value}, change={self.price_change_pct}%)>"


class NewsArticle(Base):
    """News articles linked to anomalies."""

    __tablename__ = "news_articles"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    anomaly_id = Column(String(36), ForeignKey("anomalies.id"), index=True)

    source = Column(String(50))  # cryptopanic, newsapi, reddit
    title = Column(Text, nullable=False)
    url = Column(Text)
    published_at = Column(DateTime, nullable=False)
    summary = Column(Text)

    # Clustering info
    cluster_id = Column(Integer)  # -1 for unclustered
    embedding = Column(JSON)  # Store as JSON array for similarity searches

    # Relationship
    anomaly = relationship("Anomaly", back_populates="news_articles")

    # Timing relative to anomaly
    timing_tag = Column(String(20))  # pre_event, post_event
    time_diff_minutes = Column(Float)  # minutes before/after anomaly

    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index("idx_anomaly", "anomaly_id"),
        Index("idx_published", "published_at"),
    )

    def __repr__(self):
        return f"<NewsArticle(source={self.source}, title={self.title[:50]}...)>"


class Narrative(Base):
    """Generated narratives explaining anomalies."""

    __tablename__ = "narratives"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    anomaly_id = Column(String(36), ForeignKey("anomalies.id"), unique=True, index=True)

    # Agent output
    narrative_text = Column(Text, nullable=False)
    confidence_score = Column(Float)

    # Tool usage tracking
    tools_used = Column(JSON)  # List of tools called
    tool_results = Column(JSON)  # Aggregated tool outputs

    # Validation
    validated = Column(Boolean, default=False)
    validation_passed = Column(Boolean)
    validation_reason = Column(Text)

    # Relationship
    anomaly = relationship("Anomaly", back_populates="narrative")

    # LLM metadata
    llm_provider = Column(String(20))
    llm_model = Column(String(50))
    generation_time_seconds = Column(Float)

    created_at = Column(DateTime, default=datetime.utcnow)
    validated_at = Column(DateTime)

    def __repr__(self):
        return f"<Narrative(anomaly_id={self.anomaly_id}, validated={self.validation_passed})>"


class NewsCluster(Base):
    """Clusters of related news articles."""

    __tablename__ = "news_clusters"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    anomaly_id = Column(String(36), ForeignKey("anomalies.id"), index=True)
    cluster_number = Column(Integer)  # -1 for noise

    article_ids = Column(JSON)  # List of article IDs in cluster
    centroid_summary = Column(Text)  # Representative headline
    dominant_sentiment = Column(Float)
    size = Column(Integer)

    # Relationship
    anomaly = relationship("Anomaly", back_populates="news_clusters")

    created_at = Column(DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<NewsCluster(anomaly_id={self.anomaly_id}, size={self.size})>"
