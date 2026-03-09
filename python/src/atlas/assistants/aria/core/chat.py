"""
ARIA Chat Engine - V2.0 REFINED

Enhanced with:
- Professional system prompt v2.0
- Parameter validation
- Robust error handling
- Tool calling with Ollama

Based on patterns from Claude Code, Cursor, and AI tool analysis
"""

import json
import logging
import ollama
from typing import Dict, List, Any, Optional
from pathlib import Path
from datetime import datetime, timezone

# Import validation and system prompt v2
from .validation import validate_tool_params, ValidationError
from .system_prompt import get_system_prompt

logger = logging.getLogger("atlas.aria")


class ARIA:
    """
    ARIA (Atlas Reasoning & Intelligence Assistant)
    
    Enhanced with:
    - Professional system prompt (v2.0)
    - Parameter validation before tool execution
    - Robust error handling with user-friendly messages
    - Tool calling support with Ollama
    """
    
    def __init__(self, 
                 model: str = "llama3.1:8b",
                 host: str = "http://localhost:11434",
                 temperature: float = 0.7):
        """
        Initialize ARIA with Ollama backend
        
        Args:
            model: Ollama model name (default: llama3.1:8b)
            host: Ollama server URL
            temperature: LLM temperature (0.0-1.0)
        """
        self.model = model
        self.host = host
        self.temperature = temperature
        self.backend = "ollama"
        
        # Conversation history
        self.history: List[Dict[str, str]] = []
        
        # Tool registry
        self.tools: Dict[str, Any] = {}
        self.tool_schemas: List[Dict] = []
        
        # System prompt v2.0
        self.system_prompt = get_system_prompt(version="2.0")
        
        # Version
        self.__version__ = "2.6.0"
        
        # Statistics
        self.stats = {
            "total_queries": 0,
            "successful_queries": 0,
            "failed_queries": 0,
            "tools_called": 0,
            "validation_errors": 0
        }

        # Structured tool-call audit trail
        self.tool_event_log_path = Path("outputs") / "runs" / "aria_tool_calls.jsonl"
        self.tool_event_log_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Verify Ollama connection
        self._verify_connection()
        
        # Print welcome banner
        self.print_banner()

    @staticmethod
    def _safe_print(message: str) -> None:
        """Print safely across Windows console encodings."""
        try:
            print(message)
        except UnicodeEncodeError:
            fallback = message.encode("ascii", errors="replace").decode("ascii")
            print(fallback)
        except Exception:
            # Logging should never break runtime behavior.
            try:
                print(str(message))
            except Exception:
                pass

    def print_banner(self):
        """Print startup banner."""
        banner = (
            "\n"
            + "=" * 60
            + "\nARIA - Atlas Reasoning & Intelligence Assistant\n"
            + "v5.0 - Autonomous Edition\n"
            + "System: 100% Local (no commercial APIs)\n"
            + f"Model: {self.model}\n"
            + "Status: Ready\n"
            + "=" * 60
        )
        self._safe_print(banner)
    
    def _verify_connection(self):
        """Verify connection to Ollama"""
        try:
            ollama.list()
        except Exception as e:
            raise ConnectionError(
                f"Failed to connect to Ollama at {self.host}. "
                f"Make sure Ollama is running.\nError: {e}"
            )

        self._safe_print(f"✅ Connected to Ollama ({self.host})")
        self._safe_print(f"📦 Using model: {self.model}")
    
    def register_tool(self, tool):
        """
        Register a tool for ARIA to use
        
        Args:
            tool: Tool instance with name, description, and execute method
        """
        self.tools[tool.name] = tool
        
        # Add tool schema for Ollama function calling
        tool_schema = {
            "type": "function",
            "function": {
                "name": tool.name,
                "description": tool.description,
                "parameters": tool.get_parameters_schema()
            }
        }
        self.tool_schemas.append(tool_schema)
        
        self._safe_print(f"🔧 Registered tool: {tool.name}")
    
    def ask(self, 
            user_message: str,
            max_iterations: int = 5) -> str:
        """
        Ask ARIA a question
        
        Supports multi-step tool calling:
        1. User asks question
        2. ARIA decides if tools needed
        3. ARIA calls tools (with validation)
        4. ARIA synthesizes response
        
        Args:
            user_message: User's question
            max_iterations: Max tool calling iterations
        
        Returns:
            ARIA's response
        """
        self.stats["total_queries"] += 1
        
        try:
            # Add user message to history
            self.history.append({
                "role": "user",
                "content": user_message
            })

            # Check for self-description commands (Fast Path)
            triggers = ["who are you", "what are you", "describe yourself", "/intro", "/info"]
            if any(trigger in user_message.lower() for trigger in triggers):
                description = (
                    "🤖 **I am ARIA (Atlas Reasoning & Intelligence Assistant).**\n\n"
                    "I am a refined, 100% local AI designed to be your autonomous co-pilot. "
                    "Unlike standard chatbots, I run entirely on your machine using Ollama, ensuring total privacy.\n\n"
                    "**My Key Capabilities:**\n"
                    "- 🧠 **Reasoning:** I use advanced models (Llama 3, Deepseek) to solve complex problems.\n"
                    "- 🛠️ **Tools:** I can access your files, search the web, and manage your schedule (ClickUp/Notion).\n"
                    "- 👁️ **Vision:** I can see and analyze images you share.\n"
                    "- 🗣️ **Voice:** I can speak and listen via my Voice Terminal.\n"
                    "- 🔌 **Integration:** I connect with WhatsApp, Discord, and your local apps.\n\n"
                    "I am built to be precise, helpful, and secure. How can I assist you today?"
                )
                
                # Add to history
                self.history.append({
                    "role": "assistant",
                    "content": description
                })
                
                return description
            
            # Prepare messages for Ollama
            messages = [
                {"role": "system", "content": self.system_prompt},
                *self.history
            ]
            
            # Multi-step reasoning with tools
            iterations = 0
            while iterations < max_iterations:
                iterations += 1
                
                # Call Ollama with tool support
                response = ollama.chat(
                    model=self.model,
                    messages=messages,
                    tools=self.tool_schemas if self.tool_schemas else None,
                    options={
                        "temperature": self.temperature
                    }
                )
                
                assistant_message = response['message']
                
                # Check if ARIA wants to call tools
                if 'tool_calls' in assistant_message and assistant_message['tool_calls']:
                    # Execute tools
                    tool_results = self._execute_tools(assistant_message['tool_calls'])
                    
                    # Add assistant's tool call to history
                    messages.append(assistant_message)
                    
                    # Add tool results to history
                    for tool_result in tool_results:
                        messages.append({
                            "role": "tool",
                            "content": json.dumps(tool_result)
                        })
                    
                    # Continue loop - ARIA will synthesize response
                    continue
                
                else:
                    # ARIA has final response
                    final_response = assistant_message.get('content', '')
                    
                    # Add to history
                    self.history.append({
                        "role": "assistant",
                        "content": final_response
                    })
                    
                    self.stats["successful_queries"] += 1
                    return final_response
            
            # Max iterations reached
            return "I apologize, but I'm having trouble completing this request. Could you try rephrasing or breaking it into smaller questions?"
        
        except Exception as e:
            self.stats["failed_queries"] += 1
            return self._handle_error(e)
    
    def _execute_tools(self, tool_calls: List[Dict]) -> List[Dict]:
        """
        Execute tool calls with validation
        
        Args:
            tool_calls: List of tool call dictionaries from Ollama
        
        Returns:
            List of tool result dictionaries
        """
        results = []
        
        for tool_call in tool_calls:
            function = tool_call.get('function', {})
            tool_name = function.get('name')
            tool_params = function.get('arguments', {})
            
            # Parse arguments if string
            if isinstance(tool_params, str):
                try:
                    tool_params = json.loads(tool_params)
                except json.JSONDecodeError:
                    tool_params = {}
            
            try:
                # Validate parameters
                validated_params = validate_tool_params(tool_name, tool_params)
                
                # Get tool
                tool = self.tools.get(tool_name)
                
                if not tool:
                    result = {
                        "success": False,
                        "error": f"Tool '{tool_name}' not found"
                    }
                else:
                    # Execute tool with validated params
                    self._safe_print(f"🔧 Executing: {tool_name}({validated_params})")
                    result = tool.execute(**validated_params)
                    self.stats["tools_called"] += 1
            
            except ValidationError as e:
                # Parameter validation failed
                self.stats["validation_errors"] += 1
                result = {
                    "success": False,
                    "error": str(e),
                    "error_type": "validation"
                }
            
            except Exception as e:
                # Tool execution failed
                result = {
                    "success": False,
                    "error": str(e),
                    "error_type": "execution"
                }

            self._log_tool_event(
                tool_name=tool_name or "unknown",
                params=tool_params,
                result=result,
            )

            results.append({
                "tool": tool_name,
                "result": result
            })

        return results

    def _log_tool_event(self, tool_name: str, params: Dict[str, Any], result: Dict[str, Any]) -> None:
        """Append a structured JSONL record for each tool call."""
        record = {
            "timestamp_utc": datetime.now(timezone.utc).isoformat(),
            "tool_name": tool_name,
            "params": params,
            "result": result,
        }
        try:
            with self.tool_event_log_path.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(record, ensure_ascii=False) + "\n")
        except Exception as exc:
            logger.debug("Failed to write tool event log: %s", exc)
    
    def _handle_error(self, error: Exception) -> str:
        """
        Handle errors with user-friendly messages
        
        Args:
            error: Exception that occurred
        
        Returns:
            User-friendly error message
        """
        error_type = type(error).__name__
        error_msg = str(error)
        
        # Specific error handlers
        if isinstance(error, ConnectionError):
            return (
                "I'm having trouble connecting to my language model. "
                "Please make sure Ollama is running and try again."
            )
        
        elif isinstance(error, ValidationError):
            return f"I need some clarification: {error_msg}"
        
        elif "timeout" in error_msg.lower():
            return (
                "This request is taking longer than expected. "
                "Could you try:\n"
                "1. Simplifying the query\n"
                "2. Breaking it into smaller questions\n"
                "3. Trying again in a moment"
            )
        
        else:
            # Generic error
            return (
                f"I encountered an unexpected issue: {error_msg}\n\n"
                "Could you try rephrasing your question or asking something else?"
            )
    
    def reset(self):
        """Reset conversation history"""
        self.history = []
        self._safe_print("🔄 Conversation history cleared")
    
    def get_stats(self) -> Dict:
        """Get usage statistics"""
        return {
            **self.stats,
            "success_rate": (
                self.stats["successful_queries"] / self.stats["total_queries"]
                if self.stats["total_queries"] > 0 else 0
            )
        }
    
    def export_conversation(self, filepath: str):
        """
        Export conversation history to file
        
        Args:
            filepath: Path to save conversation
        """
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump({
                "model": self.model,
                "backend": self.backend,
                "history": self.history,
                "stats": self.get_stats()
            }, f, indent=2)
        
        self._safe_print(f"💾 Conversation exported to {filepath}")


# Convenience function
def create_aria(model: str = "llama3.1:8b") -> ARIA:
    """
    Create ARIA instance with default settings
    
    Args:
        model: Ollama model to use
    
    Returns:
        ARIA instance
    """
    return ARIA(model=model)


if __name__ == "__main__":
    # Quick test
    print("🧪 Testing ARIA v2.0 (Refined Edition)")
    print("=" * 60)
    
    try:
        # Create ARIA
        aria = create_aria()
        
        # Test 1: Simple query
        print("\nTest 1: Simple question")
        print("-" * 60)
        response = aria.ask("Hello! Who are you?")
        print(f"ARIA: {response}\n")
        
        # Test 2: Capabilities
        print("Test 2: What can you do?")
        print("-" * 60)
        response = aria.ask("What can you help me with?")
        print(f"ARIA: {response}\n")
        
        # Show stats
        print("=" * 60)
        print("📊 Statistics:")
        stats = aria.get_stats()
        for key, value in stats.items():
            print(f"  {key}: {value}")
        
        print("\n✅ ARIA v2.0 is working!")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
