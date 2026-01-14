"""Phase 3: Validation Engine (Skeptic).

This module validates AI-generated market narratives using a hybrid approach:
- Rule-based validators (fast, deterministic)
- LLM-based validator (comprehensive, conditional)

Example:
    ```python
    from src.phase3_skeptic import ValidationEngine
    from src.database.connection import get_db_session

    with get_db_session() as session:
        engine = ValidationEngine(session=session)
        result = await engine.validate_narrative(narrative)

        if result.validation_passed:
            print(f"Narrative validated (score: {result.aggregate_score:.2f})")
        else:
            print(f"Validation failed: {result.validation_reason}")
    ```
"""

from .validator import ValidationEngine
from .validators import (
    Validator,
    ValidatorOutput,
    ValidationContext,
    ValidationResult,
    ValidatorRegistry,
)

__all__ = [
    "ValidationEngine",
    "Validator",
    "ValidatorOutput",
    "ValidationContext",
    "ValidationResult",
    "ValidatorRegistry",
]
