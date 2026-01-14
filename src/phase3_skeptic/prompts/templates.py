"""Context formatting templates for validation prompts."""

from datetime import datetime
from src.database.models import Narrative, Anomaly, NewsArticle


def format_validation_context(
    narrative: Narrative,
    anomaly: Anomaly,
    news_articles: list[NewsArticle]
) -> str:
    """Format validation context for Judge LLM.

    Args:
        narrative: The narrative being validated
        anomaly: The anomaly that triggered the narrative
        news_articles: Related news articles

    Returns:
        Formatted context string
    """
    # Format anomaly information
    anomaly_section = f"""ANOMALY DETAILS:
- Symbol: {anomaly.symbol}
- Type: {anomaly.anomaly_type.value}
- Detected at: {anomaly.detected_at.strftime('%Y-%m-%d %H:%M:%S UTC')}
- Z-score: {anomaly.z_score:.2f}
- Price change: {anomaly.price_change_pct:.2f}%
- Confidence: {anomaly.confidence:.2f}
- Price before: ${anomaly.price_before:.2f}
- Price at detection: ${anomaly.price_at_detection:.2f}
"""

    if anomaly.volume_change_pct:
        anomaly_section += f"- Volume change: {anomaly.volume_change_pct:.2f}%\n"

    # Format narrative
    narrative_section = f"""NARRATIVE (being validated):
"{narrative.narrative_text}"

- Confidence score: {narrative.confidence_score if narrative.confidence_score else 'N/A'}
- Tools used: {', '.join(narrative.tools_used) if narrative.tools_used else 'None'}
- LLM: {narrative.llm_provider}/{narrative.llm_model}
"""

    # Format tool results
    tool_results = narrative.tool_results or {}
    tool_section = "TOOL RESULTS:\n"

    if not tool_results:
        tool_section += "- No tool results available\n"
    else:
        for tool_name, result in tool_results.items():
            tool_section += f"\n{tool_name}:\n"
            if isinstance(result, dict):
                for key, value in result.items():
                    tool_section += f"  - {key}: {value}\n"
            else:
                tool_section += f"  {result}\n"

    # Format news articles
    news_section = f"NEWS ARTICLES ({len(news_articles)} total):\n"

    if not news_articles:
        news_section += "- No news articles available\n"
    else:
        # Show up to 5 most relevant articles
        for i, article in enumerate(news_articles[:5], 1):
            timing_info = ""
            if article.timing_tag:
                timing_info = f" [{article.timing_tag}"
                if article.time_diff_minutes:
                    timing_info += f", {article.time_diff_minutes:.0f}min"
                timing_info += "]"

            news_section += f"\n{i}. {article.title}"
            news_section += f"\n   Source: {article.source} | Published: {article.published_at.strftime('%Y-%m-%d %H:%M:%S UTC')}"
            news_section += f"{timing_info}"

            if article.summary:
                news_section += f"\n   Summary: {article.summary[:150]}..."
            news_section += "\n"

        if len(news_articles) > 5:
            news_section += f"\n... and {len(news_articles) - 5} more articles\n"

    # Combine all sections
    context = f"""{anomaly_section}
{narrative_section}
{tool_section}
{news_section}

VALIDATION TASK:
Evaluate the plausibility, causality, and coherence of this narrative.
Consider the timing, magnitude, sentiment alignment, and tool evidence.
"""

    return context


def format_anomaly_summary(anomaly: Anomaly) -> str:
    """Format a brief anomaly summary.

    Args:
        anomaly: The anomaly

    Returns:
        Brief summary string
    """
    direction = "spike" if "spike" in anomaly.anomaly_type.value else "drop"
    return (
        f"{anomaly.symbol} {direction} at {anomaly.detected_at.strftime('%H:%M UTC')}: "
        f"{anomaly.price_change_pct:+.2f}% (z-score: {anomaly.z_score:.1f})"
    )


def format_news_timing_summary(news_articles: list[NewsArticle]) -> str:
    """Format news timing summary.

    Args:
        news_articles: List of news articles

    Returns:
        Timing summary string
    """
    if not news_articles:
        return "No news articles"

    pre_event = sum(1 for a in news_articles if a.timing_tag == "pre_event")
    post_event = sum(1 for a in news_articles if a.timing_tag == "post_event")
    unknown = len(news_articles) - pre_event - post_event

    parts = []
    if pre_event:
        parts.append(f"{pre_event} pre-event")
    if post_event:
        parts.append(f"{post_event} post-event")
    if unknown:
        parts.append(f"{unknown} unknown timing")

    return ", ".join(parts)
