"""
ARIA Error Handler

Centralized error handling with user-friendly messages
Based on professional AI tool patterns
"""

from typing import Optional, Dict, Any
from .validation import ValidationError


class ErrorHandler:
    """
    Handle errors with user-friendly messages and recovery suggestions
    
    Inspired by Claude Code and Cursor error handling patterns
    """
    
    # Error message templates
    ERROR_TEMPLATES = {
        "connection": {
            "message": "I'm having trouble connecting to {service}.",
            "suggestions": [
                "Make sure {service} is running",
                "Check your internet connection",
                "Verify the service URL is correct"
            ]
        },
        "validation": {
            "message": "I need some clarification about: {parameter}",
            "suggestions": [
                "Check the parameter format",
                "Refer to the examples provided",
                "Ask for help if unsure"
            ]
        },
        "timeout": {
            "message": "This request is taking longer than expected.",
            "suggestions": [
                "Try with a smaller date range",
                "Simplify the query",
                "Wait a moment and retry"
            ]
        },
        "not_found": {
            "message": "I couldn't find {resource}.",
            "suggestions": [
                "Verify the symbol/name is correct",
                "Check if the resource exists",
                "Try a different search term"
            ]
        },
        "rate_limit": {
            "message": "I've reached the rate limit for {service}.",
            "suggestions": [
                "Wait a few moments before retrying",
                "Use a different data source if available",
                "Reduce the frequency of requests"
            ]
        },
        "data_unavailable": {
            "message": "Data for {resource} is not available for {period}.",
            "suggestions": [
                "Try a different date range",
                "Check if the market was open",
                "Verify the symbol is correct"
            ]
        },
        "permission": {
            "message": "I don't have permission to access {resource}.",
            "suggestions": [
                "Check API credentials",
                "Verify subscription level",
                "Contact support if needed"
            ]
        },
        "tool_execution": {
            "message": "I encountered an error while {action}: {error}",
            "suggestions": [
                "Try an alternative approach",
                "Simplify the request",
                "Check if all parameters are correct"
            ]
        },
        "unknown": {
            "message": "I encountered an unexpected issue: {error}",
            "suggestions": [
                "Try rephrasing your question",
                "Break it into smaller questions",
                "Let me know if you need help"
            ]
        }
    }
    
    @classmethod
    def handle_error(cls, error: Exception, context: Optional[Dict[str, Any]] = None) -> str:
        """
        Convert exception to user-friendly message
        
        Args:
            error: Exception that occurred
            context: Additional context (service name, resource, etc.)
        
        Returns:
            User-friendly error message with suggestions
        """
        context = context or {}
        error_type = cls._classify_error(error)
        
        # Get template
        template = cls.ERROR_TEMPLATES.get(error_type, cls.ERROR_TEMPLATES["unknown"])
        
        # Format message
        message = template["message"].format(
            error=str(error),
            **context
        )
        
        # Add suggestions
        suggestions = "\n\n" + cls._format_suggestions(template["suggestions"], context)
        
        return message + suggestions
    
    @classmethod
    def _classify_error(cls, error: Exception) -> str:
        """
        Classify error type from exception
        
        Args:
            error: Exception to classify
        
        Returns:
            Error type string
        """
        error_msg = str(error).lower()
        error_type_name = type(error).__name__.lower()
        
        # Validation errors
        if isinstance(error, ValidationError):
            return "validation"
        
        # Connection errors
        if any(keyword in error_type_name for keyword in ["connection", "network", "socket"]):
            return "connection"
        
        # Timeout errors
        if "timeout" in error_msg or "timeout" in error_type_name:
            return "timeout"
        
        # Not found errors
        if any(keyword in error_msg for keyword in ["not found", "404", "does not exist"]):
            return "not_found"
        
        # Rate limit errors
        if any(keyword in error_msg for keyword in ["rate limit", "429", "too many requests"]):
            return "rate_limit"
        
        # Data unavailable
        if any(keyword in error_msg for keyword in ["no data", "unavailable", "empty"]):
            return "data_unavailable"
        
        # Permission errors
        if any(keyword in error_msg for keyword in ["permission", "401", "403", "unauthorized"]):
            return "permission"
        
        # Tool execution errors
        if "tool" in error_msg or "execution" in error_msg:
            return "tool_execution"
        
        # Default
        return "unknown"
    
    @classmethod
    def _format_suggestions(cls, suggestions: list, context: Dict) -> str:
        """
        Format suggestions list
        
        Args:
            suggestions: List of suggestion strings
            context: Context for formatting
        
        Returns:
            Formatted suggestions string
        """
        formatted = "Here are some suggestions:\n"
        for i, suggestion in enumerate(suggestions, 1):
            formatted_suggestion = suggestion.format(**context)
            formatted += f"{i}. {formatted_suggestion}\n"
        
        return formatted.rstrip()
    
    @classmethod
    def create_validation_error_message(cls, 
                                       parameter: str,
                                       message: str,
                                       expected_format: Optional[str] = None,
                                       example: Optional[str] = None) -> str:
        """
        Create detailed validation error message
        
        Args:
            parameter: Parameter name
            message: Error message
            expected_format: Expected format description
            example: Example value
        
        Returns:
            Formatted error message
        """
        msg = f"Invalid parameter '{parameter}': {message}"
        
        if expected_format:
            msg += f"\n\n**Expected format:** {expected_format}"
        
        if example:
            msg += f"\n**Example:** {example}"
        
        return msg
    
    @classmethod
    def create_tool_error_message(cls,
                                  tool_name: str,
                                  error: Exception,
                                  attempted_params: Dict) -> str:
        """
        Create tool execution error message
        
        Args:
            tool_name: Name of tool that failed
            error: Exception that occurred
            attempted_params: Parameters that were used
        
        Returns:
            Formatted error message
        """
        msg = f"I encountered an error while using the '{tool_name}' tool:\n\n"
        msg += f"**Error:** {str(error)}\n\n"
        msg += "**Parameters used:**\n"
        
        for key, value in attempted_params.items():
            msg += f"  • {key}: {value}\n"
        
        msg += "\nWould you like to:\n"
        msg += "1. Try with different parameters\n"
        msg += "2. Use an alternative approach\n"
        msg += "3. Get more information about this tool"
        
        return msg


