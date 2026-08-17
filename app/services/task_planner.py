"""
Task Planner service.

Breaks down complex user requests into multi-step plans
and executes them sequentially. This enables the AI to
handle multi-step workflows like "schedule a meeting and
send an email about it" with a single command.
"""

from typing import Optional

from app.core.logging import logger
from app.tools.base import registry


class TaskPlanner:
    """
    Executes multi-step task plans by breaking down a goal
    into sequential tool calls.

    Each step is a dict with:
      - tool: the tool name to call
      - arguments: the arguments to pass
      - description: human-readable description of the step
    """

    async def execute_plan(self, plan: list[dict]) -> list[dict]:
        """
        Execute a multi-step plan.

        Args:
            plan: List of steps, each with 'tool', 'arguments', 'description'.

        Returns:
            List of step results with 'step', 'tool', 'result', 'success'.
        """
        results = []
        for i, step in enumerate(plan, 1):
            tool_name = step.get("tool", "")
            arguments = step.get("arguments", {})
            description = step.get("description", tool_name)

            logger.info("Step %d/%d: %s (%s)", i, len(plan), description, tool_name)

            try:
                result = await registry.execute(tool_name, arguments)
                results.append({
                    "step": i,
                    "tool": tool_name,
                    "description": description,
                    "result": result,
                    "success": True,
                })
                logger.info("Step %d result: %s", i, result[:200])
            except Exception as e:
                logger.error("Step %d failed: %s", i, e)
                results.append({
                    "step": i,
                    "tool": tool_name,
                    "description": description,
                    "result": f"Error: {e}",
                    "success": False,
                })
                break  # Stop on first failure

        return results


# Singleton instance
task_planner = TaskPlanner()