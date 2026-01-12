"""Phase 2 Journalist Agent - Generates narratives explaining market anomalies."""

import json
import logging
import time
from typing import Any

from sqlalchemy.orm import Session

from src.database.models import Anomaly, Narrative, NewsArticle
from src.llm import LLMClient
from src.llm.models import LLMMessage, LLMRole, LLMResponse, ToolCall
from src.phase2_journalist.prompts import JOURNALIST_SYSTEM_PROMPT, format_anomaly_context
from src.phase2_journalist.tools import ToolRegistry

logger = logging.getLogger(__name__)


class JournalistAgent:
    """
    Phase 2 agent that generates narratives explaining market anomalies.

    The agent uses an LLM with a tool loop to gather evidence and generate
    2-sentence narratives explaining why anomalies occurred.

    Responsibilities:
    - Orchestrate LLM + tool loop
    - Build context from anomaly + news
    - Track tool usage and results
    - Generate 2-sentence narratives
    - Save results to database
    """

    def __init__(
        self,
        llm_client: LLMClient | None = None,
        tool_registry: ToolRegistry | None = None,
        session: Session | None = None,
        max_tool_iterations: int = 10,
    ):
        """
        Initialize journalist agent with dependencies.

        Args:
            llm_client: LLM client for narrative generation (defaults to settings-based client)
            tool_registry: Tool registry for executing tools (defaults to new instance)
            session: Database session for persistence (required if tool_registry not provided)
            max_tool_iterations: Maximum tool loop iterations before failing
        """
        self.llm_client = llm_client or LLMClient()
        self.max_tool_iterations = max_tool_iterations
        self.session = session

        # Initialize tool registry
        if tool_registry:
            self.tool_registry = tool_registry
        elif session:
            self.tool_registry = ToolRegistry(session=session)
        else:
            raise ValueError("Either tool_registry or session must be provided")

    async def generate_narrative(
        self,
        anomaly: Anomaly,
        news_articles: list[NewsArticle] | None = None,
    ) -> Narrative:
        """
        Generate narrative for an anomaly.

        This is the main entry point. It orchestrates the tool loop, generates
        the narrative, and persists it to the database.

        Args:
            anomaly: The detected anomaly to explain
            news_articles: Related news articles (optional)

        Returns:
            Narrative object (persisted to database)

        Raises:
            ValueError: If session is not available for persistence
        """
        if not self.session:
            raise ValueError("Session is required for narrative persistence")

        logger.info(
            f"Generating narrative for anomaly {anomaly.id} ({anomaly.symbol} {anomaly.anomaly_type.value})"
        )

        try:
            # Build conversation messages
            messages = [
                LLMMessage(role=LLMRole.SYSTEM, content=JOURNALIST_SYSTEM_PROMPT),
                LLMMessage(
                    role=LLMRole.USER,
                    content=self._build_context_prompt(anomaly, news_articles or []),
                ),
            ]

            # Run tool loop to generate narrative
            narrative_text, metadata = await self._run_tool_loop(messages)

            logger.info(f"Narrative generated successfully: {narrative_text[:100]}...")

        except Exception as e:
            logger.error(f"Failed to generate narrative: {e}", exc_info=True)
            # Generate fallback narrative
            narrative_text = self._create_fallback_narrative(anomaly, e)
            metadata = {
                "tools_used": [],
                "tool_results": {"error": str(e), "fallback": True},
                "generation_time": 0.0,
                "fallback": True,
            }

        # Create and persist narrative
        narrative = Narrative(
            anomaly_id=anomaly.id,
            narrative_text=narrative_text,
            confidence_score=metadata.get("confidence", 0.5),
            tools_used=metadata.get("tools_used", []),
            tool_results=metadata.get("tool_results", {}),
            llm_provider=self.llm_client.provider,
            llm_model=self.llm_client.model,
            generation_time_seconds=metadata.get("generation_time", 0.0),
            validated=False,  # Phase 3 will validate
        )

        self.session.add(narrative)
        self.session.commit()
        self.session.refresh(narrative)

        logger.info(f"Narrative saved to database with ID {narrative.id}")

        return narrative

    def _build_context_prompt(
        self,
        anomaly: Anomaly,
        news_articles: list[NewsArticle],
    ) -> str:
        """
        Build user message with anomaly context.

        Args:
            anomaly: The detected anomaly
            news_articles: Related news articles

        Returns:
            Formatted context string
        """
        return format_anomaly_context(anomaly, news_articles)

    async def _run_tool_loop(
        self,
        messages: list[LLMMessage],
    ) -> tuple[str, dict[str, Any]]:
        """
        Execute LLM + tool loop until narrative generated.

        Loop logic:
        - While finish_reason == "tool_calls" and iteration < max:
          1. Parse tool calls from response
          2. Execute each tool via ToolRegistry
          3. Append tool results to messages
          4. Call LLM again
        - Break when finish_reason == "stop"

        Args:
            messages: Initial conversation messages

        Returns:
            Tuple of (narrative_text, metadata_dict)

        Raises:
            RuntimeError: If max iterations exceeded
            ValueError: If unexpected finish_reason
        """
        tool_executions = []
        start_time = time.perf_counter()

        for iteration in range(1, self.max_tool_iterations + 1):
            logger.debug(f"Tool loop iteration {iteration}/{self.max_tool_iterations}")

            # Call LLM with tools
            response = await self.llm_client.chat_completion(
                messages=messages,
                tools=self.tool_registry.get_all_tool_definitions(),
                tool_choice="auto",  # LLM decides which tools to use
            )

            # Check finish reason
            if response.finish_reason == "stop":
                # Narrative generated
                generation_time = time.perf_counter() - start_time
                metadata = self._build_metadata(response, tool_executions, generation_time)

                logger.info(
                    f"Narrative generated in {generation_time:.2f}s "
                    f"after {iteration} iterations using {len(tool_executions)} tools"
                )

                return response.content, metadata

            elif response.finish_reason == "tool_calls":
                # Execute tools and continue loop
                if not response.tool_calls:
                    raise ValueError("finish_reason is 'tool_calls' but no tool_calls present")

                logger.debug(f"Executing {len(response.tool_calls)} tool calls")

                tool_results = await self._execute_tool_calls(response.tool_calls)
                tool_executions.extend(tool_results)

                # Append assistant message to conversation
                messages.append(
                    LLMMessage(
                        role=LLMRole.ASSISTANT,
                        content=response.content if response.content else "",
                    )
                )

                # Append tool results to conversation
                for tool_result in tool_results:
                    messages.append(
                        LLMMessage(
                            role=LLMRole.TOOL,
                            content=json.dumps(tool_result["result"]),
                            tool_call_id=tool_result["tool_call_id"],
                        )
                    )

            else:
                raise ValueError(f"Unexpected finish_reason: {response.finish_reason}")

        # Max iterations reached
        raise RuntimeError(
            f"Max tool iterations ({self.max_tool_iterations}) exceeded without generating narrative"
        )

    async def _execute_tool_calls(
        self,
        tool_calls: list[ToolCall],
    ) -> list[dict[str, Any]]:
        """
        Execute all tool calls and track results.

        Args:
            tool_calls: List of tool calls from LLM response

        Returns:
            List of tool execution results with metadata
        """
        tool_results = []

        for tool_call in tool_calls:
            tool_name = tool_call.function["name"]
            tool_call_id = tool_call.id

            try:
                # Parse arguments (they come as JSON string)
                arguments = json.loads(tool_call.function["arguments"])

                logger.debug(f"Executing tool: {tool_name} with args: {arguments}")

                # Execute tool
                result = await self.tool_registry.execute_tool(tool_name, **arguments)

                # Convert Pydantic model to dict if needed
                if hasattr(result, "model_dump"):
                    result_dict = result.model_dump()
                else:
                    result_dict = result

                tool_results.append(
                    {
                        "tool_name": tool_name,
                        "tool_call_id": tool_call_id,
                        "arguments": arguments,
                        "result": result_dict,
                        "success": result_dict.get("success", True),
                    }
                )

                logger.debug(f"Tool {tool_name} executed successfully")

            except Exception as e:
                logger.error(f"Tool {tool_name} failed: {e}", exc_info=True)

                # Return error to LLM (non-fatal)
                tool_results.append(
                    {
                        "tool_name": tool_name,
                        "tool_call_id": tool_call_id,
                        "arguments": tool_call.function.get("arguments", "{}"),
                        "result": {"success": False, "error": str(e)},
                        "success": False,
                    }
                )

        return tool_results

    def _create_fallback_narrative(
        self,
        anomaly: Anomaly,
        error: Exception,
    ) -> str:
        """
        Generate minimal fallback narrative on failure.

        Format: "{symbol} experienced a {pct}% {direction} movement. Cause unknown."
        Follows "never halluciate" principle per user preference.

        Args:
            anomaly: The anomaly that couldn't be explained
            error: The exception that caused failure

        Returns:
            Fallback narrative string
        """
        direction = "increase" if anomaly.price_change_pct > 0 else "decrease"
        abs_pct = abs(anomaly.price_change_pct)

        return (
            f"{anomaly.symbol} experienced a {abs_pct:.2f}% price {direction} "
            f"at {anomaly.detected_at.strftime('%Y-%m-%d %H:%M:%S')} UTC. Cause unknown."
        )

    def _build_metadata(
        self,
        response: LLMResponse,
        tool_executions: list[dict],
        generation_time: float,
    ) -> dict[str, Any]:
        """
        Aggregate metadata for Narrative model.

        Args:
            response: Final LLM response with narrative
            tool_executions: List of tool execution results
            generation_time: Total generation time in seconds

        Returns:
            Metadata dictionary with tools_used, tool_results, timing, etc.
        """
        # Extract unique tool names
        tools_used = list({exec["tool_name"] for exec in tool_executions})

        # Aggregate tool results by tool name
        tool_results = {}
        for exec in tool_executions:
            tool_name = exec["tool_name"]

            if tool_name not in tool_results:
                tool_results[tool_name] = []

            tool_results[tool_name].append(
                {
                    "arguments": exec["arguments"],
                    "result": exec["result"],
                    "success": exec["success"],
                }
            )

        return {
            "tools_used": tools_used,
            "tool_results": tool_results,
            "generation_time": generation_time,
            "token_usage": (
                {
                    "prompt_tokens": response.usage.prompt_tokens,
                    "completion_tokens": response.usage.completion_tokens,
                    "total_tokens": response.usage.total_tokens,
                }
                if response.usage
                else None
            ),
            "confidence": 0.5,  # Placeholder for future confidence scoring
        }
