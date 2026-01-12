"""LiteLLM client wrapper for provider-agnostic LLM access."""

import asyncio
import logging
import os
from typing import Any

import litellm
from litellm import acompletion, completion
from litellm.exceptions import (
    APIConnectionError,
    APIError,
    AuthenticationError,
    RateLimitError,
)

from config.settings import settings
from src.llm.models import (
    LLMAuthenticationError,
    LLMConnectionError,
    LLMError,
    LLMInvalidRequestError,
    LLMMessage,
    LLMRateLimitError,
    LLMRequest,
    LLMResponse,
    LLMRole,
    TokenUsage,
    ToolCall,
)

logger = logging.getLogger(__name__)


class LLMClient:
    """Provider-agnostic LLM client using LiteLLM.

    Supports OpenAI, Anthropic Claude, DeepSeek, and Ollama with automatic API key
    management, token tracking, and error handling with retries.

    Example:
        ```python
        from src.llm import LLMClient, LLMMessage, LLMRole

        client = LLMClient()

        # Simple chat completion
        messages = [
            LLMMessage(role=LLMRole.SYSTEM, content="You are a helpful assistant."),
            LLMMessage(role=LLMRole.USER, content="What is 2+2?"),
        ]

        response = await client.chat_completion(messages)
        print(response.content)  # "4"
        print(response.usage.total_tokens)  # e.g., 45
        ```
    """

    def __init__(
        self,
        provider: str | None = None,
        model: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
        max_retries: int = 3,
        timeout: int = 60,
    ):
        """Initialize the LLM client.

        Args:
            provider: LLM provider ('openai', 'anthropic', 'deepseek', 'ollama').
                Defaults to settings.llm.provider
            model: Model identifier. Defaults to settings.llm.model
            temperature: Sampling temperature. Defaults to settings.llm.temperature
            max_tokens: Maximum tokens to generate. Defaults to settings.llm.max_tokens
            max_retries: Maximum number of retry attempts for failed requests
            timeout: Request timeout in seconds
        """
        self.provider = provider or settings.llm.provider
        self.model = model or settings.llm.model
        self.temperature = temperature or settings.llm.temperature
        self.max_tokens = max_tokens or settings.llm.max_tokens
        self.max_retries = max_retries
        self.timeout = timeout

        # Set up API keys based on provider
        self._setup_api_keys()

        # Configure LiteLLM
        litellm.drop_params = True  # Drop unsupported params instead of erroring
        litellm.set_verbose = False  # Disable verbose logging

        logger.info(
            f"Initialized LLM client: provider={self.provider}, model={self.model}"
        )

    def _setup_api_keys(self) -> None:
        """Set up API keys for the selected provider."""
        if self.provider == "openai":
            if settings.llm.openai_api_key:
                os.environ["OPENAI_API_KEY"] = settings.llm.openai_api_key
            elif not os.getenv("OPENAI_API_KEY"):
                raise LLMAuthenticationError(
                    "OpenAI API key not found. Set OPENAI_API_KEY environment variable.",
                    provider="openai",
                )

        elif self.provider == "anthropic":
            if settings.llm.anthropic_api_key:
                os.environ["ANTHROPIC_API_KEY"] = settings.llm.anthropic_api_key
            elif not os.getenv("ANTHROPIC_API_KEY"):
                raise LLMAuthenticationError(
                    "Anthropic API key not found. Set ANTHROPIC_API_KEY environment variable.",
                    provider="anthropic",
                )

        elif self.provider == "deepseek":
            if settings.llm.deepseek_api_key:
                os.environ["DEEPSEEK_API_KEY"] = settings.llm.deepseek_api_key
            elif not os.getenv("DEEPSEEK_API_KEY"):
                raise LLMAuthenticationError(
                    "DeepSeek API key not found. Set DEEPSEEK_API_KEY environment variable.",
                    provider="deepseek",
                )

        elif self.provider == "ollama":
            # Ollama typically doesn't need API keys (local deployment)
            if settings.llm.ollama_api_base:
                os.environ["OLLAMA_API_BASE"] = settings.llm.ollama_api_base
            logger.info(f"Using Ollama at {settings.llm.ollama_api_base}")

        else:
            raise ValueError(
                f"Unsupported provider: {self.provider}. "
                "Choose from: openai, anthropic, deepseek, ollama"
            )

    def _get_model_name(self) -> str:
        """Get the full model name for LiteLLM.

        LiteLLM expects provider-prefixed model names for some providers.

        Returns:
            Formatted model name (e.g., 'ollama/llama2', 'deepseek/deepseek-chat', 'claude-3-5-haiku-20241022')
        """
        if self.provider == "ollama":
            # Ollama models need 'ollama/' prefix
            if not self.model.startswith("ollama/"):
                return f"ollama/{self.model}"
        elif self.provider == "deepseek":
            # DeepSeek models need 'deepseek/' prefix
            if not self.model.startswith("deepseek/"):
                return f"deepseek/{self.model}"
        elif self.provider == "anthropic":
            # Anthropic models don't need prefix (claude-3-5-haiku-20241022)
            return self.model
        elif self.provider == "openai":
            # OpenAI models don't need prefix (gpt-4o, gpt-4o-mini)
            return self.model

        return self.model

    async def chat_completion(
        self,
        messages: list[LLMMessage] | list[dict[str, Any]],
        model: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
        tools: list[dict[str, Any]] | None = None,
        tool_choice: str | dict[str, Any] | None = None,
    ) -> LLMResponse:
        """Generate a chat completion using the configured LLM.

        Args:
            messages: Conversation history
            model: Override default model
            temperature: Override default temperature
            max_tokens: Override default max_tokens
            tools: Tool definitions for function calling (optional)
            tool_choice: How to handle tool calls (optional)

        Returns:
            LLMResponse with generated content and metadata

        Raises:
            LLMRateLimitError: Rate limit exceeded
            LLMAuthenticationError: Invalid API key
            LLMConnectionError: Network/connection error
            LLMInvalidRequestError: Invalid request parameters
            LLMError: Other LLM errors
        """
        # Convert Pydantic models to dicts if needed
        if messages and isinstance(messages[0], LLMMessage):
            messages = [msg.model_dump(exclude_none=True) for msg in messages]

        # Use provided values or defaults
        model_name = self._get_model_name() if model is None else model
        temp = temperature if temperature is not None else self.temperature
        max_tok = max_tokens if max_tokens is not None else self.max_tokens

        # Build request kwargs
        kwargs: dict[str, Any] = {
            "model": model_name,
            "messages": messages,
            "temperature": temp,
            "max_tokens": max_tok,
            "timeout": self.timeout,
        }

        # Add tool calling params if provided
        if tools:
            kwargs["tools"] = tools
        if tool_choice:
            kwargs["tool_choice"] = tool_choice

        # Retry logic
        for attempt in range(self.max_retries):
            try:
                logger.debug(
                    f"LLM request (attempt {attempt + 1}/{self.max_retries}): "
                    f"model={model_name}, messages={len(messages)}"
                )

                # Make async request to LiteLLM
                response = await acompletion(**kwargs)

                # Parse response
                return self._parse_response(response)

            except RateLimitError as e:
                if attempt < self.max_retries - 1:
                    wait_time = 2**attempt  # Exponential backoff
                    logger.warning(
                        f"Rate limit hit, retrying in {wait_time}s (attempt {attempt + 1})"
                    )
                    await asyncio.sleep(wait_time)
                    continue
                raise LLMRateLimitError(
                    "Rate limit exceeded after retries",
                    provider=self.provider,
                    model=model_name,
                    original_error=e,
                )

            except AuthenticationError as e:
                raise LLMAuthenticationError(
                    f"Authentication failed: {str(e)}",
                    provider=self.provider,
                    model=model_name,
                    original_error=e,
                )

            except APIConnectionError as e:
                if attempt < self.max_retries - 1:
                    wait_time = 2**attempt
                    logger.warning(
                        f"Connection error, retrying in {wait_time}s (attempt {attempt + 1})"
                    )
                    await asyncio.sleep(wait_time)
                    continue
                raise LLMConnectionError(
                    f"Connection failed after {self.max_retries} attempts: {str(e)}",
                    provider=self.provider,
                    model=model_name,
                    original_error=e,
                )

            except APIError as e:
                error_msg = str(e)
                if "invalid" in error_msg.lower():
                    raise LLMInvalidRequestError(
                        f"Invalid request: {error_msg}",
                        provider=self.provider,
                        model=model_name,
                        original_error=e,
                    )
                raise LLMError(
                    f"API error: {error_msg}",
                    provider=self.provider,
                    model=model_name,
                    original_error=e,
                )

            except Exception as e:
                logger.error(f"Unexpected error in LLM call: {e}")
                raise LLMError(
                    f"Unexpected error: {str(e)}",
                    provider=self.provider,
                    model=model_name,
                    original_error=e,
                )

        # Should never reach here due to raises in loop
        raise LLMError("Max retries exceeded", provider=self.provider, model=model_name)

    def chat_completion_sync(
        self,
        messages: list[LLMMessage] | list[dict[str, Any]],
        model: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
        tools: list[dict[str, Any]] | None = None,
        tool_choice: str | dict[str, Any] | None = None,
    ) -> LLMResponse:
        """Synchronous version of chat_completion.

        See chat_completion() for parameter details.
        """
        # Convert Pydantic models to dicts if needed
        if messages and isinstance(messages[0], LLMMessage):
            messages = [msg.model_dump(exclude_none=True) for msg in messages]

        model_name = self._get_model_name() if model is None else model
        temp = temperature if temperature is not None else self.temperature
        max_tok = max_tokens if max_tokens is not None else self.max_tokens

        kwargs: dict[str, Any] = {
            "model": model_name,
            "messages": messages,
            "temperature": temp,
            "max_tokens": max_tok,
            "timeout": self.timeout,
        }

        if tools:
            kwargs["tools"] = tools
        if tool_choice:
            kwargs["tool_choice"] = tool_choice

        # Use synchronous completion
        try:
            response = completion(**kwargs)
            return self._parse_response(response)
        except Exception as e:
            logger.error(f"Sync LLM call failed: {e}")
            raise LLMError(
                f"Sync call failed: {str(e)}",
                provider=self.provider,
                model=model_name,
                original_error=e,
            )

    def _parse_response(self, response: Any) -> LLMResponse:
        """Parse LiteLLM response into our LLMResponse model.

        Args:
            response: Raw response from LiteLLM

        Returns:
            Parsed LLMResponse object
        """
        choice = response.choices[0]
        message = choice.message

        # Extract tool calls if present
        tool_calls = None
        if hasattr(message, "tool_calls") and message.tool_calls:
            tool_calls = [
                ToolCall(
                    id=tc.id,
                    type=tc.type,
                    function={
                        "name": tc.function.name,
                        "arguments": tc.function.arguments,
                    },
                )
                for tc in message.tool_calls
            ]

        # Extract token usage
        usage = TokenUsage(
            prompt_tokens=response.usage.prompt_tokens,
            completion_tokens=response.usage.completion_tokens,
            total_tokens=response.usage.total_tokens,
        )

        return LLMResponse(
            id=response.id,
            content=message.content,
            role=LLMRole.ASSISTANT,
            tool_calls=tool_calls,
            finish_reason=choice.finish_reason,
            model=response.model,
            usage=usage,
        )

    async def simple_prompt(
        self, prompt: str, system_message: str | None = None
    ) -> str:
        """Simple helper for single-turn prompts.

        Args:
            prompt: User prompt
            system_message: Optional system message

        Returns:
            Generated text response
        """
        messages = []
        if system_message:
            messages.append(LLMMessage(role=LLMRole.SYSTEM, content=system_message))
        messages.append(LLMMessage(role=LLMRole.USER, content=prompt))

        response = await self.chat_completion(messages)
        return response.content or ""

    def get_total_tokens_used(self) -> int:
        """Get total tokens used across all requests.

        Note: This requires tracking in application code, as LiteLLM
        doesn't maintain a session-wide token counter.

        Returns:
            Total tokens (placeholder for now, requires external tracking)
        """
        logger.warning(
            "Token tracking requires application-level implementation. "
            "Track usage from individual LLMResponse.usage objects."
        )
        return 0
