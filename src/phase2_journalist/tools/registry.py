"""Tool registry for agent tools."""

import logging
from typing import Any
from sqlalchemy.orm import Session

from src.phase2_journalist.tools.base import AgentTool
from src.phase2_journalist.tools.verify_timestamp import VerifyTimestampTool
from src.phase2_journalist.tools.sentiment_check import SentimentCheckTool
from src.phase2_journalist.tools.search_historical import SearchHistoricalTool
from src.phase2_journalist.tools.check_market_context import CheckMarketContextTool
from src.phase2_journalist.tools.check_social_sentiment import CheckSocialSentimentTool

logger = logging.getLogger(__name__)


class ToolRegistry:
    """Registry for all agent tools.

    Provides a centralized way to access tools, get their definitions for
    LLM function calling, and execute them.

    Example:
        ```python
        from src.phase2_journalist.tools import ToolRegistry

        # Initialize registry with database session
        registry = ToolRegistry(session=db_session)

        # Get all tool definitions for LLM
        tool_defs = registry.get_all_tool_definitions()

        # Execute a tool by name
        result = await registry.execute_tool(
            "verify_timestamp",
            news_timestamp="2024-01-15T14:05:00Z",
            anomaly_timestamp="2024-01-15T14:10:00Z"
        )
        ```
    """

    def __init__(self, session: Session | None = None):
        """Initialize the tool registry.

        Args:
            session: Optional SQLAlchemy session for tools that need database access
        """
        self.session = session
        self._tools: dict[str, AgentTool] = {}
        self._register_all_tools()

    def _register_all_tools(self) -> None:
        """Register all available tools."""
        # Tools that don't need database session
        self._tools["verify_timestamp"] = VerifyTimestampTool()
        self._tools["sentiment_check"] = SentimentCheckTool()
        self._tools["check_social_sentiment"] = CheckSocialSentimentTool()

        # Tools that need database session
        self._tools["search_historical"] = SearchHistoricalTool(session=self.session)
        self._tools["check_market_context"] = CheckMarketContextTool(session=self.session)

        logger.info(f"Registered {len(self._tools)} agent tools")

    def get_tool(self, name: str) -> AgentTool | None:
        """Get a tool by name.

        Args:
            name: Tool name

        Returns:
            Tool instance or None if not found
        """
        return self._tools.get(name)

    def get_all_tools(self) -> dict[str, AgentTool]:
        """Get all registered tools.

        Returns:
            Dictionary mapping tool names to tool instances
        """
        return self._tools.copy()

    def get_tool_names(self) -> list[str]:
        """Get names of all registered tools.

        Returns:
            List of tool names
        """
        return list(self._tools.keys())

    def get_all_tool_definitions(self) -> list[dict[str, Any]]:
        """Get tool definitions for all tools (for LLM function calling).

        Returns:
            List of tool definition dicts
        """
        return [tool.__class__.get_tool_definition() for tool in self._tools.values()]

    async def execute_tool(self, tool_name: str, **kwargs: Any) -> Any:
        """Execute a tool by name.

        Args:
            tool_name: Name of the tool to execute
            **kwargs: Tool-specific parameters

        Returns:
            Tool output (ToolOutput subclass)

        Raises:
            ValueError: If tool not found
        """
        tool = self.get_tool(tool_name)
        if not tool:
            raise ValueError(f"Tool not found: {tool_name}")

        # Add session to kwargs if needed and available
        if self.session and "session" not in kwargs:
            kwargs["session"] = self.session

        logger.debug(f"Executing tool: {tool_name}")
        return await tool.execute(**kwargs)

    def set_session(self, session: Session) -> None:
        """Update the database session for all tools.

        Args:
            session: New SQLAlchemy session
        """
        self.session = session

        # Update session for tools that need it
        if "search_historical" in self._tools:
            self._tools["search_historical"].session = session
        if "check_market_context" in self._tools:
            self._tools["check_market_context"].session = session

        logger.debug("Updated database session for all tools")


# Convenience function to get tool definitions
def get_all_tool_definitions(session: Session | None = None) -> list[dict[str, Any]]:
    """Get all tool definitions for LLM function calling.

    Args:
        session: Optional SQLAlchemy session

    Returns:
        List of tool definition dicts ready for LLM function calling
    """
    registry = ToolRegistry(session=session)
    return registry.get_all_tool_definitions()
