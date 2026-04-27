"""
ARIA Chat Engine v3.0 — Multi-provider, streaming, chain-of-thought, RAG integration.

Upgraded architecture:
- Multi-provider LLM calls with intelligent fallback
- Streaming responses with chain-of-thought visibility
- RAG integration: retrieve context before each query
- Tool calling across all providers (normalized)
- Session memory: store interactions for future retrieval
- Enhanced system prompt with user/session context

Backwards compatible: works with just Ollama if no other keys are configured.

Usage:
    aria = ARIAv3()
    response = aria.chat("What's the market outlook?")

    # Streaming with chain-of-thought
    for chunk in aria.chat_stream("Analyze this portfolio"):
        print(chunk, end="", flush=True)

    # With tool calling
    response = aria.chat_with_tools("Get latest stock prices")
"""

import os
import json
import logging
import time
from typing import List, Dict, Any, Optional, Generator
from datetime import datetime, timezone
from pathlib import Path

# Import from AI layer
from ..ai_layer.provider_manager import ProviderManager
from ..ai_layer.providers.base import Message, LLMResponse
from ..ai_layer.logger import AILogger
from ..memory.retrieval import MemoryRetrieval
from .system_prompt import get_system_prompt

logger = logging.getLogger("atlas.aria.chat_v3")


