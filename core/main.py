"""
Core Orchestrator

Main entry point for the AI Connector Platform.
Handles tool registration, validation, and routing between LLMs and apps.
"""

from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel, ValidationError
from typing import Dict, List, Any, Optional
import uvicorn

# In-memory tool registry (will be replaced with distributed registry later)
tool_registry: Dict[str, Dict[str, Any]] = {}

app = FastAPI(
    title="AI Connector Orchestrator",
    description="Middleware for standardized Function Calling across LLMs and apps",
    version="0.1.0"
)


class ToolSchema(BaseModel):
    """Schema for tool registration."""
    name: str
    description: str
    parameters: Dict[str, Any]
    app_url: str  # URL of the app exposing this tool


class ToolCall(BaseModel):
    """Request to invoke a tool."""
    tool_name: str
    arguments: Dict[str, Any]


class ToolResponse(BaseModel):
    """Response from tool execution."""
    success: bool
    result: Any
    error: Optional[str] = None


@app.post("/register", status_code=status.HTTP_201_CREATED)
async def register_tool(tool: ToolSchema):
    """
    Register a new tool from an external app.
    
    Apps call this endpoint to expose their functions to the orchestrator.
    """
    if tool.name in tool_registry:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Tool '{tool.name}' already registered"
        )
    
    tool_registry[tool.name] = tool.model_dump()
    return {"message": f"Tool '{tool.name}' registered successfully", "tool": tool}


@app.get("/tools")
async def list_tools():
    """List all registered tools."""
    return {"tools": list(tool_registry.values())}


@app.get("/tools/{tool_name}")
async def get_tool(tool_name: str):
    """Get details of a specific tool."""
    if tool_name not in tool_registry:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Tool '{tool_name}' not found"
        )
    return tool_registry[tool_name]


@app.post("/invoke", response_model=ToolResponse)
async def invoke_tool(call: ToolCall):
    """
    Invoke a registered tool with validated arguments.
    
    This is the main entry point for LLMs to execute tools.
    The orchestrator validates arguments against the JSON Schema
    before forwarding to the target app.
    """
    if call.tool_name not in tool_registry:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Tool '{call.tool_name}' not found"
        )
    
    tool_info = tool_registry[call.tool_name]
    
    # Validate arguments against the tool's JSON Schema using Pydantic
    try:
        # Create a dynamic model for validation
        from pydantic import create_model
        
        # Extract parameter definitions from schema
        properties = tool_info["parameters"].get("properties", {})
        required = tool_info["parameters"].get("required", [])
        
        fields = {}
        for param_name, param_schema in properties.items():
            param_type = _json_type_to_python(param_schema.get("type", "string"))
            default = ... if param_name in required else None
            fields[param_name] = (param_type, default)
        
        # Create and validate
        validator_model = create_model("ToolArgs", **fields)
        validated_args = validator_model(**call.arguments).model_dump()
        
    except ValidationError as e:
        return ToolResponse(
            success=False,
            result=None,
            error=f"Validation failed: {e.error()}"
        )
    except Exception as e:
        return ToolResponse(
            success=False,
            result=None,
            error=f"Schema validation error: {str(e)}"
        )
    
    # Forward to the target app
    import httpx
    app_url = tool_info["app_url"]
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{app_url}/execute/{call.tool_name}",
                json={"arguments": validated_args}
            )
            response.raise_for_status()
            result = response.json()
            
            return ToolResponse(
                success=True,
                result=result.get("result"),
                error=None
            )
    except httpx.HTTPError as e:
        return ToolResponse(
            success=False,
            result=None,
            error=f"App communication error: {str(e)}"
        )
    except Exception as e:
        return ToolResponse(
            success=False,
            result=None,
            error=f"Unexpected error: {str(e)}"
        )


def _json_type_to_python(json_type: str) -> type:
    """Convert JSON Schema types to Python types."""
    type_mapping = {
        "string": str,
        "integer": int,
        "number": float,
        "boolean": bool,
        "array": list,
        "object": dict,
    }
    return type_mapping.get(json_type, str)


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
