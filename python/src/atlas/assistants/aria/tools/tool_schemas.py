"""
ARIA Tool Schemas

Central registry of tool parameter schemas for validation
Used by validation.py to automatically validate tool parameters
"""

from typing import Dict, Any


# Tool parameter schemas following JSON Schema standard
TOOL_SCHEMAS: Dict[str, Dict[str, Any]] = {
    "get_data": {
        "symbol": {
            "type": "symbol",
            "required": True,
            "description": "Asset ticker symbol (stock, crypto, forex)",
            "example": "AAPL",
            "pattern": r"^[A-Z0-9\-\.=]+$",
            "max_length": 20
        },
        "start_date": {
            "type": "date",
            "required": True,
            "description": "Start date for data retrieval",
            "example": "2024-01-01",
            "format": "YYYY-MM-DD"
        },
        "end_date": {
            "type": "date",
            "required": True,
            "description": "End date for data retrieval",
            "example": "2024-12-31",
            "format": "YYYY-MM-DD"
        },
        "interval": {
            "type": "string",
            "required": False,
            "default": "1d",
            "enum": ["1m", "5m", "15m", "30m", "1h", "1d", "1wk", "1mo"],
            "description": "Data interval/timeframe",
            "example": "1d"
        }
    },
    
    "web_search": {
        "query": {
            "type": "string",
            "required": True,
            "min_length": 1,
            "max_length": 500,
            "description": "Search query string",
            "example": "Tesla latest news"
        },
        "max_results": {
            "type": "integer",
            "required": False,
            "default": 5,
            "min": 1,
            "max": 20,
            "description": "Maximum number of search results",
            "example": 5
        },
        "time_range": {
            "type": "string",
            "required": False,
            "enum": ["day", "week", "month", "year", "all"],
            "default": "all",
            "description": "Time range for search results",
            "example": "week"
        }
    },
    
    "create_file": {
        "filename": {
            "type": "string",
            "required": True,
            "min_length": 1,
            "max_length": 255,
            "pattern": r"^[a-zA-Z0-9_\-\.]+$",
            "description": "Name of file to create (with extension)",
            "example": "report.md"
        },
        "content": {
            "type": "string",
            "required": True,
            "min_length": 1,
            "description": "Content to write to file",
            "example": "# Report\n\nThis is the content."
        },
        "directory": {
            "type": "string",
            "required": False,
            "default": "outputs",
            "description": "Subdirectory to save file in",
            "example": "reports"
        },
        "overwrite": {
            "type": "boolean",
            "required": False,
            "default": False,
            "description": "Whether to overwrite if file exists",
            "example": False
        }
    },
    
    "execute_code": {
        "code": {
            "type": "string",
            "required": True,
            "min_length": 1,
            "description": "Python code to execute",
            "example": "print('Hello, World!')"
        },
        "description": {
            "type": "string",
            "required": False,
            "max_length": 200,
            "description": "Brief description of what the code does",
            "example": "Calculate correlation between two assets"
        },
        "timeout": {
            "type": "integer",
            "required": False,
            "default": 30,
            "min": 1,
            "max": 300,
            "description": "Execution timeout in seconds",
            "example": 30
        }
    },
    
    "read_file": {
        "filepath": {
            "type": "string",
            "required": True,
            "min_length": 1,
            "description": "Path to file to read",
            "example": "data/report.txt"
        },
        "encoding": {
            "type": "string",
            "required": False,
            "default": "utf-8",
            "enum": ["utf-8", "ascii", "latin-1"],
            "description": "File encoding",
            "example": "utf-8"
        },
        "max_lines": {
            "type": "integer",
            "required": False,
            "min": 1,
            "description": "Maximum lines to read (for large files)",
            "example": 1000
        }
    },
    
    "calculate_indicator": {
        "indicator": {
            "type": "string",
            "required": True,
            "enum": ["rsi", "macd", "bollinger", "sma", "ema", "atr", "stochastic"],
            "description": "Technical indicator to calculate",
            "example": "rsi"
        },
        "symbol": {
            "type": "symbol",
            "required": True,
            "description": "Asset ticker symbol",
            "example": "AAPL"
        },
        "period": {
            "type": "integer",
            "required": False,
            "default": 14,
            "min": 1,
            "max": 200,
            "description": "Period for indicator calculation",
            "example": 14
        },
        "start_date": {
            "type": "date",
            "required": True,
            "description": "Start date for data",
            "example": "2024-01-01"
        },
        "end_date": {
            "type": "date",
            "required": True,
            "description": "End date for data",
            "example": "2024-12-31"
        }
    },
    
    "analyze_sentiment": {
        "text": {
            "type": "string",
            "required": True,
            "min_length": 1,
            "max_length": 10000,
            "description": "Text to analyze for sentiment",
            "example": "The market is looking bullish today"
        },
        "language": {
            "type": "string",
            "required": False,
            "default": "en",
            "enum": ["en", "es", "fr", "de", "zh"],
            "description": "Language of text",
            "example": "en"
        }
    },
    
    "compare_assets": {
        "symbols": {
            "type": "array",
            "required": True,
            "min_items": 2,
            "max_items": 10,
            "item_type": "symbol",
            "description": "List of asset symbols to compare",
            "example": ["AAPL", "MSFT", "GOOGL"]
        },
        "start_date": {
            "type": "date",
            "required": True,
            "description": "Start date for comparison",
            "example": "2024-01-01"
        },
        "end_date": {
            "type": "date",
            "required": True,
            "description": "End date for comparison",
            "example": "2024-12-31"
        },
        "metrics": {
            "type": "array",
            "required": False,
            "default": ["return", "volatility", "sharpe"],
            "item_type": "string",
            "enum_items": ["return", "volatility", "sharpe", "correlation", "beta"],
            "description": "Metrics to calculate for comparison",
            "example": ["return", "volatility", "sharpe"]
        }
    },
    
    "backtest_strategy": {
        "strategy_name": {
            "type": "string",
            "required": True,
            "description": "Name of strategy to backtest",
            "example": "momentum_crossover"
        },
        "symbols": {
            "type": "array",
            "required": True,
            "min_items": 1,
            "item_type": "symbol",
            "description": "Assets to backtest on",
            "example": ["AAPL", "MSFT"]
        },
        "start_date": {
            "type": "date",
            "required": True,
            "description": "Backtest start date",
            "example": "2020-01-01"
        },
        "end_date": {
            "type": "date",
            "required": True,
            "description": "Backtest end date",
            "example": "2024-12-31"
        },
        "initial_capital": {
            "type": "float",
            "required": False,
            "default": 100000.0,
            "min": 1000.0,
            "description": "Initial capital for backtest",
            "example": 100000.0
        },
        "parameters": {
            "type": "object",
            "required": False,
            "description": "Strategy-specific parameters",
            "example": {"fast_period": 12, "slow_period": 26}
        }
    }
}