class ARIAv3:
    """
    ARIA Chat Engine v3.0 with multi-provider support and advanced features.

    Features:
      - Multi-provider LLM with intelligent fallback
      - Streaming responses with visible chain-of-thought
      - RAG: automatic context injection before each query
      - Tool calling across all providers
      - Session memory and persistence
      - Comprehensive audit logging
    """

    def __init__(self,
                 preferred_provider: Optional[str] = None,
                 model_override: Optional[str] = None,
                 temperature: float = 0.7,
                 max_tokens: int = 4096,
                 memory_retrieval: Optional[MemoryRetrieval] = None,
                 enable_streaming: bool = True,
                 enable_rag: bool = True,
                 enable_cot: bool = True):
        """
        Initialize ARIA v3.0.

        Args:
            preferred_provider: User's preferred provider (groq, openrouter, etc.)
            model_override: Override default model for chosen provider
            temperature: LLM temperature (0.0-1.0)
            max_tokens: Max tokens in response
            memory_retrieval: Optional MemoryRetrieval instance for RAG
            enable_streaming: Enable streaming responses
            enable_rag: Enable RAG context injection
            enable_cot: Enable chain-of-thought reasoning display
        """
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.enable_streaming = enable_streaming
        self.enable_rag = enable_rag
        self.enable_cot = enable_cot

        # Initialize provider manager
        self.provider_manager = ProviderManager(
            preferred_provider=preferred_provider
        )

        # Memory and context
        self.memory_retrieval = memory_retrieval
        self.conversation_history: List[Dict[str, str]] = []

        # Tools
        self.tools: Dict[str, Any] = {}
        self.tool_schemas: List[Dict] = []

        # Session tracking
        self.session_id = self._generate_session_id()
        self.created_at = datetime.now(timezone.utc)
        self.total_queries = 0
        self.total_tokens = 0

        # Logging
        self.ai_logger = AILogger(
            db_path="data/aria_v3_audit.db",
            enabled=True
        )

        # System prompt (v3.0 with dynamic context)
        self.system_prompt = get_system_prompt(version="3.0")

        logger.info(
            "ARIAv3 initialized: session=%s, preferred=%s, rag=%s, streaming=%s, cot=%s",
            self.session_id,
            preferred_provider or "auto",
            enable_rag,
            enable_streaming,
            enable_cot
        )

    def _generate_session_id(self) -> str:
        """Generate unique session ID."""
        timestamp = int(time.time() * 1000)
        return f"aria-v3-{timestamp}"

    def register_tool(self, tool: Any):
        """
        Register a tool for ARIA to use.

        Args:
            tool: Tool instance with name, description, get_parameters_schema(), execute()
        """
        self.tools[tool.name] = tool

        # Add to tool schemas
        tool_schema = {
            "type": "function",
            "function": {
                "name": tool.name,
                "description": tool.description,
                "parameters": tool.get_parameters_schema()
            }
        }
        self.tool_schemas.append(tool_schema)
        logger.debug("Registered tool: %s", tool.name)

    def chat(self, message: str, use_tools: bool = False) -> str:
        """
        Send a message and get a response.

        Args:
            message: User's message
            use_tools: Whether to allow tool calling

        Returns:
            ARIA's response as a string
        """
        self.total_queries += 1
        t0 = time.time()

        try:
            # Build messages with context
            messages = self._build_message_context(message)

            # Log query
            self.ai_logger.log_query(message, session_id=self.session_id)

            # Call provider
            response, provider_name = self.provider_manager.chat_with_fallback(
                messages,
                tools=self.tool_schemas if use_tools and self.tool_schemas else None
            )

            # Track tokens and latency
            self.total_tokens += response.tokens_used
            latency_ms = (time.time() - t0) * 1000

            # Log response
            self.ai_logger.log_response(
                response.content[:500],
                tokens=response.tokens_used,
                latency_ms=latency_ms,
                session_id=self.session_id,
                provider=provider_name,
                model=response.model
            )

            # Handle tool calls
            if response.tool_calls and use_tools:
                final_response = self._handle_tool_calls(response, messages)
            else:
                final_response = response.content

            # Store in history
            self.conversation_history.append({"role": "user", "content": message})
            self.conversation_history.append({"role": "assistant", "content": final_response})

            logger.info(
                "Query completed: %s tokens, %.1f ms via %s",
                response.tokens_used, latency_ms, provider_name
            )

            return final_response

        except Exception as e:
            logger.exception("Chat error: %s", str(e))
            self.ai_logger.log_error(
                str(e)[:500],
                error_type="chat_error",
                session_id=self.session_id
            )
            return f"I encountered an error: {str(e)[:100]}. Please try again."

    def chat_stream(self, message: str) -> Generator[str, None, None]:
        """
        Send a message and stream the response.

        Yields chunks as they arrive. If provider doesn't support streaming natively,
        yields the full response at once.

        Args:
            message: User's message

        Yields:
            Response chunks as strings
        """
        self.total_queries += 1
        t0 = time.time()

        try:
            # Build messages with context
            messages = self._build_message_context(message)

            # Log query
            self.ai_logger.log_query(message, session_id=self.session_id)

            # For now, we'll get the full response and yield it
            # In production, integrate with provider's actual streaming if available
            response, provider_name = self.provider_manager.chat_with_fallback(messages)

            self.total_tokens += response.tokens_used
            latency_ms = (time.time() - t0) * 1000

            # If chain-of-thought enabled, show reasoning first
            if self.enable_cot and response.raw:
                reasoning = self._extract_reasoning(response.raw)
                if reasoning:
                    yield f"\n[Thinking] {reasoning}\n\n"

            # Yield response in chunks (simulated streaming)
            content = response.content
            chunk_size = 50
            for i in range(0, len(content), chunk_size):
                yield content[i:i + chunk_size]

            # Log response
            self.ai_logger.log_response(
                content[:500],
                tokens=response.tokens_used,
                latency_ms=latency_ms,
                session_id=self.session_id,
                provider=provider_name,
                model=response.model
            )

            # Store in history
            self.conversation_history.append({"role": "user", "content": message})
            self.conversation_history.append({"role": "assistant", "content": content})

        except Exception as e:
            logger.exception("Stream error: %s", str(e))
            self.ai_logger.log_error(
                str(e)[:500],
                error_type="stream_error",
                session_id=self.session_id
            )
            yield f"I encountered an error: {str(e)[:100]}"

    def chat_with_tools(self, message: str) -> str:
        """
        Send a message with tool calling support.

        ARIA can call registered tools to answer your question.

        Args:
            message: User's message

        Returns:
            ARIA's response (may include tool results)
        """
        return self.chat(message, use_tools=True)

    def _build_message_context(self, user_message: str) -> List[Dict[str, str]]:
        """
        Build message context with RAG and conversation history.

        Args:
            user_message: Current user message

        Returns:
            List of messages ready for LLM
        """
        messages = []

        # System prompt with context
        system_content = self.system_prompt
        if self.enable_rag and self.memory_retrieval:
            # Retrieve relevant context
            rag_context = self.memory_retrieval.get_context(user_message, max_items=5)
            if rag_context:
                system_content += "\n\n[Relevant Context from Memory]\n"
                for item in rag_context:
                    system_content += f"- {item}\n"

        messages.append({
            "role": "system",
            "content": system_content
        })

        # Add conversation history (last 10 messages for context)
        for msg in self.conversation_history[-20:]:
            messages.append(msg)

        # Add current message
        messages.append({
            "role": "user",
            "content": user_message
        })

        return messages

    def _handle_tool_calls(self,
                           response: LLMResponse,
                           messages: List[Dict[str, str]]) -> str:
        """
        Handle tool calls in response.

        Args:
            response: LLMResponse with tool_calls
            messages: Original message context

        Returns:
            Final response after tool execution
        """
        if not response.tool_calls:
            return response.content

        # Execute tools
        tool_results = []
        for tool_call in response.tool_calls:
            tool_name = tool_call.get("name")
            tool_args = tool_call.get("arguments", {})

            try:
                if tool_name not in self.tools:
                    result = {"error": f"Tool '{tool_name}' not found"}
                else:
                    tool = self.tools[tool_name]
                    logger.debug("Executing tool: %s with args %s", tool_name, tool_args)
                    result = tool.execute(**tool_args)
                    self.ai_logger.log_tool_call(
                        tool_name,
                        params=tool_args,
                        result=result,
                        session_id=self.session_id
                    )

                tool_results.append({
                    "tool": tool_name,
                    "result": result
                })

            except Exception as e:
                logger.exception("Tool execution failed: %s", tool_name)
                tool_results.append({
                    "tool": tool_name,
                    "result": {"error": str(e)[:200]}
                })

        # Get final response with tool results
        messages_with_results = messages + [
            {"role": "assistant", "content": response.content},
            {
                "role": "tool",
                "content": json.dumps(tool_results)
            }
        ]

        final_response, _ = self.provider_manager.chat_with_fallback(messages_with_results)
        return final_response.content

    def _extract_reasoning(self, raw_response: Any) -> Optional[str]:
        """
        Extract chain-of-thought reasoning from raw response.

        Args:
            raw_response: Raw provider response

        Returns:
            Reasoning text if available, None otherwise
        """
        if not raw_response:
            return None

        # Check for reasoning tags in response
        if isinstance(raw_response, dict):
            choices = raw_response.get("choices", [])
            if choices:
                message = choices[0].get("message", {})
                content = message.get("content", "")

                # Look for <thinking> or similar tags
                if "<thinking>" in content:
                    start = content.find("<thinking>") + 10
                    end = content.find("</thinking>")
                    if end > start:
                        return content[start:end].strip()

        return None

    def reset_conversation(self):
        """Reset conversation history."""
        self.conversation_history = []
        logger.info("Conversation history reset for session %s", self.session_id)

    def get_stats(self) -> Dict[str, Any]:
        """Get session statistics."""
        provider_stats = self.provider_manager.get_stats()
        return {
            "session_id": self.session_id,
            "created_at": self.created_at.isoformat(),
            "total_queries": self.total_queries,
            "total_tokens": self.total_tokens,
            "conversation_length": len(self.conversation_history),
            "tools_registered": len(self.tools),
            "providers": provider_stats.get("providers", {}),
        }

    def export_session(self, filepath: str):
        """
        Export session to JSON file.

        Args:
            filepath: Path to save session
        """
        session_data = {
            "session_id": self.session_id,
            "created_at": self.created_at.isoformat(),
            "stats": self.get_stats(),
            "conversation": self.conversation_history,
            "provider_manager_log": self.provider_manager.get_request_log(),
        }

        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(session_data, f, indent=2)

        logger.info("Session exported to %s", filepath)

    def get_provider_info(self) -> Dict[str, Any]:
        """Get information about all providers."""
        available = self.provider_manager.get_available_providers()
        return {
            "available": available,
            "preferred": self.provider_manager.preferred_provider,
            "providers": {
                name: self.provider_manager.get_provider_info(name)
                for name in self.provider_manager.fallback_chain
            }
        }


def create_aria_v3(preferred_provider: Optional[str] = None) -> ARIAv3:
    """
    Convenience function to create ARIAv3 instance.

    Args:
        preferred_provider: Optional preferred LLM provider

    Returns:
        ARIAv3 instance
    """
    return ARIAv3(preferred_provider=preferred_provider)


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)

    print("Testing ARIA v3.0")
    print("=" * 60)

    aria = create_aria_v3()

    # Test 1: Simple chat
    print("\nTest 1: Simple query")
    response = aria.chat("What is machine learning?")
    print(f"ARIA: {response}\n")

    # Test 2: Streaming
    print("Test 2: Streaming response")
    for chunk in aria.chat_stream("Tell me about neural networks"):
        print(chunk, end="", flush=True)
    print("\n")

    # Test 3: Stats
    print("Test 3: Statistics")
    stats = aria.get_stats()
    print(json.dumps(stats, indent=2))

    print("\nAll tests completed!")
