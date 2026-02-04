"""
Base Tool System for ARIA

Based on patterns from:
- Cursor Agent
- Claude Code
- v0 (Vercel)

Copyright (c) 2026 M&C. All rights reserved.
"""
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional
from pydantic import BaseModel, Field


class ToolParameter(BaseModel):
    """Tool parameter definition"""
    name: str
    type: str
    description: str
    required: bool = True
    default: Optional[Any] = None


class Tool(ABC):
    """
    Base class for all ARIA tools
    
    All tools must inherit from this class and implement:
    - name: Tool name
    - description: What the tool does
    - parameters: List of parameters
    - execute: The actual tool logic
    
    Example:
        >>> class GetDataTool(Tool):
        >>>     def __init__(self):
        >>>         super().__init__(
        >>>             name="get_data",
        >>>             description="Get historical market data"
        >>>         )
        >>>         self.add_parameter("symbol", "string", "Ticker symbol")
        >>>     
        >>>     def execute(self, symbol):
        >>>         # Tool logic here
        >>>         return data
    """
    
    def __init__(
        self,
        name: str,
        description: str,
        category: str = "general"
    ):
        """
        Initialize tool
        
        Args:
            name: Tool name (e.g. "get_data")
            description: What the tool does
            category: Tool category (e.g. "data", "analysis", "web")
        """
        self.name = name
        self.description = description
        self.category = category
        self.parameters: Dict[str, ToolParameter] = {}
    
    def add_parameter(
        self,
        name: str,
        param_type: str,
        description: str,
        required: bool = True,
        default: Any = None
    ):
        """
        Add a parameter to the tool
        
        Args:
            name: Parameter name
            param_type: Type (string, number, boolean, array, object)
            description: Parameter description
            required: If parameter is required
            default: Default value if not required
        """
        self.parameters[name] = ToolParameter(
            name=name,
            type=param_type,
            description=description,
            required=required,
            default=default
        )
    
    @abstractmethod
    def execute(self, **kwargs) -> Any:
        """
        Execute the tool
        
        This must be implemented by all tools
        
        Args:
            **kwargs: Tool parameters
            
        Returns:
            Tool result (any type)
        """
        pass
    
    def to_anthropic_format(self) -> Dict:
        """
        Convert tool to Anthropic function calling format
        
        Returns:
            Tool definition in Anthropic format
        """
        properties = {}
        required = []
        
        for param_name, param in self.parameters.items():
            properties[param_name] = {
                "type": param.type,
                "description": param.description
            }
            if param.required:
                required.append(param_name)
        
        return {
            "name": self.name,
            "description": self.description,
            "input_schema": {
                "type": "object",
                "properties": properties,
                "required": required
            }
        }
    
    def validate_parameters(self, **kwargs) -> bool:
        """
        Validate that required parameters are provided
        
        Args:
            **kwargs: Parameters to validate
            
        Returns:
            True if valid, raises ValueError if not
        """
        for param_name, param in self.parameters.items():
            if param.required and param_name not in kwargs:
                raise ValueError(
                    f"Missing required parameter: {param_name}"
                )
        return True
    
    def __repr__(self):
        return f"Tool({self.name}, category={self.category})"
    
    def __str__(self):
        params = ", ".join(self.parameters.keys())
        return f"{self.name}({params}): {self.description}"


# Example tool for testing
class EchoTool(Tool):
    """Simple echo tool for testing"""
    
    def __init__(self):
        super().__init__(
            name="echo",
            description="Echo back the input message",
            category="testing"
        )
        self.add_parameter(
            "message",
            "string",
            "Message to echo back"
        )
    
    def execute(self, message: str) -> str:
        """Echo the message"""
        return f"Echo: {message}"


# Test
if __name__ == "__main__":
    print("🧪 Testing Tool system...\n")
    
    # Create echo tool
    echo = EchoTool()
    
    print(f"Tool: {echo}")
    print(f"Anthropic format: {echo.to_anthropic_format()}\n")
    
    # Test execution
    result = echo.execute(message="Hello, ARIA!")
    print(f"Result: {result}\n")
    
    # Test validation
    try:
        echo.validate_parameters(message="test")
        print("✅ Validation passed")
    except ValueError as e:
        print(f"❌ Validation failed: {e}")
    
    print("\n✅ Tool system working!")
