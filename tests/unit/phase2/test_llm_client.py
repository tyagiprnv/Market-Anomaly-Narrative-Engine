"""Unit tests for LLM client."""

import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from litellm.exceptions import (
    APIConnectionError,
    AuthenticationError,
    RateLimitError,
)

from src.llm import (
    LLMAuthenticationError,
    LLMClient,
    LLMConnectionError,
    LLMMessage,
    LLMRateLimitError,
    LLMRole,
)


@pytest.fixture
def mock_litellm_response():
    """Create a mock LiteLLM response."""
    response = MagicMock()
    response.id = "chatcmpl-test123"
    response.model = "gpt-4o-mini"

    choice = MagicMock()
    choice.finish_reason = "stop"

    message = MagicMock()
    message.content = "This is a test response"
    message.tool_calls = None

    choice.message = message
    response.choices = [choice]

    usage = MagicMock()
    usage.prompt_tokens = 10
    usage.completion_tokens = 20
    usage.total_tokens = 30
    response.usage = usage

    return response


@pytest.fixture
def mock_env_vars():
    """Set up mock environment variables for testing."""
    original_env = os.environ.copy()

    # Set test API keys
    os.environ["OPENAI_API_KEY"] = "sk-test-openai"
    os.environ["ANTHROPIC_API_KEY"] = "sk-ant-test-anthropic"
    os.environ["DEEPSEEK_API_KEY"] = "sk-test-deepseek"
    os.environ["OLLAMA_API_BASE"] = "http://localhost:11434"

    yield

    # Restore original environment
    os.environ.clear()
    os.environ.update(original_env)


class TestLLMClientInitialization:
    """Test LLM client initialization."""

    def test_init_with_defaults(self, mock_env_vars):
        """Test initialization with default settings."""
        with patch("src.llm.client.settings") as mock_settings:
            mock_settings.llm.provider = "openai"
            mock_settings.llm.model = "gpt-4o-mini"
            mock_settings.llm.temperature = 0.7
            mock_settings.llm.max_tokens = 1000
            mock_settings.llm.openai_api_key = "sk-test"
            mock_settings.llm.anthropic_api_key = None
            mock_settings.llm.ollama_api_base = "http://localhost:11434"

            client = LLMClient()

            assert client.provider == "openai"
            assert client.model == "gpt-4o-mini"
            assert client.temperature == 0.7
            assert client.max_tokens == 1000

    def test_init_with_custom_params(self, mock_env_vars):
        """Test initialization with custom parameters."""
        with patch("src.llm.client.settings") as mock_settings:
            mock_settings.llm.provider = "openai"
            mock_settings.llm.openai_api_key = "sk-test"
            mock_settings.llm.anthropic_api_key = None
            mock_settings.llm.ollama_api_base = "http://localhost:11434"

            client = LLMClient(
                provider="anthropic",
                model="claude-3-5-sonnet-20241022",
                temperature=0.5,
                max_tokens=2000,
            )

            assert client.provider == "anthropic"
            assert client.model == "claude-3-5-sonnet-20241022"
            assert client.temperature == 0.5
            assert client.max_tokens == 2000

    def test_init_missing_api_key(self, mock_env_vars):
        """Test initialization fails without API key."""
        # Clear environment
        os.environ.pop("OPENAI_API_KEY", None)

        with patch("src.llm.client.settings") as mock_settings:
            mock_settings.llm.provider = "openai"
            mock_settings.llm.openai_api_key = None
            mock_settings.llm.anthropic_api_key = None

            with pytest.raises(LLMAuthenticationError, match="OpenAI API key not found"):
                LLMClient(provider="openai")

    def test_init_unsupported_provider(self, mock_env_vars):
        """Test initialization with unsupported provider."""
        with patch("src.llm.client.settings") as mock_settings:
            mock_settings.llm.provider = "invalid_provider"
            mock_settings.llm.openai_api_key = "sk-test"

            with pytest.raises(ValueError, match="Unsupported provider"):
                LLMClient()


