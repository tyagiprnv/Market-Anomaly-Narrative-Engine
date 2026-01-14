"""Main validation engine orchestrator for Phase 3."""

import logging
from datetime import datetime, UTC

from sqlalchemy.orm import Session

from src.database.models import Narrative, Anomaly, NewsArticle, NewsCluster
from src.llm.client import LLMClient
from config.settings import settings
from .validators import (
    ValidatorRegistry,
    ValidationContext,
    ValidationResult,
    ValidatorOutput,
)

logger = logging.getLogger(__name__)


class ValidationEngine:
    """Main validation orchestrator for Phase 3.

    Coordinates the execution of all validators and aggregates their results
    to produce a final validation verdict. Supports:
    - Parallel rule validator execution
    - Conditional LLM validator execution
    - Weighted score aggregation
    - Database persistence

    Example:
        ```python
        from src.phase3_skeptic import ValidationEngine
        from src.database.connection import get_db_session

        with get_db_session() as session:
            engine = ValidationEngine(session=session)
            result = await engine.validate_narrative(narrative)

            print(f"Validation passed: {result.validation_passed}")
            print(f"Score: {result.aggregate_score:.2f}")
            print(f"Reason: {result.validation_reason}")
        ```
    """

    def __init__(
        self,
        session: Session | None = None,
        llm_client: LLMClient | None = None,
        validator_registry: ValidatorRegistry | None = None
    ):
        """Initialize validation engine.

        Args:
            session: Database session for loading context and persisting results
            llm_client: LLM client for Judge LLM validator
            validator_registry: Validator registry (creates new if None)
        """
        self.session = session
        self.llm_client = llm_client or LLMClient()
        self.validator_registry = validator_registry or ValidatorRegistry(
            session=session,
            llm_client=self.llm_client
        )

        logger.info("Initialized ValidationEngine")

    async def validate_narrative(
        self,
        narrative: Narrative,
    ) -> ValidationResult:
        """Validate a narrative and update database.

        Workflow:
        1. Load context (anomaly, news, clusters) from database
        2. Run rule validators in parallel
        3. Aggregate scores (weighted)
        4. If rules pass threshold, run Judge LLM
        5. Compute final verdict
        6. Update Narrative model in DB
        7. Return ValidationResult

        Args:
            narrative: The narrative to validate (must have anomaly relationship loaded)

        Returns:
            ValidationResult with verdict and scores

        Raises:
            ValueError: If narrative is missing required relationships
        """
        logger.info(f"Starting validation for narrative {narrative.id}")

        # Build validation context
        context = self._build_validation_context(narrative)

        # Phase 1: Run rule validators in parallel
        logger.debug("Phase 1: Running rule validators")
        rule_results = await self._run_rule_validators(context)

        # Calculate initial score from rule validators
        initial_score = self._calculate_aggregate_score(rule_results)
        logger.debug(f"Rule validators aggregate score: {initial_score:.2f}")

        # Phase 2: Conditionally run Judge LLM
        all_results = rule_results.copy()
        if self._should_run_judge_llm(initial_score):
            logger.debug("Phase 2: Running Judge LLM validator")
            judge_results = await self._run_judge_validator(context)
            all_results.update(judge_results)
        else:
            logger.debug(
                f"Skipping Judge LLM (score {initial_score:.2f} < "
                f"threshold {settings.validation.judge_llm_min_trigger_score})"
            )

        # Aggregate all results
        validation_result = self._aggregate_results(all_results)

        # Persist to database
        if self.session:
            self._update_narrative(narrative, validation_result)

        logger.info(
            f"Validation completed for narrative {narrative.id}: "
            f"passed={validation_result.validation_passed}, "
            f"score={validation_result.aggregate_score:.2f}"
        )

        return validation_result

    def _build_validation_context(self, narrative: Narrative) -> ValidationContext:
        """Build validation context from narrative.

        Args:
            narrative: The narrative to validate

        Returns:
            ValidationContext with all required data

        Raises:
            ValueError: If required relationships are missing
        """
        # Get anomaly (should be loaded via relationship)
        anomaly = narrative.anomaly
        if not anomaly:
            raise ValueError(
                f"Narrative {narrative.id} missing anomaly relationship. "
                "Ensure anomaly is loaded or use joinedload/selectinload."
            )

        # Get news articles from anomaly
        news_articles = anomaly.news_articles or []

        # Get news clusters from anomaly (optional)
        news_clusters = anomaly.news_clusters or []

        logger.debug(
            f"Built context: anomaly={anomaly.id}, "
            f"news_articles={len(news_articles)}, "
            f"news_clusters={len(news_clusters)}"
        )

        return ValidationContext(
            narrative=narrative,
            anomaly=anomaly,
            news_articles=news_articles,
            news_clusters=news_clusters if news_clusters else None
        )

    async def _run_rule_validators(
        self,
        context: ValidationContext
    ) -> dict[str, ValidatorOutput]:
        """Run rule-based validators.

        Args:
            context: Validation context

        Returns:
            Dictionary of validator name to ValidatorOutput
        """
        parallel = settings.validation.parallel_validation
        return await self.validator_registry.validate_rules_only(
            context,
            parallel=parallel
        )

    async def _run_judge_validator(
        self,
        context: ValidationContext
    ) -> dict[str, ValidatorOutput]:
        """Run Judge LLM validator.

        Args:
            context: Validation context

        Returns:
            Dictionary of validator name to ValidatorOutput
        """
        return await self.validator_registry.validate_llm_only(context)

    def _should_run_judge_llm(self, rule_score: float) -> bool:
        """Determine if Judge LLM should be called.

        Args:
            rule_score: Aggregate score from rule validators

        Returns:
            True if Judge LLM should be called
        """
        # Check if LLM validation is enabled
        if not settings.validation.judge_llm_enabled:
            return False

        # Check if score meets minimum threshold
        min_score = settings.validation.judge_llm_min_trigger_score
        return rule_score >= min_score

    def _calculate_aggregate_score(
        self,
        validator_results: dict[str, ValidatorOutput]
    ) -> float:
        """Calculate weighted aggregate score.

        Formula:
        Score = Σ(validator_score × validator_weight × confidence)
                / Σ(validator_weight × confidence)

        Args:
            validator_results: Results from validators

        Returns:
            Aggregate score (0-1)
        """
        total_weighted_score = 0.0
        total_weight = 0.0

        for name, output in validator_results.items():
            # Skip failed validators or those without scores
            if not output.success or output.score is None:
                continue

            # Get validator weight
            validator = self.validator_registry.get_validator(name)
            if not validator:
                logger.warning(f"Unknown validator: {name}")
                continue

            # Calculate weighted contribution
            contribution = (
                output.score *
                validator.weight *
                output.confidence
            )
            total_weighted_score += contribution
            total_weight += validator.weight * output.confidence

        # Calculate final score
        if total_weight == 0:
            logger.warning("No validators contributed to score")
            return 0.0

        aggregate_score = total_weighted_score / total_weight
        return max(0.0, min(1.0, aggregate_score))  # Clamp to [0, 1]

    def _aggregate_results(
        self,
        validator_results: dict[str, ValidatorOutput]
    ) -> ValidationResult:
        """Aggregate validator results into final verdict.

        Args:
            validator_results: Results from all validators

        Returns:
            ValidationResult with final verdict
        """
        # Calculate aggregate score
        aggregate_score = self._calculate_aggregate_score(validator_results)

        # Calculate overall confidence
        confidence = self._compute_confidence(validator_results)

        # Determine pass/fail
        validation_passed, validation_reason = self._determine_verdict(
            aggregate_score,
            validator_results
        )

        return ValidationResult(
            validated=True,
            validation_passed=validation_passed,
            validation_reason=validation_reason,
            validator_results=validator_results,
            aggregate_score=aggregate_score,
            confidence=confidence,
        )

    def _compute_confidence(
        self,
        validator_results: dict[str, ValidatorOutput]
    ) -> float:
        """Compute overall confidence from validator confidences.

        Args:
            validator_results: Results from validators

        Returns:
            Overall confidence (0-1)
        """
        confidences = [
            output.confidence
            for output in validator_results.values()
            if output.success
        ]

        if not confidences:
            return 0.0

        # Simple average (could use weighted average)
        return sum(confidences) / len(confidences)

    def _determine_verdict(
        self,
        aggregate_score: float,
        validator_results: dict[str, ValidatorOutput]
    ) -> tuple[bool, str]:
        """Determine final validation verdict.

        Args:
            aggregate_score: Weighted aggregate score
            validator_results: Results from all validators

        Returns:
            Tuple of (validation_passed, validation_reason)
        """
        # Check for critical validator failures
        critical_validators = ["timing_coherence", "sentiment_match"]
        for name in critical_validators:
            result = validator_results.get(name)
            if result and result.success and result.score is not None:
                if result.score < 0.3:
                    return False, f"Critical failure: {name} - {result.reasoning}"

        # Threshold-based verdict
        pass_threshold = settings.validation.pass_threshold

        if aggregate_score >= pass_threshold:
            # Passed
            return True, (
                f"Validation passed (score: {aggregate_score:.2f}, "
                f"threshold: {pass_threshold:.2f})"
            )
        else:
            # Failed - generate explanation
            failures = []
            for name, output in validator_results.items():
                if output.success and output.passed is False:
                    failures.append(f"{name}: {output.reasoning}")

            failure_summary = "; ".join(failures[:3])  # Limit to 3 failures
            return False, (
                f"Validation failed (score: {aggregate_score:.2f}, "
                f"threshold: {pass_threshold:.2f}). Issues: {failure_summary}"
            )

    def _update_narrative(
        self,
        narrative: Narrative,
        result: ValidationResult
    ) -> None:
        """Persist validation results to database.

        Args:
            narrative: The narrative to update
            result: Validation result
        """
        try:
            # Update narrative fields
            narrative.validated = True
            narrative.validation_passed = result.validation_passed
            narrative.validation_reason = result.validation_reason
            narrative.validated_at = datetime.now(UTC)

            # Commit changes
            self.session.commit()
            self.session.refresh(narrative)

            logger.debug(f"Updated narrative {narrative.id} in database")

        except Exception as e:
            logger.error(f"Failed to update narrative in database: {e}")
            self.session.rollback()
            raise
