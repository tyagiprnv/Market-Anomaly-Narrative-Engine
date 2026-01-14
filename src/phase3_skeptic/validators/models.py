"""Pydantic models for Phase 3 validation engine."""

from typing import Any
from pydantic import BaseModel, Field

from src.database.models import Narrative, Anomaly, NewsArticle, NewsCluster


class ValidatorOutput(BaseModel):
    """Output from individual validators.

    This model represents the result of a single validator's execution,
    including success status, validation score, and reasoning.
    """

    success: bool = Field(
        description="Whether the validator executed successfully"
    )
    passed: bool | None = Field(
        default=None,
        description="Whether the validation check passed (None if not applicable)"
    )
    score: float | None = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Validation score from 0-1 (1=perfect, None if not applicable)"
    )
    confidence: float = Field(
        default=1.0,
        ge=0.0,
        le=1.0,
        description="Confidence in the assessment (0-1)"
    )
    reasoning: str | None = Field(
        default=None,
        description="Explanation of the validation result"
    )
    error: str | None = Field(
        default=None,
        description="Error message if execution failed"
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional metadata for debugging/analysis"
    )

    model_config = {"arbitrary_types_allowed": True}


class ValidationContext(BaseModel):
    """Context passed to all validators.

    This bundles all the data needed for validation into a single object.
    """

    narrative: Narrative = Field(
        description="The narrative being validated"
    )
    anomaly: Anomaly = Field(
        description="The anomaly that the narrative explains"
    )
    news_articles: list[NewsArticle] = Field(
        default_factory=list,
        description="News articles related to the anomaly"
    )
    news_clusters: list[NewsCluster] | None = Field(
        default=None,
        description="Clustered news articles (optional)"
    )

    model_config = {"arbitrary_types_allowed": True}


class ValidationResult(BaseModel):
    """Aggregated validation result from all validators.

    This represents the final validation verdict after running all validators
    and aggregating their results with weighted scoring.
    """

    validated: bool = Field(
        default=True,
        description="Whether validation was attempted"
    )
    validation_passed: bool = Field(
        description="Final validation verdict (pass/fail)"
    )
    validation_reason: str = Field(
        description="Human-readable explanation of the verdict"
    )
    validator_results: dict[str, ValidatorOutput] = Field(
        default_factory=dict,
        description="Individual results from each validator"
    )
    aggregate_score: float = Field(
        ge=0.0,
        le=1.0,
        description="Weighted average score across all validators"
    )
    confidence: float = Field(
        ge=0.0,
        le=1.0,
        description="Overall confidence in the validation result"
    )

    model_config = {"arbitrary_types_allowed": True}
