"""Tools for scheduling and triggering autonomous background missions."""

from typing import Any, Dict, List, Optional
from tools.registry import register_tool


def _get_sched():
    from autonomous.scheduler import get_scheduler
    return get_scheduler()


def _get_runner():
    from autonomous.engine import get_mission_runner
    return get_mission_runner()


@register_tool({
    "name": "schedule_autonomous_task",
    "description": "Schedule a recurring or one-shot autonomous mission that Jarvis runs independently in the background.",
    "input_schema": {
        "type": "object",
        "properties": {
            "name": {
                "type": "string",
                "description": "Short, human-readable name of the scheduled mission.",
            },
            "goal": {
                "type": "string",
                "description": "Detailed goal or objective for the autonomous runner to achieve.",
            },
            "schedule_type": {
                "type": "string",
                "description": "Schedule cadence: 'interval' (every N minutes), 'daily' (at HH:MM), or 'once' (at date/time). Defaults to 'interval'.",
            },
            "interval_minutes": {
                "type": "integer",
                "description": "Minutes between executions (for 'interval' type). Default is 60.",
            },
            "run_at": {
                "type": "string",
                "description": "Time string for 'daily' (e.g. '09:00') or 'once' (e.g. '2026-09-15 14:00').",
            },
        },
        "required": ["name", "goal"],
    },
})
def schedule_autonomous_task(
    name: str,
    goal: str,
    schedule_type: str = "interval",
    interval_minutes: int = 60,
    run_at: Optional[str] = None,
) -> Dict[str, Any]:
    """Schedule autonomous task."""
    scheduler = _get_sched()
    return scheduler.add_task(
        name=name,
        goal=goal,
        schedule_type=schedule_type,
        interval_minutes=interval_minutes,
        run_at=run_at,
    )


@register_tool({
    "name": "list_scheduled_tasks",
    "description": "List all active, completed, or scheduled autonomous background missions.",
    "input_schema": {
        "type": "object",
        "properties": {
            "status": {
                "type": "string",
                "description": "Optional status filter ('active', 'completed').",
            },
        },
        "required": [],
    },
})
def list_scheduled_tasks(status: Optional[str] = None) -> Dict[str, Any]:
    """List scheduled tasks."""
    scheduler = _get_sched()
    tasks = scheduler.list_tasks(status=status)
    return {
        "success": True,
        "count": len(tasks),
        "tasks": tasks,
    }


@register_tool({
    "name": "cancel_scheduled_task",
    "description": "Cancel a scheduled autonomous task by its task ID.",
    "input_schema": {
        "type": "object",
        "properties": {
            "task_id": {
                "type": "string",
                "description": "The unique ID of the task to cancel.",
            },
        },
        "required": ["task_id"],
    },
})
def cancel_scheduled_task(task_id: str) -> Dict[str, Any]:
    """Cancel scheduled task."""
    scheduler = _get_sched()
    return scheduler.cancel_task(task_id=task_id)


@register_tool({
    "name": "run_autonomous_mission",
    "description": "Directly run a multi-step autonomous mission now, with plan formulation, execution, QA verification, and user notification.",
    "input_schema": {
        "type": "object",
        "properties": {
            "goal": {
                "type": "string",
                "description": "High-level goal or objective to execute autonomously.",
            },
            "max_steps": {
                "type": "integer",
                "description": "Maximum steps for mission execution (default: 5).",
            },
        },
        "required": ["goal"],
    },
})
def run_autonomous_mission(goal: str, max_steps: int = 5) -> Dict[str, Any]:
    """Run autonomous mission immediately."""
    runner = _get_runner()
    return runner.run_mission(goal=goal, max_steps=max_steps, notify_on_complete=True)