class TestLLMClientModelNames:
    """Test model name formatting for different providers."""

    def test_ollama_model_prefix(self, mock_env_vars):
        """Test Ollama models get 'ollama/' prefix."""
        with patch("src.llm.client.settings") as mock_settings:
            mock_settings.llm.provider = "ollama"
            mock_settings.llm.model = "llama2"
            mock_settings.llm.ollama_api_base = "http://localhost:11434"

            client = LLMClient(provider="ollama")
            model_name = client._get_model_name()

            assert model_name == "ollama/llama2"

    def test_anthropic_model_no_prefix(self, mock_env_vars):
        """Test Anthropic models don't get prefix."""
        with patch("src.llm.client.settings") as mock_settings:
            mock_settings.llm.provider = "anthropic"
            mock_settings.llm.model = "claude-3-5-haiku-20241022"
            mock_settings.llm.anthropic_api_key = "sk-ant-test"

            client = LLMClient(provider="anthropic")
            model_name = client._get_model_name()

            assert model_name == "claude-3-5-haiku-20241022"

    def test_openai_model_no_prefix(self, mock_env_vars):
        """Test OpenAI models don't get prefix."""
        with patch("src.llm.client.settings") as mock_settings:
            mock_settings.llm.provider = "openai"
            mock_settings.llm.model = "gpt-4o"
            mock_settings.llm.openai_api_key = "sk-test"

            client = LLMClient(provider="openai")
            model_name = client._get_model_name()

            assert model_name == "gpt-4o"

    def test_deepseek_model_prefix(self, mock_env_vars):
        """Test DeepSeek models get 'deepseek/' prefix."""
        with patch("src.llm.client.settings") as mock_settings:
            mock_settings.llm.provider = "deepseek"
            mock_settings.llm.model = "deepseek-chat"
            mock_settings.llm.deepseek_api_key = "sk-test"

            client = LLMClient(provider="deepseek")
            model_name = client._get_model_name()

            assert model_name == "deepseek/deepseek-chat"


class TestLLMClientChatCompletion:
    """Test chat completion methods."""

    @pytest.mark.asyncio
    async def test_chat_completion_success(
        self, mock_env_vars, mock_litellm_response
    ):
        """Test successful chat completion."""
        with patch("src.llm.client.settings") as mock_settings:
            mock_settings.llm.provider = "openai"
            mock_settings.llm.model = "gpt-4o-mini"
            mock_settings.llm.temperature = 0.3
            mock_settings.llm.max_tokens = 500
            mock_settings.llm.openai_api_key = "sk-test"

            with patch("src.llm.client.acompletion", new_callable=AsyncMock) as mock_acompletion:
                mock_acompletion.return_value = mock_litellm_response

                client = LLMClient()
                messages = [
                    LLMMessage(role=LLMRole.USER, content="Hello, world!"),
                ]

                response = await client.chat_completion(messages)

                assert response.content == "This is a test response"
                assert response.role == LLMRole.ASSISTANT
                assert response.finish_reason == "stop"
                assert response.usage.prompt_tokens == 10
                assert response.usage.completion_tokens == 20
                assert response.usage.total_tokens == 30

                # Verify acompletion was called correctly
                mock_acompletion.assert_called_once()
                call_kwargs = mock_acompletion.call_args[1]
                assert call_kwargs["model"] == "gpt-4o-mini"
                assert len(call_kwargs["messages"]) == 1
                assert call_kwargs["temperature"] == 0.3

    @pytest.mark.asyncio
    async def test_chat_completion_with_dict_messages(
        self, mock_env_vars, mock_litellm_response
    ):
        """Test chat completion with dict messages instead of LLMMessage objects."""
        with patch("src.llm.client.settings") as mock_settings:
            mock_settings.llm.provider = "openai"
            mock_settings.llm.openai_api_key = "sk-test"

            with patch("src.llm.client.acompletion", new_callable=AsyncMock) as mock_acompletion:
                mock_acompletion.return_value = mock_litellm_response

                client = LLMClient()
                messages = [{"role": "user", "content": "Hello"}]

                response = await client.chat_completion(messages)

                assert response.content == "This is a test response"

    @pytest.mark.asyncio
    async def test_chat_completion_rate_limit_retry(self, mock_env_vars):
        """Test retry logic on rate limit error."""
        with patch("src.llm.client.settings") as mock_settings:
            mock_settings.llm.provider = "openai"
            mock_settings.llm.openai_api_key = "sk-test"

            with patch("src.llm.client.acompletion", new_callable=AsyncMock) as mock_acompletion:
                # Fail with rate limit 3 times (max retries)
                mock_acompletion.side_effect = RateLimitError(
                    "Rate limit exceeded",
                    llm_provider="openai",
                    model="gpt-4o-mini",
                )

                client = LLMClient(max_retries=3)
                messages = [LLMMessage(role=LLMRole.USER, content="Test")]

                with pytest.raises(LLMRateLimitError):
                    await client.chat_completion(messages)

                # Should have tried 3 times
                assert mock_acompletion.call_count == 3

    @pytest.mark.asyncio
    async def test_chat_completion_auth_error(self, mock_env_vars):
        """Test authentication error handling."""
        with patch("src.llm.client.settings") as mock_settings:
            mock_settings.llm.provider = "openai"
            mock_settings.llm.openai_api_key = "sk-test"

            with patch("src.llm.client.acompletion", new_callable=AsyncMock) as mock_acompletion:
                mock_acompletion.side_effect = AuthenticationError(
                    "Invalid API key",
                    llm_provider="openai",
                    model="gpt-4o-mini",
                )

                client = LLMClient()
                messages = [LLMMessage(role=LLMRole.USER, content="Test")]

                with pytest.raises(LLMAuthenticationError, match="Authentication failed"):
                    await client.chat_completion(messages)

    @pytest.mark.asyncio
    async def test_chat_completion_connection_error_retry(
        self, mock_env_vars, mock_litellm_response
    ):
        """Test connection error retry and eventual success."""
        with patch("src.llm.client.settings") as mock_settings:
            mock_settings.llm.provider = "openai"
            mock_settings.llm.openai_api_key = "sk-test"

            with patch("src.llm.client.acompletion", new_callable=AsyncMock) as mock_acompletion:
                # Fail twice, then succeed
                mock_acompletion.side_effect = [
                    APIConnectionError("Connection failed", llm_provider="openai", model="gpt-4o-mini"),
                    APIConnectionError("Connection failed", llm_provider="openai", model="gpt-4o-mini"),
                    mock_litellm_response,
                ]

                client = LLMClient(max_retries=3)
                messages = [LLMMessage(role=LLMRole.USER, content="Test")]

                response = await client.chat_completion(messages)

                # Should succeed on third try
                assert response.content == "This is a test response"
                assert mock_acompletion.call_count == 3

    @pytest.mark.asyncio
    async def test_chat_completion_with_tools(
        self, mock_env_vars, mock_litellm_response
    ):
        """Test chat completion with tool definitions."""
        with patch("src.llm.client.settings") as mock_settings:
            mock_settings.llm.provider = "openai"
            mock_settings.llm.openai_api_key = "sk-test"

            # Mock tool call in response
            tool_call = MagicMock()
            tool_call.id = "call_123"
            tool_call.type = "function"
            tool_call.function.name = "get_weather"
            tool_call.function.arguments = '{"location": "San Francisco"}'

            mock_litellm_response.choices[0].message.tool_calls = [tool_call]

            with patch("src.llm.client.acompletion", new_callable=AsyncMock) as mock_acompletion:
                mock_acompletion.return_value = mock_litellm_response

                client = LLMClient()
                messages = [LLMMessage(role=LLMRole.USER, content="What's the weather?")]

                tools = [
                    {
                        "type": "function",
                        "function": {
                            "name": "get_weather",
                            "description": "Get weather for a location",
                            "parameters": {
                                "type": "object",
                                "properties": {
                                    "location": {"type": "string"},
                                },
                                "required": ["location"],
                            },
                        },
                    }
                ]

                response = await client.chat_completion(messages, tools=tools)

                assert response.tool_calls is not None
                assert len(response.tool_calls) == 1
                assert response.tool_calls[0].function["name"] == "get_weather"

                # Verify tools were passed to acompletion
                call_kwargs = mock_acompletion.call_args[1]
                assert "tools" in call_kwargs


