"""News clustering using sentence-transformers and HDBSCAN."""

import logging
from collections import Counter
from typing import Any

import hdbscan
import numpy as np
from sentence_transformers import SentenceTransformer
from sqlalchemy.orm import Session

from config.settings import settings
from src.database.models import NewsArticle, NewsCluster
from src.phase1_detector.news_aggregation.models import NewsArticle as NewsArticlePydantic

logger = logging.getLogger(__name__)


class NewsClusterer:
    """Clusters news articles using embeddings and HDBSCAN."""

    def __init__(self, session: Session | None = None):
        """Initialize the news clusterer.

        Args:
            session: SQLAlchemy database session (optional, for persistence)
        """
        self.settings = settings
        self.session = session

        # Load embedding model
        logger.info(f"Loading embedding model: {self.settings.clustering.embedding_model}")
        self.embedding_model = SentenceTransformer(
            self.settings.clustering.embedding_model
        )

        # HDBSCAN clusterer (will be fit on data)
        self.clusterer = None

    def generate_embeddings(
        self, articles: list[NewsArticlePydantic]
    ) -> tuple[list[NewsArticlePydantic], np.ndarray]:
        """Generate embeddings for news articles.

        Args:
            articles: List of news articles to embed

        Returns:
            Tuple of (articles, embeddings matrix)
        """
        if not articles:
            logger.warning("No articles to embed")
            return articles, np.array([])

        # Combine title and summary for richer embeddings
        texts = []
        for article in articles:
            text = article.title
            if article.summary:
                text += f" {article.summary}"
            texts.append(text)

        # Generate embeddings
        logger.info(f"Generating embeddings for {len(texts)} articles")
        embeddings = self.embedding_model.encode(
            texts, convert_to_numpy=True, show_progress_bar=False
        )

        logger.info(f"Generated embeddings with shape {embeddings.shape}")
        return articles, embeddings

    def cluster_articles(
        self, articles: list[NewsArticlePydantic], embeddings: np.ndarray
    ) -> dict[int, list[int]]:
        """Cluster articles using HDBSCAN.

        Args:
            articles: List of news articles
            embeddings: Embedding matrix (n_articles x embedding_dim)

        Returns:
            Dictionary mapping cluster_id -> list of article indices
            Noise points have cluster_id = -1
        """
        if len(articles) == 0 or embeddings.size == 0:
            logger.warning("No articles to cluster")
            return {}

        # Need at least min_cluster_size articles
        if len(articles) < self.settings.clustering.min_cluster_size:
            logger.warning(
                f"Too few articles ({len(articles)}) for clustering "
                f"(min_cluster_size={self.settings.clustering.min_cluster_size}). "
                "Treating all as noise."
            )
            return {-1: list(range(len(articles)))}

        # Fit HDBSCAN
        logger.info(
            f"Clustering {len(articles)} articles with "
            f"min_cluster_size={self.settings.clustering.min_cluster_size}"
        )

        self.clusterer = hdbscan.HDBSCAN(
            min_cluster_size=self.settings.clustering.min_cluster_size,
            metric="euclidean",
            cluster_selection_method="eom",  # Excess of mass
            prediction_data=True,
        )

        cluster_labels = self.clusterer.fit_predict(embeddings)

        # Group articles by cluster
        clusters: dict[int, list[int]] = {}
        for idx, cluster_id in enumerate(cluster_labels):
            if cluster_id not in clusters:
                clusters[cluster_id] = []
            clusters[cluster_id].append(idx)

        # Log clustering results
        n_clusters = len([c for c in clusters.keys() if c != -1])
        n_noise = len(clusters.get(-1, []))
        logger.info(f"Found {n_clusters} clusters and {n_noise} noise points")

        return clusters

    def get_cluster_centroid_summary(
        self,
        cluster_indices: list[int],
        articles: list[NewsArticlePydantic],
        embeddings: np.ndarray,
    ) -> str:
        """Get representative headline for a cluster.

        Finds the article closest to the cluster centroid.

        Args:
            cluster_indices: Indices of articles in the cluster
            articles: List of all articles
            embeddings: Embedding matrix

        Returns:
            Title of the article closest to centroid
        """
        if not cluster_indices:
            return ""

        # Get embeddings for this cluster
        cluster_embeddings = embeddings[cluster_indices]

        # Calculate centroid
        centroid = np.mean(cluster_embeddings, axis=0)

        # Find article closest to centroid
        distances = np.linalg.norm(cluster_embeddings - centroid, axis=1)
        closest_idx = cluster_indices[np.argmin(distances)]

        return articles[closest_idx].title

    def get_dominant_sentiment(
        self, cluster_indices: list[int], articles: list[NewsArticlePydantic]
    ) -> float:
        """Calculate dominant sentiment for a cluster.

        Args:
            cluster_indices: Indices of articles in the cluster
            articles: List of all articles

        Returns:
            Mean sentiment score (-1.0 to 1.0)
        """
        sentiments = [
            articles[idx].sentiment
            for idx in cluster_indices
            if articles[idx].sentiment is not None
        ]

        if not sentiments:
            return 0.0

        return float(np.mean(sentiments))

    def cluster_and_persist(
        self, anomaly_id: str, articles: list[NewsArticlePydantic]
    ) -> list[NewsCluster]:
        """Cluster news articles and persist to database.

        Args:
            anomaly_id: ID of the anomaly these articles belong to
            articles: List of news articles to cluster

        Returns:
            List of created NewsCluster objects

        Raises:
            ValueError: If no database session is provided
        """
        if self.session is None:
            raise ValueError("Database session required for persistence")

        if not articles:
            logger.warning("No articles to cluster")
            return []

        # Generate embeddings
        articles, embeddings = self.generate_embeddings(articles)

        # Cluster articles
        clusters = self.cluster_articles(articles, embeddings)

        # Create NewsCluster and NewsArticle database records
        news_clusters = []
        news_articles_db = []

        for cluster_id, cluster_indices in clusters.items():
            if cluster_id == -1:
                # Handle noise points - save articles without creating a cluster
                for idx in cluster_indices:
                    article = articles[idx]
                    article_db = NewsArticle(
                        anomaly_id=anomaly_id,
                        source=article.source,
                        title=article.title,
                        url=str(article.url) if article.url else None,
                        published_at=article.published_at,
                        summary=article.summary,
                        cluster_id=-1,  # Noise
                        embedding=embeddings[idx].tolist(),
                        timing_tag=article.timing_tag,
                        time_diff_minutes=article.time_diff_minutes,
                    )
                    news_articles_db.append(article_db)
                continue

            # Get cluster metadata
            centroid_summary = self.get_cluster_centroid_summary(
                cluster_indices, articles, embeddings
            )
            dominant_sentiment = self.get_dominant_sentiment(cluster_indices, articles)

            # Create cluster articles with embeddings
            cluster_article_ids = []
            for idx in cluster_indices:
                article = articles[idx]
                article_db = NewsArticle(
                    anomaly_id=anomaly_id,
                    source=article.source,
                    title=article.title,
                    url=str(article.url) if article.url else None,
                    published_at=article.published_at,
                    summary=article.summary,
                    cluster_id=cluster_id,
                    embedding=embeddings[idx].tolist(),
                    timing_tag=article.timing_tag,
                    time_diff_minutes=article.time_diff_minutes,
                )
                news_articles_db.append(article_db)
                # Will get ID after flush
                cluster_article_ids.append(article_db)

            # Create NewsCluster record
            cluster = NewsCluster(
                anomaly_id=anomaly_id,
                cluster_number=cluster_id,
                article_ids=[],  # Will update after articles are persisted
                centroid_summary=centroid_summary,
                dominant_sentiment=dominant_sentiment,
                size=len(cluster_indices),
            )
            news_clusters.append((cluster, cluster_article_ids))

        # Persist to database
        logger.info(
            f"Persisting {len(news_articles_db)} articles and "
            f"{len(news_clusters)} clusters"
        )

        # Add articles first to generate IDs
        self.session.add_all(news_articles_db)
        self.session.flush()  # Generate IDs

        # Update cluster article_ids and add clusters
        final_clusters = []
        for cluster, article_objs in news_clusters:
            cluster.article_ids = [article.id for article in article_objs]
            self.session.add(cluster)
            final_clusters.append(cluster)

        self.session.commit()

        logger.info(
            f"Successfully clustered and persisted {len(news_articles_db)} articles "
            f"into {len(final_clusters)} clusters"
        )

        return final_clusters

    def cluster_for_anomaly(
        self, anomaly_id: str, articles: list[NewsArticlePydantic]
    ) -> dict[str, Any]:
        """Cluster news articles for an anomaly (without persistence).

        Useful for testing or analysis without database writes.

        Args:
            anomaly_id: ID of the anomaly
            articles: List of news articles to cluster

        Returns:
            Dictionary with clustering results:
                - clusters: mapping of cluster_id -> article indices
                - embeddings: numpy array of embeddings
                - n_clusters: number of clusters found
                - n_noise: number of noise points
        """
        if not articles:
            return {
                "clusters": {},
                "embeddings": np.array([]),
                "n_clusters": 0,
                "n_noise": 0,
            }

        # Generate embeddings
        articles, embeddings = self.generate_embeddings(articles)

        # Cluster articles
        clusters = self.cluster_articles(articles, embeddings)

        # Calculate stats
        n_clusters = len([c for c in clusters.keys() if c != -1])
        n_noise = len(clusters.get(-1, []))

        return {
            "clusters": clusters,
            "embeddings": embeddings,
            "n_clusters": n_clusters,
            "n_noise": n_noise,
        }
