"""
ARIA Tool Parameter Validation

Robust parameter validation inspired by professional AI tools
Based on analysis of Claude Code, Cursor, and other tools
"""

import re
from datetime import datetime
from typing import Any, Dict, List, Optional, Union
from enum import Enum


class ValidationError(Exception):
    """Custom exception for validation errors"""
    
    def __init__(self, parameter: str, message: str, expected_format: Optional[str] = None, 
                 example: Optional[str] = None):
        self.parameter = parameter
        self.message = message
        self.expected_format = expected_format
        self.example = example
        super().__init__(self.format_error())
    
    def format_error(self) -> str:
        """Format error message for user"""
        msg = f"Invalid parameter '{self.parameter}': {self.message}"
        
        if self.expected_format:
            msg += f"\n\nExpected format: {self.expected_format}"
        
        if self.example:
            msg += f"\nExample: {self.example}"
        
        return msg


class ParameterType(Enum):
    """Supported parameter types"""
    STRING = "string"
    INTEGER = "integer"
    FLOAT = "float"
    BOOLEAN = "boolean"
    DATE = "date"
    SYMBOL = "symbol"
    ARRAY = "array"
    OBJECT = "object"


class ParameterValidator:
    """
    Validates tool parameters before execution
    
    Inspired by patterns from Claude Code and Cursor:
    - Type checking
    - Range validation
    - Format validation
    - Required vs optional
    - Custom validators
    """
    
    def __init__(self):
        self.validators = {
            ParameterType.STRING: self._validate_string,
            ParameterType.INTEGER: self._validate_integer,
            ParameterType.FLOAT: self._validate_float,
            ParameterType.BOOLEAN: self._validate_boolean,
            ParameterType.DATE: self._validate_date,
            ParameterType.SYMBOL: self._validate_symbol,
            ParameterType.ARRAY: self._validate_array,
            ParameterType.OBJECT: self._validate_object
        }
    
    def validate(self, parameters: Dict[str, Any], schema: Dict) -> Dict[str, Any]:
        """
        Validate parameters against schema
        
        Args:
            parameters: Dict of parameter values
            schema: Dict defining parameter requirements
        
        Returns:
            Validated and potentially transformed parameters
        
        Raises:
            ValidationError: If validation fails
        """
        validated = {}
        
        # Check required parameters
        for param_name, param_spec in schema.items():
            is_required = param_spec.get('required', False)
            param_value = parameters.get(param_name)
            
            # Check if required parameter is missing
            if is_required and param_value is None:
                raise ValidationError(
                    parameter=param_name,
                    message="Required parameter is missing",
                    expected_format=param_spec.get('description', 'N/A'),
                    example=param_spec.get('example')
                )
            
            # Skip validation if optional and not provided
            if param_value is None and not is_required:
                # Use default if available
                if 'default' in param_spec:
                    validated[param_name] = param_spec['default']
                continue
            
            # Validate parameter
            param_type = param_spec.get('type')
            if param_type:
                validated[param_name] = self._validate_by_type(
                    param_name,
                    param_value,
                    param_type,
                    param_spec
                )
            else:
                validated[param_name] = param_value
        
        return validated
    
    def _validate_by_type(self, name: str, value: Any, param_type: str, 
                          spec: Dict) -> Any:
        """
        Validate parameter by type
        
        Args:
            name: Parameter name
            value: Parameter value
            param_type: Expected type
            spec: Full parameter spec
        
        Returns:
            Validated (and possibly transformed) value
        """
        try:
            type_enum = ParameterType(param_type)
            validator = self.validators.get(type_enum)
            
            if validator:
                return validator(name, value, spec)
            else:
                return value
        
        except ValueError:
            # Unknown type, return as-is
            return value
    
    def _validate_string(self, name: str, value: Any, spec: Dict) -> str:
        """Validate string parameter"""
        if not isinstance(value, str):
            try:
                value = str(value)
            except:
                raise ValidationError(
                    parameter=name,
                    message=f"Expected string, got {type(value).__name__}",
                    example=spec.get('example', '"example_string"')
                )
        
        # Check min/max length
        if 'min_length' in spec and len(value) < spec['min_length']:
            raise ValidationError(
                parameter=name,
                message=f"String too short (min: {spec['min_length']} characters)"
            )
        
        if 'max_length' in spec and len(value) > spec['max_length']:
            raise ValidationError(
                parameter=name,
                message=f"String too long (max: {spec['max_length']} characters)"
            )
        
        # Check pattern
        if 'pattern' in spec:
            if not re.match(spec['pattern'], value):
                raise ValidationError(
                    parameter=name,
                    message=f"String doesn't match required pattern",
                    expected_format=spec.get('pattern_description', spec['pattern']),
                    example=spec.get('example')
                )
        
        # Check enum values
        if 'enum' in spec:
            if value not in spec['enum']:
                raise ValidationError(
                    parameter=name,
                    message=f"Invalid value. Must be one of: {', '.join(spec['enum'])}",
                    example=spec['enum'][0]
                )
        
        return value
    
    def _validate_integer(self, name: str, value: Any, spec: Dict) -> int:
        """Validate integer parameter"""
        try:
            value = int(value)
        except (ValueError, TypeError):
            raise ValidationError(
                parameter=name,
                message=f"Expected integer, got {type(value).__name__}",
                example=spec.get('example', '42')
            )
        
        # Check min/max
        if 'min' in spec and value < spec['min']:
            raise ValidationError(
                parameter=name,
                message=f"Value too small (min: {spec['min']})"
            )
        
        if 'max' in spec and value > spec['max']:
            raise ValidationError(
                parameter=name,
                message=f"Value too large (max: {spec['max']})"
            )
        
        return value
    
    def _validate_float(self, name: str, value: Any, spec: Dict) -> float:
        """Validate float parameter"""
        try:
            value = float(value)
        except (ValueError, TypeError):
            raise ValidationError(
                parameter=name,
                message=f"Expected number, got {type(value).__name__}",
                example=spec.get('example', '3.14')
            )
        
        # Check min/max
        if 'min' in spec and value < spec['min']:
            raise ValidationError(
                parameter=name,
                message=f"Value too small (min: {spec['min']})"
            )
        
        if 'max' in spec and value > spec['max']:
            raise ValidationError(
                parameter=name,
                message=f"Value too large (max: {spec['max']})"
            )
        
        return value
    
    def _validate_boolean(self, name: str, value: Any, spec: Dict) -> bool:
        """Validate boolean parameter"""
        if isinstance(value, bool):
            return value
        
        if isinstance(value, str):
            value_lower = value.lower()
            if value_lower in ('true', 'yes', '1', 'on'):
                return True
            elif value_lower in ('false', 'no', '0', 'off'):
                return False
        
        raise ValidationError(
            parameter=name,
            message=f"Expected boolean, got {type(value).__name__}",
            example=spec.get('example', 'true or false')
        )
    
    def _validate_date(self, name: str, value: Any, spec: Dict) -> str:
        """
        Validate date parameter
        
        Accepts:
        - YYYY-MM-DD
        - datetime objects
        """
        if isinstance(value, datetime):
            return value.strftime('%Y-%m-%d')
        
        if isinstance(value, str):
            # Try to parse date
            date_formats = [
                '%Y-%m-%d',
                '%Y/%m/%d',
                '%d-%m-%Y',
                '%d/%m/%Y',
                '%m-%d-%Y',
                '%m/%d/%Y'
            ]
            
            for fmt in date_formats:
                try:
                    parsed_date = datetime.strptime(value, fmt)
                    return parsed_date.strftime('%Y-%m-%d')
                except ValueError:
                    continue
            
            raise ValidationError(
                parameter=name,
                message="Invalid date format",
                expected_format="YYYY-MM-DD",
                example=spec.get('example', '2024-01-15')
            )
        
        raise ValidationError(
            parameter=name,
            message=f"Expected date string, got {type(value).__name__}",
            expected_format="YYYY-MM-DD",
            example="2024-01-15"
        )
    
    def _validate_symbol(self, name: str, value: Any, spec: Dict) -> str:
        """
        Validate symbol/ticker parameter
        
        Accepts:
        - Stock tickers (AAPL, MSFT)
        - Crypto (BTC-USD, ETH-USD)
        - Forex (EURUSD=X)
        """
        if not isinstance(value, str):
            try:
                value = str(value)
            except:
                raise ValidationError(
                    parameter=name,
                    message=f"Expected symbol string, got {type(value).__name__}",
                    example=spec.get('example', 'AAPL')
                )
        
        value = value.upper().strip()
        
        # Basic validation
        if not value:
            raise ValidationError(
                parameter=name,
                message="Symbol cannot be empty",
                example="AAPL"
            )
        
        # Check length (most tickers are 1-5 characters)
        if len(value) > 20:
            raise ValidationError(
                parameter=name,
                message="Symbol too long",
                example="AAPL"
            )
        
        # Check for invalid characters (basic check)
        # Allow: letters, numbers, dash, dot, equals sign
        if not re.match(r'^[A-Z0-9\-\.=]+$', value):
            raise ValidationError(
                parameter=name,
                message="Symbol contains invalid characters",
                expected_format="Letters, numbers, dash, dot, equals only",
                example="AAPL or BTC-USD"
            )
        
        return value
    
    def _validate_array(self, name: str, value: Any, spec: Dict) -> List:
        """Validate array parameter"""
        if not isinstance(value, (list, tuple)):
            raise ValidationError(
                parameter=name,
                message=f"Expected array, got {type(value).__name__}",
                example=spec.get('example', '["item1", "item2"]')
            )
        
        # Check min/max length
        if 'min_items' in spec and len(value) < spec['min_items']:
            raise ValidationError(
                parameter=name,
                message=f"Array too short (min: {spec['min_items']} items)"
            )
        
        if 'max_items' in spec and len(value) > spec['max_items']:
            raise ValidationError(
                parameter=name,
                message=f"Array too long (max: {spec['max_items']} items)"
            )
        
        # Validate items if item_type specified
        if 'item_type' in spec:
            validated_items = []
            for i, item in enumerate(value):
                try:
                    validated_item = self._validate_by_type(
                        f"{name}[{i}]",
                        item,
                        spec['item_type'],
                        spec.get('item_spec', {})
                    )
                    validated_items.append(validated_item)
                except ValidationError as e:
                    raise ValidationError(
                        parameter=f"{name}[{i}]",
                        message=e.message
                    )
            return validated_items
        
        return list(value)
    
    def _validate_object(self, name: str, value: Any, spec: Dict) -> Dict:
        """Validate object parameter"""
        if not isinstance(value, dict):
            raise ValidationError(
                parameter=name,
                message=f"Expected object, got {type(value).__name__}",
                example=spec.get('example', '{"key": "value"}')
            )
        
        # Validate properties if schema provided
        if 'properties' in spec:
            return self.validate(value, spec['properties'])
        
        return value


