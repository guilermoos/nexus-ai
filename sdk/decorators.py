"""
Decorators for exposing functions to AI models.

This module provides the @tool decorator that automatically generates
JSON Schema from function signatures and docstrings using Pydantic.
"""

import inspect
import json
from functools import wraps
from typing import Any, Callable, Dict, Optional, get_type_hints
from pydantic import create_model, BaseModel
from pydantic.json_schema import GenerateJsonSchema


class ToolMetadata(BaseModel):
    """Metadata for a registered tool."""
    name: str
    description: str
    function: Callable
    input_schema: Dict[str, Any]
    output_type: type


def _generate_schema(func: Callable) -> Dict[str, Any]:
    """
    Generate JSON Schema from function signature and docstring.
    
    Uses Pydantic to create a model from function parameters,
    then extracts the JSON Schema for validation and LLM consumption.
    """
    sig = inspect.signature(func)
    type_hints = get_type_hints(func)
    
    # Build field definitions for Pydantic model
    fields = {}
    for param_name, param in sig.parameters.items():
        if param_name == 'self':
            continue
            
        param_type = type_hints.get(param_name, Any)
        
        # Handle default values
        if param.default is inspect.Parameter.empty:
            fields[param_name] = (param_type, ...)
        else:
            fields[param_name] = (param_type, param.default)
    
    # Create dynamic Pydantic model
    if fields:
        model = create_model(f"{func.__name__}_input", **fields)
        # Generate JSON Schema
        schema = model.model_json_schema()
    else:
        # Function with no parameters
        schema = {
            "type": "object",
            "properties": {},
            "required": []
        }
    
    # Extract description from docstring
    description = func.__doc__ or ""
    description = inspect.cleandoc(description).split('\n')[0].strip()
    
    return {
        "name": func.__name__,
        "description": description,
        "parameters": schema
    }


def tool(_func: Optional[Callable] = None, *, name: Optional[str] = None):
    """
    Decorator to expose a function as an AI-accessible tool.
    
    Automatically generates JSON Schema from the function's signature
    and docstring. The decorated function can be registered with the
    orchestrator for use by LLMs.
    
    Args:
        _func: The function to decorate (when used without parentheses)
        name: Optional custom name for the tool (defaults to function name)
    
    Returns:
        The wrapped function with attached metadata
    
    Example:
        @tool
        def add(a: int, b: int) -> int:
            \"\"\"Add two numbers together.\"\"\"
            return a + b
        
        @tool(name="calculate_sum")
        def add_numbers(a: int, b: int) -> int:
            \"\"\"Add two numbers together.\"\"\"
            return a + b
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            return func(*args, **kwargs)
        
        # Generate schema and attach metadata
        schema = _generate_schema(func)
        if name:
            schema["name"] = name
        
        wrapper._tool_metadata = ToolMetadata(
            name=schema["name"],
            description=schema["description"],
            function=func,
            input_schema=schema["parameters"],
            output_type=type_hints.get('return', Any) if (type_hints := get_type_hints(func)) else Any
        )
        
        # Attach schema for easy access
        wrapper._tool_schema = schema
        
        return wrapper
    
    # Handle both @tool and @tool() usage
    if _func is not None:
        return decorator(_func)
    return decorator
