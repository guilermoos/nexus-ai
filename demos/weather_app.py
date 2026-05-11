"""
Weather WebApp Demo

A simple weather API webapp that exposes tools to the AI Connector Platform.
Demonstrates how to use the SDK to expose functions to LLMs.
"""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Dict, Any
import uvicorn
import httpx

# Import our SDK
import sys
sys.path.insert(0, '/workspace')
from sdk.decorators import tool

app = FastAPI(title="Weather App", description="Demo weather service with AI tools")

# In-memory "database" of cities
WEATHER_DATA = {
    "São Paulo": {"temp": 28, "condition": "Sunny", "humidity": 65},
    "Rio de Janeiro": {"temp": 32, "condition": "Partly Cloudy", "humidity": 70},
    "Brasília": {"temp": 25, "condition": "Clear", "humidity": 45},
    "Porto Alegre": {"temp": 18, "condition": "Rainy", "humidity": 80},
    "Recife": {"temp": 30, "condition": "Sunny", "humidity": 75},
}


@tool
def get_weather(city: str) -> Dict[str, Any]:
    """
    Get current weather information for a specific city.
    
    Returns temperature, condition, and humidity.
    """
    if city not in WEATHER_DATA:
        return {"error": f"City '{city}' not found", "available_cities": list(WEATHER_DATA.keys())}
    
    data = WEATHER_DATA[city]
    return {
        "city": city,
        "temperature": data["temp"],
        "condition": data["condition"],
        "humidity": data["humidity"],
        "unit": "celsius"
    }


@tool
def list_available_cities() -> Dict[str, Any]:
    """
    List all cities where weather data is available.
    
    Useful for discovering which locations can be queried.
    """
    return {
        "cities": list(WEATHER_DATA.keys()),
        "count": len(WEATHER_DATA)
    }


class ExecuteRequest(BaseModel):
    """Request model for tool execution endpoint."""
    arguments: Dict[str, Any]


@app.get("/")
async def root():
    """Health check endpoint."""
    return {"service": "Weather App", "status": "running", "tools": ["get_weather", "list_available_cities"]}


@app.post("/execute/get_weather")
async def execute_get_weather(request: ExecuteRequest):
    """Execute the get_weather tool."""
    city = request.arguments.get("city")
    if not city:
        raise HTTPException(status_code=400, detail="Missing 'city' argument")
    
    result = get_weather(city)
    return {"result": result}


@app.post("/execute/list_available_cities")
async def execute_list_cities(request: ExecuteRequest):
    """Execute the list_available_cities tool."""
    result = list_available_cities()
    return {"result": result}


@app.on_event("startup")
async def register_with_orchestrator():
    """Auto-register tools with the orchestrator on startup."""
    orchestrator_url = "http://localhost:8000"
    app_url = "http://localhost:8001"
    
    tools_to_register = [
        {
            "name": "get_weather",
            "description": "Get current weather information for a specific city.",
            "parameters": get_weather._tool_schema["parameters"],
            "app_url": app_url
        },
        {
            "name": "list_available_cities",
            "description": "List all cities where weather data is available.",
            "parameters": list_available_cities._tool_schema["parameters"],
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
    uvicorn.run(app, host="0.0.0.0", port=8001)