# Tool-specific parameter schemas
TOOL_SCHEMAS = {
    "get_data": {
        "symbol": {
            "type": "symbol",
            "required": True,
            "description": "Asset ticker symbol",
            "example": "AAPL"
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
        },
        "interval": {
            "type": "string",
            "required": False,
            "default": "1d",
            "enum": ["1m", "5m", "15m", "30m", "1h", "1d", "1wk", "1mo"],
            "description": "Data interval",
            "example": "1d"
        }
    },
    "web_search": {
        "query": {
            "type": "string",
            "required": True,
            "min_length": 1,
            "max_length": 500,
            "description": "Search query",
            "example": "Tesla latest news"
        },
        "max_results": {
            "type": "integer",
            "required": False,
            "default": 5,
            "min": 1,
            "max": 20,
            "description": "Maximum number of results",
            "example": 5
        }
    },
    "create_file": {
        "filename": {
            "type": "string",
            "required": True,
            "min_length": 1,
            "max_length": 255,
            "description": "Name of file to create",
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
            "description": "Subdirectory to save in",
            "example": "reports"
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
            "description": "Brief description of code",
            "example": "Calculate correlation"
        }
    }
}


def validate_tool_params(tool_name: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
    """
    Convenience function to validate tool parameters
    
    Args:
        tool_name: Name of tool
        parameters: Dict of parameters to validate
    
    Returns:
        Validated parameters
    
    Raises:
        ValidationError: If validation fails
    """
    schema = TOOL_SCHEMAS.get(tool_name)
    
    if not schema:
        # No schema defined, return as-is
        return parameters
    
    validator = ParameterValidator()
    return validator.validate(parameters, schema)


if __name__ == "__main__":
    # Tests
    print("Testing Parameter Validation...")
    print("=" * 60)
    
    # Test 1: Valid parameters
    try:
        params = {
            "symbol": "AAPL",
            "start_date": "2024-01-01",
            "end_date": "2024-12-31"
        }
        validated = validate_tool_params("get_data", params)
        print("✓ Test 1 passed:", validated)
    except ValidationError as e:
        print("✗ Test 1 failed:", e)
    
    # Test 2: Missing required parameter
    try:
        params = {
            "symbol": "AAPL",
            "start_date": "2024-01-01"
            # Missing end_date
        }
        validated = validate_tool_params("get_data", params)
        print("✗ Test 2 should have failed")
    except ValidationError as e:
        print("✓ Test 2 passed (caught error):", e.parameter)
    
    # Test 3: Invalid date format
    try:
        params = {
            "symbol": "AAPL",
            "start_date": "01/01/2024",  # Should auto-convert
            "end_date": "2024-12-31"
        }
        validated = validate_tool_params("get_data", params)
        print("✓ Test 3 passed:", validated['start_date'])
    except ValidationError as e:
        print("✗ Test 3 failed:", e)
    
    # Test 4: Invalid symbol
    try:
        params = {
            "symbol": "INVALID@SYMBOL",
            "start_date": "2024-01-01",
            "end_date": "2024-12-31"
        }
        validated = validate_tool_params("get_data", params)
        print("✗ Test 4 should have failed")
    except ValidationError as e:
        print("✓ Test 4 passed (caught error):", e.parameter)
    
    print("\n" + "=" * 60)
    print("All tests completed!")