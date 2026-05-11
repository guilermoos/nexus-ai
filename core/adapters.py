"""
Core Adapters

Implements the Adapter pattern for different LLM providers.
Each adapter translates LLM-specific function calling formats to our standard.
"""

from abc import ABC, abstractmethod
import json
from typing import Dict, List, Any, Optional


class LLMAdapter(ABC):
    """Base class for LLM adapters."""
    
    @abstractmethod
    def parse_tool_call(self, response: Any) -> Dict[str, Any]:
        """Parse LLM response to extract tool call information."""
        pass
    
    @abstractmethod
    def format_tools_for_llm(self, tools: List[Dict[str, Any]]) -> Any:
        """Format our tool schema for the specific LLM provider."""
        pass
    
    @abstractmethod
    def format_result_for_llm(self, result: Any, tool_name: str) -> Any:
        """Format tool execution result back to LLM's expected format."""
        pass


class OpenAIAdapter(LLMAdapter):
    """Adapter for OpenAI/compatible APIs (GPT-4, GPT-3.5, etc.)."""
    
    def parse_tool_call(self, response: Any) -> Dict[str, Any]:
        """Parse OpenAI chat completion response."""
        message = response.choices[0].message
        
        if not message.tool_calls:
            return {"tool_name": None, "arguments": None}
        
        tool_call = message.tool_calls[0]
        return {
            "tool_name": tool_call.function.name,
            "arguments": json.loads(tool_call.function.arguments),
            "call_id": tool_call.id
        }
    
    def format_tools_for_llm(self, tools: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Convert our tool schema to OpenAI function format."""
        formatted = []
        for tool in tools:
            formatted.append({
                "type": "function",
                "function": {
                    "name": tool["name"],
                    "description": tool["description"],
                    "parameters": tool["parameters"]
                }
            })
        return formatted
    
    def format_result_for_llm(self, result: Any, tool_name: str, call_id: str) -> Dict[str, Any]:
        """Format result as OpenAI tool message."""
        return {
            "role": "tool",
            "tool_call_id": call_id,
            "name": tool_name,
            "content": json.dumps(result) if not isinstance(result, str) else result
        }


class OllamaAdapter(LLMAdapter):
    """Adapter for local Ollama models."""
    
    def parse_tool_call(self, response: Dict[str, Any]) -> Dict[str, Any]:
        """Parse Ollama response with tool calls."""
        # Ollama format may vary by model, this is a generic implementation
        message = response.get("message", {})
        tool_calls = message.get("tool_calls", [])
        
        if not tool_calls:
            return {"tool_name": None, "arguments": None}
        
        tool_call = tool_calls[0]
        return {
            "tool_name": tool_call.get("function", {}).get("name"),
            "arguments": tool_call.get("function", {}).get("arguments", {}),
            "call_id": tool_call.get("id", "ollama-call-1")
        }
    
    def format_tools_for_llm(self, tools: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Convert our tool schema to Ollama format."""
        formatted = []
        for tool in tools:
            formatted.append({
                "type": "function",
                "function": {
                    "name": tool["name"],
                    "description": tool["description"],
                    "parameters": tool["parameters"]
                }
            })
        return formatted
    
    def format_result_for_llm(self, result: Any, tool_name: str, call_id: str) -> Dict[str, Any]:
        """Format result for Ollama context."""
        return {
            "role": "tool",
            "name": tool_name,
            "content": json.dumps(result) if not isinstance(result, str) else result
        }


# Factory function to get the appropriate adapter
def get_adapter(provider: str) -> LLMAdapter:
    """Get an LLM adapter by provider name."""
    adapters = {
        "openai": OpenAIAdapter(),
        "ollama": OllamaAdapter(),
    }
    
    if provider.lower() not in adapters:
        raise ValueError(f"Unknown provider: {provider}. Supported: {list(adapters.keys())}")
    
    return adapters[provider.lower()]
