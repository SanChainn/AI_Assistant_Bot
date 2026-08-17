"""
System tools for the AI assistant.

Provides tools for getting current time, date, weather, and calculations.
Weather uses the free Open-Meteo API (no API key required).
"""

from datetime import datetime, timezone

import httpx

from app.tools.base import BaseTool


class GetCurrentTimeTool(BaseTool):
    """Tool to get the current date and time."""

    @property
    def name(self) -> str:
        return "get_current_time"

    @property
    def description(self) -> str:
        return "Get the current date and time in UTC. Use this when the user asks what time or date it is."

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {},
            "required": [],
        }

    async def execute(self, **kwargs) -> str:
        now = datetime.now(timezone.utc)
        return now.strftime("%Y-%m-%d %H:%M:%S UTC")


class CalculatorTool(BaseTool):
    """Tool to perform mathematical calculations."""

    @property
    def name(self) -> str:
        return "calculator"

    @property
    def description(self) -> str:
        return "Perform a mathematical calculation. Provide the expression as a string."

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "expression": {
                    "type": "string",
                    "description": "The mathematical expression to evaluate (e.g., '2 + 2', 'sqrt(16)')",
                }
            },
            "required": ["expression"],
        }

    async def execute(self, expression: str, **kwargs) -> str:
        import ast
        import math
        import operator

        # Safe math operations mapping
        SAFE_OPS = {
            ast.Add: operator.add,
            ast.Sub: operator.sub,
            ast.Mult: operator.mul,
            ast.Div: operator.truediv,
            ast.Mod: operator.mod,
            ast.Pow: operator.pow,
            ast.USub: operator.neg,
            ast.UAdd: operator.pos,
        }

        SAFE_FUNCS = {
            "sqrt": math.sqrt,
            "abs": abs,
            "round": round,
            "pow": pow,
        }

        def _safe_eval(node):
            """Recursively evaluate an AST node safely."""
            if isinstance(node, ast.Expression):
                return _safe_eval(node.body)
            if isinstance(node, ast.Constant):
                if isinstance(node.value, (int, float)):
                    return node.value
                raise ValueError(f"Invalid constant: {node.value}")
            if isinstance(node, ast.BinOp):
                left = _safe_eval(node.left)
                right = _safe_eval(node.right)
                op_type = type(node.op)
                if op_type in SAFE_OPS:
                    return SAFE_OPS[op_type](left, right)
                raise ValueError(f"Unsupported operator: {op_type.__name__}")
            if isinstance(node, ast.UnaryOp):
                operand = _safe_eval(node.operand)
                op_type = type(node.op)
                if op_type in SAFE_OPS:
                    return SAFE_OPS[op_type](operand)
                raise ValueError(f"Unsupported unary op: {op_type.__name__}")
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name) and node.func.id in SAFE_FUNCS:
                    args = [_safe_eval(a) for a in node.args]
                    return SAFE_FUNCS[node.func.id](*args)
                raise ValueError("Only sqrt(), abs(), round(), pow() functions allowed")
            raise ValueError(f"Invalid expression node: {type(node).__name__}")

        try:
            tree = ast.parse(expression.strip(), mode="eval")
            result = _safe_eval(tree)
            return f"{expression} = {result}"
        except Exception as e:
            return f"Error evaluating '{expression}': {e}"


# Open-Meteo weather code descriptions
WEATHER_CODES = {
    0: "Clear sky",
    1: "Mainly clear",
    2: "Partly cloudy",
    3: "Overcast",
    45: "Foggy",
    48: "Depositing rime fog",
    51: "Light drizzle",
    53: "Moderate drizzle",
    55: "Dense drizzle",
    56: "Light freezing drizzle",
    57: "Dense freezing drizzle",
    61: "Slight rain",
    63: "Moderate rain",
    65: "Heavy rain",
    66: "Light freezing rain",
    67: "Heavy freezing rain",
    71: "Slight snow fall",
    73: "Moderate snow fall",
    75: "Heavy snow fall",
    77: "Snow grains",
    80: "Slight rain showers",
    81: "Moderate rain showers",
    82: "Violent rain showers",
    85: "Slight snow showers",
    86: "Heavy snow showers",
    95: "Thunderstorm",
    96: "Thunderstorm with slight hail",
    99: "Thunderstorm with heavy hail",
}


class GetWeatherTool(BaseTool):
    """Tool to get real weather data using the free Open-Meteo API."""

    @property
    def name(self) -> str:
        return "get_weather"

    @property
    def description(self) -> str:
        return (
            "Get the current weather for any city using real data from Open-Meteo API (free, no key needed). "
            "Returns temperature, humidity, wind speed, and weather conditions. "
            "Always use this tool when the user asks about the weather."
        )

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "city": {
                    "type": "string",
                    "description": "The city name (e.g., 'Tokyo', 'New York', 'Yangon')",
                }
            },
            "required": ["city"],
        }

    async def execute(self, city: str, **kwargs) -> str:
        """Fetch real weather data from Open-Meteo API."""
        async with httpx.AsyncClient(timeout=10.0) as client:
            # Step 1: Geocode the city name to get coordinates
            try:
                geo_resp = await client.get(
                    "https://geocoding-api.open-meteo.com/v1/search",
                    params={"name": city, "count": 1, "language": "en", "format": "json"},
                )
                geo_data = geo_resp.json()
                results = geo_data.get("results", [])
                if not results:
                    return f"Could not find city '{city}'. Please check the spelling."
                lat = results[0]["latitude"]
                lon = results[0]["longitude"]
                found_name = f"{results[0].get('name', city)}, {results[0].get('country', '')}"
            except Exception as e:
                return f"Error finding location '{city}': {e}"

            # Step 2: Get current weather
            try:
                weather_resp = await client.get(
                    "https://api.open-meteo.com/v1/forecast",
                    params={
                        "latitude": lat,
                        "longitude": lon,
                        "current": "temperature_2m,relative_humidity_2m,apparent_temperature,weather_code,wind_speed_10m",
                        "timezone": "auto",
                    },
                )
                weather_data = weather_resp.json()
                current = weather_data.get("current", {})
                temp = current.get("temperature_2m", "?")
                feels_like = current.get("apparent_temperature", "?")
                humidity = current.get("relative_humidity_2m", "?")
                wind = current.get("wind_speed_10m", "?")
                code = current.get("weather_code", 0)
                description = WEATHER_CODES.get(code, f"Code {code}")

                return (
                    f"Weather in {found_name}:\n"
                    f"  Condition: {description}\n"
                    f"  Temperature: {temp}C (feels like {feels_like}C)\n"
                    f"  Humidity: {humidity}%\n"
                    f"  Wind: {wind} km/h"
                )
            except Exception as e:
                return f"Error fetching weather for {city}: {e}"