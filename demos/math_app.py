"""
Math WebApp Demo

A mathematical operations webapp that exposes calculation tools to the AI Connector Platform.
Demonstrates how to use the SDK with typed parameters and complex return values.
"""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Dict, Any, List
import uvicorn
import httpx

# Import our SDK
import sys
sys.path.insert(0, '/workspace')
from sdk.decorators import tool

app = FastAPI(title="Math App", description="Demo math service with AI tools")


@tool
def add(a: float, b: float) -> Dict[str, Any]:
    """
    Add two numbers together.
    
    Returns the sum of the two input values.
    """
    return {"result": a + b, "operation": "addition", "operands": [a, b]}


@tool
def multiply(a: float, b: float) -> Dict[str, Any]:
    """
    Multiply two numbers.
    
    Returns the product of the two input values.
    """
    return {"result": a * b, "operation": "multiplication", "operands": [a, b]}


@tool
def calculate_average(numbers: List[float]) -> Dict[str, Any]:
    """
    Calculate the average of a list of numbers.
    
    Returns the arithmetic mean of the provided values.
    """
    if not numbers:
        return {"error": "Empty list provided", "result": None}
    
    avg = sum(numbers) / len(numbers)
    return {
        "result": avg,
        "operation": "average",
        "count": len(numbers),
        "sum": sum(numbers)
    }


@tool(name="calculate_statistics")
def get_statistics(values: List[float]) -> Dict[str, Any]:
    """
    Calculate comprehensive statistics for a list of numbers.
    
    Returns min, max, mean, median, and count.
    """
    if not values:
        return {"error": "Empty list provided"}
    
    sorted_values = sorted(values)
    n = len(sorted_values)
    
    # Calculate median
    if n % 2 == 0:
        median = (sorted_values[n//2 - 1] + sorted_values[n//2]) / 2
    else:
        median = sorted_values[n//2]
    
    return {
        "min": min(values),
        "max": max(values),
        "mean": sum(values) / n,
        "median": median,
        "count": n,
        "range": max(values) - min(values)
    }


class ExecuteRequest(BaseModel):
    """Request model for tool execution endpoint."""
    arguments: Dict[str, Any]


@app.get("/")
async def root():
    """Health check endpoint."""
    return {
        "service": "Math App", 
        "status": "running", 
        "tools": ["add", "multiply", "calculate_average", "calculate_statistics"]
    }


@app.post("/execute/add")
async def execute_add(request: ExecuteRequest):
    """Execute the add tool."""
    a = request.arguments.get("a")
    b = request.arguments.get("b")
    
    if a is None or b is None:
        raise HTTPException(status_code=400, detail="Missing 'a' or 'b' argument")
    
    result = add(a, b)
    return {"result": result}


@app.post("/execute/multiply")
async def execute_multiply(request: ExecuteRequest):
    """Execute the multiply tool."""
    a = request.arguments.get("a")
    b = request.arguments.get("b")
    
    if a is None or b is None:
        raise HTTPException(status_code=400, detail="Missing 'a' or 'b' argument")
    
    result = multiply(a, b)
    return {"result": result}


@app.post("/execute/calculate_average")
async def execute_average(request: ExecuteRequest):
    """Execute the calculate_average tool."""
    numbers = request.arguments.get("numbers")
    
    if numbers is None:
        raise HTTPException(status_code=400, detail="Missing 'numbers' argument")
    
    result = calculate_average(numbers)
    return {"result": result}


@app.post("/execute/calculate_statistics")
async def execute_statistics(request: ExecuteRequest):
    """Execute the calculate_statistics tool."""
    values = request.arguments.get("values")
    
    if values is None:
        raise HTTPException(status_code=400, detail="Missing 'values' argument")
    
    result = get_statistics(values)
    return {"result": result}


@app.on_event("startup")
async def register_with_orchestrator():
    """Auto-register tools with the orchestrator on startup."""
    orchestrator_url = "http://localhost:8000"
    app_url = "http://localhost:8002"
    
    tools_to_register = [
        {
            "name": "add",
            "description": "Add two numbers together.",
            "parameters": add._tool_schema["parameters"],
            "app_url": app_url
        },
        {
            "name": "multiply",
            "description": "Multiply two numbers.",
            "parameters": multiply._tool_schema["parameters"],
            "app_url": app_url
        },
        {
            "name": "calculate_average",
            "description": "Calculate the average of a list of numbers.",
            "parameters": calculate_average._tool_schema["parameters"],
            "app_url": app_url
        },
        {
            "name": "calculate_statistics",
            "description": "Calculate comprehensive statistics for a list of numbers.",
            "parameters": get_statistics._tool_schema["parameters"],
            "app_url": app_url
        }
    ]
    
    async with httpx.AsyncClient(timeout=10.0) as client:
        for tool_data in tools_to_register:
            try:
                response = await client.post(f"{orchestrator_url}/register", json=tool_data)
                if response.status_code == 201:
                    print(f"✓ Registered tool: {tool_data['name']}")
                elif response.status_code == 409:
                    print(f"⚠ Tool already registered: {tool_data['name']}")
                else:
                    print(f"✗ Failed to register {tool_data['name']}: {response.text}")
            except Exception as e:
                print(f"✗ Could not connect to orchestrator: {e}")
                print("  (Make sure the orchestrator is running on port 8000)")


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8002)
