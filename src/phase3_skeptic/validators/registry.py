"""Validator registry for managing and executing validators."""

import asyncio
import logging
from typing import Any

from sqlalchemy.orm import Session

from src.llm.client import LLMClient
from config.settings import settings
from .base import Validator
from .models import ValidationContext, ValidatorOutput
from .sentiment_match import SentimentMatchValidator
from .timing_coherence import TimingCoherenceValidator
from .magnitude_coherence import MagnitudeCoherenceValidator
from .tool_consistency import ToolConsistencyValidator
from .narrative_quality import NarrativeQualityValidator
from .judge_llm import JudgeLLMValidator

logger = logging.getLogger(__name__)


class ValidatorRegistry:
    """Registry for all validators.

    Manages validator lifecycle and provides execution orchestration
    with support for parallel and sequential execution.
    """

    def __init__(
        self,
        session: Session | None = None,
        llm_client: LLMClient | None = None
    ):
        """Initialize validator registry.

        Args:
            session: Database session (for validators that need DB access)
            llm_client: LLM client (for Judge LLM validator)
        """
        self.session = session
        self.llm_client = llm_client
        self._validators: dict[str, Validator] = {}
        self._rule_validators: dict[str, Validator] = {}
        self._llm_validators: dict[str, Validator] = {}

        # Register all validators
        self._register_all_validators()

        logger.info(
            f"Initialized ValidatorRegistry with {len(self._validators)} validators "
            f"({len(self._rule_validators)} rule-based, {len(self._llm_validators)} LLM-based)"
        )

    def _register_all_validators(self) -> None:
        """Register all validators."""
        # Rule-based validators (fast, deterministic)
        rule_validators = [
            SentimentMatchValidator(),
            TimingCoherenceValidator(),
            MagnitudeCoherenceValidator(),
            ToolConsistencyValidator(),
            NarrativeQualityValidator(),
        ]

        for validator in rule_validators:
            self._validators[validator.name] = validator
            self._rule_validators[validator.name] = validator
            logger.debug(f"Registered rule validator: {validator.name}")

        # LLM validator (conditional, expensive)
        if settings.validation.judge_llm_enabled:
            judge_validator = JudgeLLMValidator(llm_client=self.llm_client)
            self._validators[judge_validator.name] = judge_validator
            self._llm_validators[judge_validator.name] = judge_validator
            logger.debug(f"Registered LLM validator: {judge_validator.name}")
        else:
            logger.info("Judge LLM validator disabled in settings")

    def get_validator(self, name: str) -> Validator | None:
        """Get a validator by name.

        Args:
            name: Validator name

        Returns:
            Validator instance or None if not found
        """
        return self._validators.get(name)

    def get_all_validators(self) -> dict[str, Validator]:
        """Get all registered validators.

        Returns:
            Dictionary of validator name to validator instance
        """
        return self._validators.copy()

    def get_rule_validators(self) -> dict[str, Validator]:
        """Get only rule-based validators.

        Returns:
            Dictionary of rule validator name to validator instance
        """
        return self._rule_validators.copy()

    def get_llm_validators(self) -> dict[str, Validator]:
        """Get only LLM-based validators.

        Returns:
            Dictionary of LLM validator name to validator instance
        """
        return self._llm_validators.copy()

    async def validate_all(
        self,
        context: ValidationContext,
        parallel: bool = True,
        include_llm: bool = True
    ) -> dict[str, ValidatorOutput]:
        """Run all validators on a context.

        Args:
            context: Validation context with narrative, anomaly, news
            parallel: Whether to run validators in parallel (faster)
            include_llm: Whether to include LLM validators

        Returns:
            Dictionary of validator name to ValidatorOutput
        """
        # Determine which validators to run
        validators_to_run = self._rule_validators.copy()
        if include_llm:
            validators_to_run.update(self._llm_validators)

        if parallel:
            return await self._validate_parallel(context, validators_to_run)
        else:
            return await self._validate_sequential(context, validators_to_run)

    async def validate_rules_only(
        self,
        context: ValidationContext,
        parallel: bool = True
    ) -> dict[str, ValidatorOutput]:
        """Run only rule-based validators.

        Args:
            context: Validation context
            parallel: Whether to run in parallel

        Returns:
            Dictionary of validator name to ValidatorOutput
        """
        if parallel:
            return await self._validate_parallel(context, self._rule_validators)
        else:
            return await self._validate_sequential(context, self._rule_validators)

    async def validate_llm_only(
        self,
        context: ValidationContext
    ) -> dict[str, ValidatorOutput]:
        """Run only LLM-based validators.

        Args:
            context: Validation context

        Returns:
            Dictionary of validator name to ValidatorOutput
        """
        return await self._validate_sequential(context, self._llm_validators)

    async def _validate_parallel(
        self,
        context: ValidationContext,
        validators: dict[str, Validator]
    ) -> dict[str, ValidatorOutput]:
        """Run validators in parallel using asyncio.gather.

        Args:
            context: Validation context
            validators: Validators to run

        Returns:
            Dictionary of validator name to ValidatorOutput
        """
        logger.debug(f"Running {len(validators)} validators in parallel")

        # Create tasks for all validators
        tasks = [
            self._run_validator_safe(name, validator, context)
            for name, validator in validators.items()
        ]

        # Run all in parallel
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Build results dict
        output: dict[str, ValidatorOutput] = {}
        for (name, _), result in zip(validators.items(), results):
            if isinstance(result, Exception):
                logger.error(f"Validator {name} raised exception: {result}")
                output[name] = ValidatorOutput(
                    success=False,
                    error=f"Validator exception: {str(result)}",
                    score=None,
                    confidence=0.0,
                    reasoning="Validator raised exception"
                )
            else:
                output[name] = result

        return output

    async def _validate_sequential(
        self,
        context: ValidationContext,
        validators: dict[str, Validator]
    ) -> dict[str, ValidatorOutput]:
        """Run validators sequentially.

        Args:
            context: Validation context
            validators: Validators to run

        Returns:
            Dictionary of validator name to ValidatorOutput
        """
        logger.debug(f"Running {len(validators)} validators sequentially")

        results: dict[str, ValidatorOutput] = {}

        for name, validator in validators.items():
            result = await self._run_validator_safe(name, validator, context)
            results[name] = result

        return results

    async def _run_validator_safe(
        self,
        name: str,
        validator: Validator,
        context: ValidationContext
    ) -> ValidatorOutput:
        """Run a single validator with error isolation.

        Args:
            name: Validator name
            validator: Validator instance
            context: Validation context

        Returns:
            ValidatorOutput (with error field set if validator fails)
        """
        try:
            logger.debug(f"Running validator: {name}")
            result = await validator.validate(
                context.narrative,
                context.anomaly,
                context.news_articles,
                news_clusters=context.news_clusters
            )
            logger.debug(
                f"Validator {name} completed: "
                f"success={result.success}, score={result.score}"
            )
            return result

        except Exception as e:
            logger.error(f"Validator {name} failed with exception: {e}", exc_info=True)
            return ValidatorOutput(
                success=False,
                error=f"Validator exception: {str(e)}",
                score=None,
                confidence=0.0,
                reasoning="Validator raised exception"
            )

    def get_validator_info(self) -> dict[str, dict[str, Any]]:
        """Get metadata about all registered validators.

        Returns:
            Dictionary of validator name to metadata (name, description, weight)
        """
        return {
            name: validator.get_validator_info()
            for name, validator in self._validators.items()
        }
