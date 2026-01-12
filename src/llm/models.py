"""Pydantic models for LLM requests and responses."""

from datetime import datetime
from enum import Enum
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class LLMRole(str, Enum):
    """Message roles in LLM conversations."""

    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"


class LLMMessage(BaseModel):
    """A single message in an LLM conversation.

    Attributes:
        role: The role of the message sender
        content: The message content
        name: Optional name for tool messages
        tool_call_id: Optional ID for tool response messages
    """

    role: LLMRole
    content: str
    name: str | None = None
    tool_call_id: str | None = None


class ToolCall(BaseModel):
    """A tool call made by the LLM.

    Attributes:
        id: Unique identifier for this tool call
        type: Type of tool call (always "function")
        function: Function call details
    """

    id: str
    type: str = "function"
    function: dict[str, Any]


class TokenUsage(BaseModel):
    """Token usage statistics for an LLM call.

    Attributes:
        prompt_tokens: Number of tokens in the prompt
        completion_tokens: Number of tokens in the completion
        total_tokens: Total tokens used
    """

    prompt_tokens: int
    completion_tokens: int
    total_tokens: int


class LLMResponse(BaseModel):
    """Response from an LLM call.

    Attributes:
        id: Unique identifier for this response
        content: The generated text content (if any)
        role: The role of the response (always "assistant")
        tool_calls: Any tool calls requested by the LLM
        finish_reason: Why the generation stopped
        model: Model that generated this response
        usage: Token usage statistics
        created_at: Timestamp when response was created
    """

    id: str
    content: str | None
    role: LLMRole = LLMRole.ASSISTANT
    tool_calls: list[ToolCall] | None = None
    finish_reason: str
    model: str
    usage: TokenUsage
    created_at: datetime = Field(default_factory=datetime.now)


class LLMRequest(BaseModel):
    """Request to send to an LLM.

    Attributes:
        messages: Conversation history
        model: Model identifier (provider-specific)
        temperature: Sampling temperature (0.0-2.0)
        max_tokens: Maximum tokens to generate
        tools: Tool definitions for function calling (optional)
        tool_choice: How to handle tool calls (optional)
        request_id: Unique identifier for tracking this request
    """

    messages: list[LLMMessage]
    model: str
    temperature: float = 0.3
    max_tokens: int = 500
    tools: list[dict[str, Any]] | None = None
    tool_choice: str | dict[str, Any] | None = None
    request_id: UUID = Field(default_factory=uuid4)


class LLMError(Exception):
    """Base exception for LLM client errors.

    Attributes:
        message: Error description
        provider: LLM provider that raised the error
        model: Model that was being called
        original_error: The underlying exception (if any)
    """

    def __init__(
        self,
        message: str,
        provider: str | None = None,
        model: str | None = None,
        original_error: Exception | None = None,
    ):
        self.message = message
        self.provider = provider
        self.model = model
        self.original_error = original_error
        super().__init__(self.message)


class LLMRateLimitError(LLMError):
    """Rate limit exceeded error."""

    pass


class LLMAuthenticationError(LLMError):
    """Authentication/API key error."""

    pass


class LLMConnectionError(LLMError):
    """Network connection error."""

    pass


class LLMInvalidRequestError(LLMError):
    """Invalid request parameters error."""

    pass