class TestLLMClientSimplePrompt:
    """Test simple prompt helper method."""

    @pytest.mark.asyncio
    async def test_simple_prompt(self, mock_env_vars, mock_litellm_response):
        """Test simple_prompt helper method."""
        with patch("src.llm.client.settings") as mock_settings:
            mock_settings.llm.provider = "openai"
            mock_settings.llm.openai_api_key = "sk-test"

            with patch("src.llm.client.acompletion", new_callable=AsyncMock) as mock_acompletion:
                mock_acompletion.return_value = mock_litellm_response

                client = LLMClient()
                result = await client.simple_prompt("What is 2+2?")

                assert result == "This is a test response"

    @pytest.mark.asyncio
    async def test_simple_prompt_with_system(
        self, mock_env_vars, mock_litellm_response
    ):
        """Test simple_prompt with system message."""
        with patch("src.llm.client.settings") as mock_settings:
            mock_settings.llm.provider = "openai"
            mock_settings.llm.openai_api_key = "sk-test"

            with patch("src.llm.client.acompletion", new_callable=AsyncMock) as mock_acompletion:
                mock_acompletion.return_value = mock_litellm_response

                client = LLMClient()
                result = await client.simple_prompt(
                    "What is 2+2?", system_message="You are a math tutor."
                )

                assert result == "This is a test response"

                # Verify system message was included
                call_kwargs = mock_acompletion.call_args[1]
                messages = call_kwargs["messages"]
                assert len(messages) == 2
                assert messages[0]["role"] == "system"
                assert messages[1]["role"] == "user"


class TestLLMClientSyncCompletion:
    """Test synchronous completion method."""

    def test_sync_completion(self, mock_env_vars, mock_litellm_response):
        """Test synchronous chat completion."""
        with patch("src.llm.client.settings") as mock_settings:
            mock_settings.llm.provider = "openai"
            mock_settings.llm.openai_api_key = "sk-test"

            with patch("src.llm.client.completion") as mock_completion:
                mock_completion.return_value = mock_litellm_response

                client = LLMClient()
                messages = [LLMMessage(role=LLMRole.USER, content="Hello")]

                response = client.chat_completion_sync(messages)

                assert response.content == "This is a test response"
                mock_completion.assert_called_once()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
