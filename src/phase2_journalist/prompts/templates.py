"""Context templates for formatting anomaly data."""

from datetime import datetime

from src.database.models import Anomaly, NewsArticle

ANOMALY_CONTEXT_TEMPLATE = """ANOMALY DETECTED:
- Symbol: {symbol}
- Type: {anomaly_type_display}
- Detected at: {detected_at_formatted} UTC
- Price change: {price_change_pct:+.2f}%
- Z-score: {z_score:.2f}
- Confidence: {confidence:.2%}

PRICE SNAPSHOT:
- Before: ${price_before:,.2f}
- At detection: ${price_at_detection:,.2f}
- Volume change: {volume_change_pct:+.2f}%

RELATED NEWS ({news_count} articles):
{news_list}

Generate a 2-sentence narrative explaining why this anomaly occurred. Use the available tools to verify timing, sentiment, and context."""


def format_anomaly_context(
    anomaly: Anomaly, news_articles: list[NewsArticle] | None = None
) -> str:
    """
    Format anomaly and news articles into a user message for the agent.

    Args:
        anomaly: The detected anomaly to explain
        news_articles: Related news articles (optional)

    Returns:
        Formatted context string for the LLM
    """
    # Handle None or empty news articles
    if not news_articles:
        news_articles = []

    # Format anomaly type for display
    anomaly_type_display = anomaly.anomaly_type.value.replace("_", " ").title()

    # Format datetime
    detected_at_formatted = anomaly.detected_at.strftime("%Y-%m-%d %H:%M:%S")

    # Format news list
    if news_articles:
        news_list_items = []
        for i, article in enumerate(news_articles[:10], 1):  # Limit to 10 articles
            # Format publish time
            time_str = article.published_at.strftime("%Y-%m-%d %H:%M")

            # Format timing tag
            timing_info = ""
            if article.timing_tag:
                timing_info = f" [{article.timing_tag}]"

            news_list_items.append(
                f"{i}. [{article.source}] {article.title} (Published: {time_str}{timing_info})"
            )

        news_list = "\n".join(news_list_items)

        if len(news_articles) > 10:
            news_list += f"\n... and {len(news_articles) - 10} more articles"
    else:
        news_list = "(No related news articles found)"

    # Format the template
    return ANOMALY_CONTEXT_TEMPLATE.format(
        symbol=anomaly.symbol,
        anomaly_type_display=anomaly_type_display,
        detected_at_formatted=detected_at_formatted,
        price_change_pct=anomaly.price_change_pct,
        z_score=anomaly.z_score,
        confidence=anomaly.confidence,
        price_before=anomaly.price_before,
        price_at_detection=anomaly.price_at_detection,
        volume_change_pct=anomaly.volume_change_pct or 0.0,
        news_count=len(news_articles),
        news_list=news_list,
    )
