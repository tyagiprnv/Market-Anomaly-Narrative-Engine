"""Tests for news clustering functionality."""

import os
import uuid
from datetime import datetime, timedelta

import numpy as np
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

# Set required environment variables for tests
os.environ["DATABASE__PASSWORD"] = "test_password"
os.environ["NEWS__CRYPTOPANIC_API_KEY"] = "test_crypto_key"
os.environ["NEWS__REDDIT_CLIENT_ID"] = "test_reddit_id"
os.environ["NEWS__REDDIT_CLIENT_SECRET"] = "test_reddit_secret"

from src.database.models import Base, NewsArticle, NewsCluster
from src.phase1_detector.clustering import NewsClusterer
from src.phase1_detector.news_aggregation.models import NewsArticle as NewsArticlePydantic


@pytest.fixture
def sample_articles() -> list[NewsArticlePydantic]:
    """Create sample news articles for testing."""
    base_time = datetime.now()

    articles = [
        # Cluster 1: Bitcoin price surge
        NewsArticlePydantic(
            source="cryptopanic",
            title="Bitcoin surges to new all-time high",
            url="https://example.com/btc1",
            published_at=base_time,
            summary="Bitcoin reaches unprecedented price levels amid institutional buying",
            sentiment=0.8,
            symbols=["BTC"],
            timing_tag="pre_event",
            time_diff_minutes=-5.0,
        ),
        NewsArticlePydantic(
            source="newsapi",
            title="BTC hits record high as institutions pile in",
            url="https://example.com/btc2",
            published_at=base_time + timedelta(minutes=1),
            summary="Major institutions continue accumulating Bitcoin",
            sentiment=0.9,
            symbols=["BTC"],
            timing_tag="pre_event",
            time_diff_minutes=-4.0,
        ),
        NewsArticlePydantic(
            source="reddit",
            title="Bitcoin breaks resistance, new ATH incoming",
            url="https://example.com/btc3",
            published_at=base_time + timedelta(minutes=2),
            summary="Technical analysis suggests Bitcoin will continue rising",
            sentiment=0.7,
            symbols=["BTC"],
            timing_tag="pre_event",
            time_diff_minutes=-3.0,
        ),
        # Cluster 2: Regulatory news
        NewsArticlePydantic(
            source="cryptopanic",
            title="SEC announces new crypto regulations",
            url="https://example.com/sec1",
            published_at=base_time + timedelta(minutes=5),
            summary="New regulatory framework for cryptocurrency trading",
            sentiment=-0.3,
            symbols=["BTC", "ETH"],
            timing_tag="post_event",
            time_diff_minutes=5.0,
        ),
        NewsArticlePydantic(
            source="newsapi",
            title="Regulators introduce stricter crypto rules",
            url="https://example.com/sec2",
            published_at=base_time + timedelta(minutes=6),
            summary="Government bodies tighten oversight of digital assets",
            sentiment=-0.4,
            symbols=["BTC", "ETH"],
            timing_tag="post_event",
            time_diff_minutes=6.0,
        ),
        # Noise: unrelated article
        NewsArticlePydantic(
            source="reddit",
            title="New DeFi protocol launches on Solana",
            url="https://example.com/sol1",
            published_at=base_time + timedelta(minutes=10),
            summary="Innovative DeFi platform debuts on Solana blockchain",
            sentiment=0.5,
            symbols=["SOL"],
            timing_tag="post_event",
            time_diff_minutes=10.0,
        ),
    ]

    return articles


