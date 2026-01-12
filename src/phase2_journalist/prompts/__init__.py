"""Prompt templates for Phase 2 Journalist Agent."""

from .system import JOURNALIST_SYSTEM_PROMPT
from .templates import ANOMALY_CONTEXT_TEMPLATE, format_anomaly_context

__all__ = [
    "JOURNALIST_SYSTEM_PROMPT",
    "ANOMALY_CONTEXT_TEMPLATE",
    "format_anomaly_context",
]
