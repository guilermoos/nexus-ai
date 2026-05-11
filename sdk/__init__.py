"""
AI Connector SDK

Minimalist SDK for exposing functions to AI models.
Usage:
    from ai_connector_sdk import tool

    @tool
    def my_function(param: str) -> str:
        \"\"\"Description of what the function does.\"\"\"
        return result
"""

from .decorators import tool

__all__ = ["tool"]