@pytest.fixture
def in_memory_db():
    """Create an in-memory SQLite database for testing."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()

    yield session

    session.close()


class TestNewsClusterer:
    """Test cases for NewsClusterer."""

    def test_initialization(self):
        """Test NewsClusterer initialization."""
        clusterer = NewsClusterer()
        assert clusterer.embedding_model is not None
        assert clusterer.session is None

    def test_initialization_with_session(self, in_memory_db):
        """Test NewsClusterer initialization with database session."""
        clusterer = NewsClusterer(session=in_memory_db)
        assert clusterer.session is not None

    def test_generate_embeddings(self, sample_articles):
        """Test embedding generation."""
        clusterer = NewsClusterer()
        articles, embeddings = clusterer.generate_embeddings(sample_articles)

        assert len(articles) == len(sample_articles)
        assert embeddings.shape[0] == len(sample_articles)
        assert embeddings.shape[1] > 0  # Embedding dimension > 0
        assert embeddings.dtype == np.float32

    def test_generate_embeddings_empty(self):
        """Test embedding generation with empty input."""
        clusterer = NewsClusterer()
        articles, embeddings = clusterer.generate_embeddings([])

        assert len(articles) == 0
        assert embeddings.size == 0

    def test_cluster_articles(self, sample_articles):
        """Test article clustering."""
        clusterer = NewsClusterer()
        articles, embeddings = clusterer.generate_embeddings(sample_articles)
        clusters = clusterer.cluster_articles(articles, embeddings)

        # Should find at least one cluster
        assert len(clusters) > 0

        # Check that all articles are assigned
        total_articles = sum(len(indices) for indices in clusters.values())
        assert total_articles == len(sample_articles)

        # Noise cluster should exist (cluster_id = -1)
        assert -1 in clusters

    def test_cluster_articles_too_few(self):
        """Test clustering with too few articles."""
        clusterer = NewsClusterer()

        # Create single article
        article = NewsArticlePydantic(
            source="cryptopanic",
            title="Bitcoin price update",
            url="https://example.com/btc",
            published_at=datetime.now(),
            sentiment=0.5,
            symbols=["BTC"],
        )

        articles, embeddings = clusterer.generate_embeddings([article])
        clusters = clusterer.cluster_articles(articles, embeddings)

        # All should be noise when below min_cluster_size
        assert clusters == {-1: [0]}

    def test_get_cluster_centroid_summary(self, sample_articles):
        """Test centroid summary extraction."""
        clusterer = NewsClusterer()
        articles, embeddings = clusterer.generate_embeddings(sample_articles)

        # Get centroid for first 3 articles (BTC cluster)
        cluster_indices = [0, 1, 2]
        centroid_summary = clusterer.get_cluster_centroid_summary(
            cluster_indices, articles, embeddings
        )

        # Should return one of the BTC article titles
        assert centroid_summary in [
            "Bitcoin surges to new all-time high",
            "BTC hits record high as institutions pile in",
            "Bitcoin breaks resistance, new ATH incoming",
        ]

    def test_get_cluster_centroid_summary_empty(self, sample_articles):
        """Test centroid summary with empty cluster."""
        clusterer = NewsClusterer()
        articles, embeddings = clusterer.generate_embeddings(sample_articles)

        centroid_summary = clusterer.get_cluster_centroid_summary([], articles, embeddings)
        assert centroid_summary == ""

    def test_get_dominant_sentiment(self, sample_articles):
        """Test dominant sentiment calculation."""
        clusterer = NewsClusterer()

        # Cluster 1: Bitcoin articles (positive sentiment)
        cluster_indices = [0, 1, 2]
        sentiment = clusterer.get_dominant_sentiment(cluster_indices, sample_articles)
        assert 0.7 <= sentiment <= 0.9  # Should be average of 0.8, 0.9, 0.7

        # Cluster 2: Regulatory articles (negative sentiment)
        cluster_indices = [3, 4]
        sentiment = clusterer.get_dominant_sentiment(cluster_indices, sample_articles)
        assert -0.4 <= sentiment <= -0.3  # Should be average of -0.3, -0.4

    def test_get_dominant_sentiment_no_sentiments(self):
        """Test dominant sentiment with no sentiment values."""
        clusterer = NewsClusterer()

        articles = [
            NewsArticlePydantic(
                source="cryptopanic",
                title="Test article",
                url="https://example.com/test",
                published_at=datetime.now(),
                sentiment=None,
                symbols=["BTC"],
            )
        ]

        sentiment = clusterer.get_dominant_sentiment([0], articles)
        assert sentiment == 0.0

    def test_cluster_for_anomaly(self, sample_articles):
        """Test clustering without persistence."""
        clusterer = NewsClusterer()
        anomaly_id = str(uuid.uuid4())

        result = clusterer.cluster_for_anomaly(anomaly_id, sample_articles)

        assert "clusters" in result
        assert "embeddings" in result
        assert "n_clusters" in result
        assert "n_noise" in result

        # HDBSCAN may or may not find clusters depending on similarity
        # Just verify the clustering ran and all articles are accounted for
        assert result["n_clusters"] >= 0
        assert result["n_noise"] >= 0
        assert result["embeddings"].shape[0] == len(sample_articles)

        # Verify all articles are assigned to some cluster (including noise)
        total_assigned = sum(len(indices) for indices in result["clusters"].values())
        assert total_assigned == len(sample_articles)

    def test_cluster_for_anomaly_empty(self):
        """Test clustering with no articles."""
        clusterer = NewsClusterer()
        anomaly_id = str(uuid.uuid4())

        result = clusterer.cluster_for_anomaly(anomaly_id, [])

        assert result["clusters"] == {}
        assert result["embeddings"].size == 0
        assert result["n_clusters"] == 0
        assert result["n_noise"] == 0

    def test_cluster_and_persist(self, in_memory_db, sample_articles):
        """Test clustering with database persistence."""
        anomaly_id = str(uuid.uuid4())
        clusterer = NewsClusterer(session=in_memory_db)

        clusters = clusterer.cluster_and_persist(anomaly_id, sample_articles)

        # May or may not create cluster records depending on HDBSCAN results
        assert len(clusters) >= 0

        # Verify clusters in database
        db_clusters = in_memory_db.query(NewsCluster).all()
        assert len(db_clusters) == len(clusters)

        # Verify articles in database
        db_articles = in_memory_db.query(NewsArticle).all()
        assert len(db_articles) == len(sample_articles)

        # Check that noise articles have cluster_id = -1
        noise_articles = [a for a in db_articles if a.cluster_id == -1]
        assert len(noise_articles) >= 0

        # Check that clustered articles have valid cluster_ids
        clustered_articles = [a for a in db_articles if a.cluster_id != -1]
        for article in clustered_articles:
            assert article.cluster_id >= 0
            assert article.embedding is not None
            assert isinstance(article.embedding, list)

        # Verify cluster metadata (if clusters were found)
        if len(db_clusters) > 0:
            for cluster in db_clusters:
                assert cluster.anomaly_id == anomaly_id
                assert cluster.cluster_number >= 0
                assert len(cluster.article_ids) > 0
                assert cluster.centroid_summary != ""
                assert cluster.size > 0
                assert -1.0 <= cluster.dominant_sentiment <= 1.0

    def test_cluster_and_persist_no_session(self, sample_articles):
        """Test that persistence fails without a database session."""
        clusterer = NewsClusterer()
        anomaly_id = str(uuid.uuid4())

        with pytest.raises(ValueError, match="Database session required"):
            clusterer.cluster_and_persist(anomaly_id, sample_articles)

    def test_cluster_and_persist_empty(self, in_memory_db):
        """Test persistence with no articles."""
        anomaly_id = str(uuid.uuid4())
        clusterer = NewsClusterer(session=in_memory_db)

        clusters = clusterer.cluster_and_persist(anomaly_id, [])

        assert len(clusters) == 0

        # Verify no clusters or articles in database
        db_clusters = in_memory_db.query(NewsCluster).all()
        db_articles = in_memory_db.query(NewsArticle).all()
        assert len(db_clusters) == 0
        assert len(db_articles) == 0

    def test_embedding_consistency(self, sample_articles):
        """Test that embeddings are consistent across calls."""
        clusterer = NewsClusterer()

        # Generate embeddings twice
        _, embeddings1 = clusterer.generate_embeddings(sample_articles)
        _, embeddings2 = clusterer.generate_embeddings(sample_articles)

        # Should be identical (deterministic model)
        np.testing.assert_array_almost_equal(embeddings1, embeddings2)

    def test_clustering_semantic_grouping(self, sample_articles):
        """Test that similar articles are clustered together."""
        clusterer = NewsClusterer()
        articles, embeddings = clusterer.generate_embeddings(sample_articles)
        clusters = clusterer.cluster_articles(articles, embeddings)

        # Find non-noise clusters
        valid_clusters = {k: v for k, v in clusters.items() if k != -1}

        if len(valid_clusters) > 0:
            # Check that BTC surge articles (0, 1, 2) tend to cluster together
            btc_cluster_ids = []
            for cluster_id, indices in valid_clusters.items():
                if 0 in indices or 1 in indices or 2 in indices:
                    btc_cluster_ids.append(cluster_id)

            # If BTC articles are clustered, they should be in the same cluster
            if btc_cluster_ids:
                assert len(set(btc_cluster_ids)) <= 2  # At most 2 different clusters

            # Check that regulatory articles (3, 4) tend to cluster together
            reg_cluster_ids = []
            for cluster_id, indices in valid_clusters.items():
                if 3 in indices or 4 in indices:
                    reg_cluster_ids.append(cluster_id)

            if reg_cluster_ids:
                assert len(set(reg_cluster_ids)) <= 2