def get_tool_schema(tool_name: str) -> Dict[str, Any]:
    """
    Get parameter schema for a tool
    
    Args:
        tool_name: Name of the tool
    
    Returns:
        Parameter schema dict, or empty dict if not found
    """
    return TOOL_SCHEMAS.get(tool_name, {})


def get_all_tool_names() -> list:
    """
    Get list of all registered tools
    
    Returns:
        List of tool names
    """
    return list(TOOL_SCHEMAS.keys())


def get_required_params(tool_name: str) -> list:
    """
    Get list of required parameters for a tool
    
    Args:
        tool_name: Name of the tool
    
    Returns:
        List of required parameter names
    """
    schema = get_tool_schema(tool_name)
    return [
        param_name
        for param_name, param_spec in schema.items()
        if param_spec.get("required", False)
    ]


def get_optional_params(tool_name: str) -> list:
    """
    Get list of optional parameters for a tool
    
    Args:
        tool_name: Name of the tool
    
    Returns:
        List of optional parameter names
    """
    schema = get_tool_schema(tool_name)
    return [
        param_name
        for param_name, param_spec in schema.items()
        if not param_spec.get("required", False)
    ]


def get_param_info(tool_name: str, param_name: str) -> Dict[str, Any]:
    """
    Get detailed information about a parameter
    
    Args:
        tool_name: Name of the tool
        param_name: Name of the parameter
    
    Returns:
        Parameter spec dict, or empty dict if not found
    """
    schema = get_tool_schema(tool_name)
    return schema.get(param_name, {})


if __name__ == "__main__":
    # Tests
    print("Tool Schemas Registry")
    print("=" * 60)
    
    print(f"\nTotal tools registered: {len(TOOL_SCHEMAS)}")
    print("\nRegistered tools:")
    for i, tool_name in enumerate(get_all_tool_names(), 1):
        required = get_required_params(tool_name)
        optional = get_optional_params(tool_name)
        print(f"{i}. {tool_name}")
        print(f"   Required: {', '.join(required)}")
        print(f"   Optional: {', '.join(optional)}")
    
    print("\n" + "=" * 60)
    print("\nExample: get_data schema")
    print("-" * 60)
    schema = get_tool_schema("get_data")
    for param_name, param_spec in schema.items():
        required = "REQUIRED" if param_spec.get("required") else "optional"
        print(f"\n{param_name} ({required}):")
        print(f"  Type: {param_spec.get('type')}")
        print(f"  Description: {param_spec.get('description')}")
        print(f"  Example: {param_spec.get('example')}")
    
    print("\n" + "=" * 60)
    print("Schema registry ready!")
