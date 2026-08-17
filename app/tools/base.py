"""
Base tool class and registry for AI function calling.

Tools are callable functions that the LLM can invoke to
perform actions. Each tool defines its schema for the
OpenAI function-calling format.
"""

from abc import ABC, abstractmethod
from typing import Any, Optional

# In-memory user preferences cache (keyed by user_id)
# Populated by TelegramService when handling OAuth code exchange
_user_preferences: dict[str, dict] = {}


class BaseTool(ABC):
    """Abstract base class for all AI tools."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Unique tool name."""

    @property
    @abstractmethod
    def description(self) -> str:
        """Human-readable description of what the tool does."""

    @property
    @abstractmethod
    def parameters(self) -> dict:
        """JSON Schema for the tool's parameters (OpenAI format)."""

    @abstractmethod
    async def execute(self, **kwargs) -> str:
        """Execute the tool with the given parameters and return a result string."""

    def to_openai_spec(self) -> dict:
        """Return the tool specification in OpenAI function-calling format."""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters,
            },
        }


class ToolRegistry:
    """
    Registry of all available tools.

    Tools self-register when added. The registry provides
    OpenAI-compatible specs for the LLM and executes tool calls.
    """

    def __init__(self) -> None:
        self._tools: dict[str, BaseTool] = {}

    def register(self, tool: BaseTool) -> None:
        """Register a tool."""
        self._tools[tool.name] = tool

    def get_specs(self) -> list[dict]:
        """Get OpenAI-compatible specs for all registered tools."""
        return [t.to_openai_spec() for t in self._tools.values()]

    async def execute(self, name: str, arguments: dict) -> str:
        """Execute a tool by name with the given arguments."""
        tool = self._tools.get(name)
        if tool is None:
            return f"Error: Tool '{name}' not found."
        return await tool.execute(**arguments)

    def get_tool_names(self) -> list[str]:
        """Get list of registered tool names."""
        return list(self._tools.keys())


# Global registry instance
registry = ToolRegistry()


def _normalize_user_id(user_id: str) -> str:
    """Normalize a user_id to canonical UUID format for consistent lookups."""
    try:
        import uuid
        return str(uuid.UUID(str(user_id)))
    except (ValueError, TypeError, AttributeError):
        return str(user_id)


def get_user_preferences(user_id: str) -> Optional[dict]:
    """Get the in-memory preferences for a user."""
    return _user_preferences.get(_normalize_user_id(user_id))


def update_user_preferences(user_id: str, updates: dict) -> dict:
    """Merge updates into a user's in-memory preferences."""
    key = _normalize_user_id(user_id)
    prefs = _user_preferences.setdefault(key, {})
    prefs.update(updates)
    return prefs
