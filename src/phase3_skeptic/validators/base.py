"""Abstract base class for all validators."""

from abc import ABC, abstractmethod
from typing import ClassVar, Any

from src.database.models import Narrative, Anomaly, NewsArticle
from .models import ValidatorOutput


class Validator(ABC):
    """Abstract base class for all validators.

    All validators must inherit from this class and implement the validate() method.
    Validators assess different aspects of narrative quality and plausibility.

    Attributes:
        name: Unique identifier for the validator
        description: Human-readable description of what the validator checks
        weight: Relative weight for aggregation (higher = more important)
    """

    name: ClassVar[str]
    description: ClassVar[str]
    weight: ClassVar[float] = 1.0  # Weight for aggregation (0-1)

    @abstractmethod
    async def validate(
        self,
        narrative: Narrative,
        anomaly: Anomaly,
        news_articles: list[NewsArticle],
        **kwargs: Any
    ) -> ValidatorOutput:
        """Validate narrative against specific criteria.

        Args:
            narrative: The narrative being validated
            anomaly: The anomaly that triggered the narrative
            news_articles: Related news articles
            **kwargs: Additional context (e.g., news_clusters, settings)

        Returns:
            ValidatorOutput with validation results

        Raises:
            Should catch all exceptions and return ValidatorOutput with error field set
        """
        pass

    @classmethod
    def get_validator_info(cls) -> dict[str, Any]:
        """Get validator metadata for introspection.

        Returns:
            Dictionary with name, description, and weight
        """
        return {
            "name": cls.name,
            "description": cls.description,
            "weight": cls.weight,
        }

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}(name={self.name}, weight={self.weight})>"
