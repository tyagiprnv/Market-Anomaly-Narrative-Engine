"""Base class for agent tools."""

from abc import ABC, abstractmethod
from typing import Any, ClassVar
from pydantic import BaseModel

from src.phase2_journalist.tools.models import ToolInput, ToolOutput


class AgentTool(ABC):
    """Abstract base class for all agent tools.

    Each tool must implement:
    - name: Unique tool identifier
    - description: What the tool does
    - parameters_schema: JSON schema for tool parameters
    - execute(): Main tool logic

    Tools are designed to be called by LLM agents through function calling.
    """

    name: ClassVar[str]
    description: ClassVar[str]

    @classmethod
    @abstractmethod
    def get_parameters_schema(cls) -> dict[str, Any]:
        """Get JSON schema for tool parameters.

        This schema is passed to the LLM for function calling.

        Returns:
            JSON schema dict compatible with OpenAI/Anthropic function calling
        """
        pass

    @abstractmethod
    async def execute(self, **kwargs: Any) -> ToolOutput:
        """Execute the tool with given parameters.

        Args:
            **kwargs: Tool-specific parameters

        Returns:
            ToolOutput with results or error message
        """
        pass

    @classmethod
    def get_tool_definition(cls) -> dict[str, Any]:
        """Get complete tool definition for LLM function calling.

        Returns:
            Tool definition dict with name, description, and parameters
        """
        return {
            "type": "function",
            "function": {
                "name": cls.name,
                "description": cls.description,
                "parameters": cls.get_parameters_schema(),
            },
        }

    def _create_error_output(
        self, error_message: str, output_class: type[ToolOutput]
    ) -> ToolOutput:
        """Create an error output.

        Args:
            error_message: Error description
            output_class: ToolOutput subclass to instantiate

        Returns:
            ToolOutput instance with error
        """
        return output_class(success=False, error=error_message)
