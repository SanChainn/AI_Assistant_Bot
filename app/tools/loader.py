"""
Tool loader — registers all available tools into the global registry.

Call init_tools() during application startup to make all tools available.
"""

from app.tools.base import registry
from app.tools.system_tools import CalculatorTool, GetCurrentTimeTool, GetWeatherTool
from app.tools.calendar_tools import CreateEventTool, ListEventsTool
from app.tools.email_tools import SendEmailTool, ListInboxTool


def init_tools() -> None:
    """Register all tools into the global registry."""
    # System tools
    registry.register(GetCurrentTimeTool())
    registry.register(CalculatorTool())
    registry.register(GetWeatherTool())

    # Calendar tools
    registry.register(CreateEventTool())
    registry.register(ListEventsTool())

    # Email tools
    registry.register(SendEmailTool())
    registry.register(ListInboxTool())