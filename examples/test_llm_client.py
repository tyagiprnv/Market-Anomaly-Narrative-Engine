"""Example usage of the LLM client.

This script demonstrates how to use the LLMClient for various tasks.

Before running:
1. Set up your .env file with appropriate API keys:
   - ANTHROPIC_API_KEY for Claude models
   - OPENAI_API_KEY for GPT models
   - DEEPSEEK_API_KEY for DeepSeek models
   - Or use Ollama locally (no key needed)

2. Configure provider in .env:
   LLM__PROVIDER=anthropic  # or openai, deepseek, ollama
   LLM__MODEL=claude-3-5-haiku-20241022  # or gpt-4o-mini, deepseek-chat, llama2, etc.

Usage:
    python examples/test_llm_client.py
"""

import asyncio
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.llm import LLMClient, LLMMessage, LLMRole


async def example_simple_prompt():
    """Example 1: Simple single-turn prompt."""
    print("=" * 60)
    print("Example 1: Simple Prompt")
    print("=" * 60)

    client = LLMClient()

    prompt = "Explain in one sentence what causes cryptocurrency price volatility."
    print(f"\nPrompt: {prompt}")

    response = await client.simple_prompt(
        prompt,
        system_message="You are a financial analyst specializing in cryptocurrency markets.",
    )

    print(f"\nResponse: {response}")
    print()


async def example_multi_turn_conversation():
    """Example 2: Multi-turn conversation."""
    print("=" * 60)
    print("Example 2: Multi-turn Conversation")
    print("=" * 60)

    client = LLMClient()

    messages = [
        LLMMessage(
            role=LLMRole.SYSTEM,
            content="You are a helpful cryptocurrency trading assistant.",
        ),
        LLMMessage(role=LLMRole.USER, content="What is Bitcoin?"),
    ]

    # First turn
    print("\nUser: What is Bitcoin?")
    response1 = await client.chat_completion(messages)
    print(f"Assistant: {response1.content}")
    print(f"Tokens used: {response1.usage.total_tokens}")

    # Add response to conversation
    messages.append(LLMMessage(role=LLMRole.ASSISTANT, content=response1.content))

    # Second turn
    messages.append(
        LLMMessage(role=LLMRole.USER, content="How is it different from Ethereum?")
    )

    print("\nUser: How is it different from Ethereum?")
    response2 = await client.chat_completion(messages)
    print(f"Assistant: {response2.content}")
    print(f"Tokens used: {response2.usage.total_tokens}")
    print()


async def example_with_custom_parameters():
    """Example 3: Using custom parameters."""
    print("=" * 60)
    print("Example 3: Custom Parameters")
    print("=" * 60)

    # Override default settings
    client = LLMClient(temperature=0.9, max_tokens=200)

    prompt = "Write a creative story about a Bitcoin price surge."
    print(f"\nPrompt: {prompt}")
    print(f"Temperature: 0.9 (more creative)")
    print(f"Max tokens: 200")

    response = await client.simple_prompt(prompt)

    print(f"\nResponse: {response}")
    print()


async def example_with_tool_calling():
    """Example 4: Function/tool calling."""
    print("=" * 60)
    print("Example 4: Tool Calling")
    print("=" * 60)

    client = LLMClient()

    # Define a tool for getting crypto prices
    tools = [
        {
            "type": "function",
            "function": {
                "name": "get_crypto_price",
                "description": "Get the current price of a cryptocurrency",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "symbol": {
                            "type": "string",
                            "description": "The crypto symbol (e.g., BTC, ETH)",
                        },
                    },
                    "required": ["symbol"],
                },
            },
        }
    ]

    messages = [
        LLMMessage(
            role=LLMRole.USER,
            content="What's the current price of Bitcoin?",
        )
    ]

    print("\nUser: What's the current price of Bitcoin?")
    print("(With tool calling enabled)")

    response = await client.chat_completion(messages, tools=tools)

    if response.tool_calls:
        print(f"\nLLM requested tool call:")
        for tool_call in response.tool_calls:
            print(f"  Function: {tool_call.function['name']}")
            print(f"  Arguments: {tool_call.function['arguments']}")
    else:
        print(f"\nResponse: {response.content}")
    print()


async def example_error_handling():
    """Example 5: Error handling."""
    print("=" * 60)
    print("Example 5: Error Handling")
    print("=" * 60)

    from src.llm import LLMAuthenticationError, LLMError

    # Try with invalid API key (will fail)
    print("\nTrying with invalid provider to demonstrate error handling...")

    try:
        client = LLMClient(provider="invalid_provider")
        await client.simple_prompt("Test")
    except ValueError as e:
        print(f"Caught ValueError: {e}")

    print("\nError handling ensures graceful failures!")
    print()


async def example_token_tracking():
    """Example 6: Token usage tracking."""
    print("=" * 60)
    print("Example 6: Token Usage Tracking")
    print("=" * 60)

    client = LLMClient()

    prompts = [
        "What is Bitcoin?",
        "What is Ethereum?",
        "What is DeFi?",
    ]

    total_tokens = 0

    for prompt in prompts:
        print(f"\nPrompt: {prompt}")
        response = await client.chat_completion(
            [LLMMessage(role=LLMRole.USER, content=prompt)]
        )

        print(f"Response: {response.content[:100]}...")
        print(
            f"Tokens: {response.usage.prompt_tokens} (prompt) + "
            f"{response.usage.completion_tokens} (completion) = "
            f"{response.usage.total_tokens} (total)"
        )

        total_tokens += response.usage.total_tokens

    print(f"\nTotal tokens used across all prompts: {total_tokens}")
    print()


async def example_different_providers():
    """Example 7: Switching between providers."""
    print("=" * 60)
    print("Example 7: Different Providers")
    print("=" * 60)

    prompt = "Explain cryptocurrency in one sentence."

    # Note: This requires having API keys for all providers
    providers = [
        ("openai", "gpt-4o-mini"),
        ("anthropic", "claude-3-5-haiku-20241022"),
        ("deepseek", "deepseek-chat"),
        # ("ollama", "llama2"),  # Uncomment if you have Ollama running locally
    ]

    for provider, model in providers:
        print(f"\n{provider.upper()} ({model}):")
        try:
            client = LLMClient(provider=provider, model=model)
            response = await client.simple_prompt(prompt)
            print(f"Response: {response}")
        except Exception as e:
            print(f"Error: {e}")
            print("(Make sure you have the API key configured)")

    print()


async def main():
    """Run all examples."""
    print("\n" + "=" * 60)
    print("LLM Client Examples")
    print("=" * 60)

    try:
        # Run examples
        await example_simple_prompt()
        await example_multi_turn_conversation()
        await example_with_custom_parameters()
        await example_with_tool_calling()
        await example_error_handling()
        await example_token_tracking()

        # Uncomment to test different providers (requires API keys)
        # await example_different_providers()

        print("=" * 60)
        print("All examples completed!")
        print("=" * 60)

    except Exception as e:
        print(f"\n❌ Error running examples: {e}")
        print(
            "\nMake sure you have:\n"
            "1. Set up your .env file with API keys\n"
            "2. Configured LLM__PROVIDER in .env\n"
            "3. Internet connection (for OpenAI/Anthropic)\n"
            "   OR Ollama running locally (for ollama provider)"
        )
        raise


if __name__ == "__main__":
    asyncio.run(main())