def handle_connection_error(service: str, host: str = None) -> str:
    """
    Convenience function for connection errors
    
    Args:
        service: Service name (e.g., "Ollama", "Yahoo Finance")
        host: Optional host URL
    
    Returns:
        User-friendly error message
    """
    msg = f"I'm having trouble connecting to {service}."
    
    if host:
        msg += f"\n\n**Host:** {host}"
    
    msg += "\n\n**Suggestions:**\n"
    msg += f"1. Make sure {service} is running\n"
    msg += "2. Check your internet connection\n"
    msg += "3. Verify the service configuration\n"
    
    return msg


def handle_tool_not_found(tool_name: str) -> str:
    """
    Handle tool not found error
    
    Args:
        tool_name: Name of missing tool
    
    Returns:
        User-friendly error message
    """
    msg = f"I don't have access to the '{tool_name}' tool."
    msg += "\n\n**This could mean:**\n"
    msg += "1. The tool hasn't been registered yet\n"
    msg += "2. The tool name is misspelled\n"
    msg += "3. The tool is not available in this environment\n"
    msg += "\n**Available actions:**\n"
    msg += "• Ask what tools I have available\n"
    msg += "• Try a different approach\n"
    msg += "• Check the tool registry\n"
    
    return msg


def handle_data_error(symbol: str, date_range: str = None) -> str:
    """
    Handle data not available error
    
    Args:
        symbol: Asset symbol
        date_range: Optional date range
    
    Returns:
        User-friendly error message
    """
    msg = f"I couldn't find data for {symbol}"
    
    if date_range:
        msg += f" for the period {date_range}"
    
    msg += ".\n\n**This might be because:**\n"
    msg += "1. The symbol doesn't exist or is misspelled\n"
    msg += "2. Data is not available for that date range\n"
    msg += "3. The market was closed on those dates\n"
    msg += "4. The data source doesn't have this asset\n"
    msg += "\n**Try:**\n"
    msg += "• Verify the symbol is correct\n"
    msg += "• Check a different date range\n"
    msg += "• Use a different data source\n"
    
    return msg


# Convenience function for backward compatibility
def get_error_message(error: Exception, context: Dict = None) -> str:
    """
    Get user-friendly error message
    
    Args:
        error: Exception
        context: Additional context
    
    Returns:
        Formatted error message
    """
    return ErrorHandler.handle_error(error, context)


if __name__ == "__main__":
    # Tests
    print("Testing Error Handler...")
    print("=" * 60)
    
    # Test 1: Connection error
    print("\n1. Connection Error:")
    msg = handle_connection_error("Ollama", "http://localhost:11434")
    print(msg)
    
    # Test 2: Tool not found
    print("\n2. Tool Not Found:")
    msg = handle_tool_not_found("unknown_tool")
    print(msg)
    
    # Test 3: Data error
    print("\n3. Data Error:")
    msg = handle_data_error("INVALID", "2024-01-01 to 2024-12-31")
    print(msg)
    
    # Test 4: Validation error
    print("\n4. Validation Error:")
    from .validation import ValidationError
    try:
        raise ValidationError(
            parameter="symbol",
            message="Invalid format",
            expected_format="Stock ticker (e.g., AAPL)",
            example="AAPL"
        )
    except ValidationError as e:
        msg = ErrorHandler.handle_error(e, {"parameter": "symbol"})
        print(msg)
    
    print("\n" + "=" * 60)
    print("All tests completed!")
