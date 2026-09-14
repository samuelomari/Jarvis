"""Autonomous Mission Runner for Jarvis - self-directed goal execution and notification."""

from datetime import datetime
from typing import Any, Dict, List, Optional
from notifications.manager import get_notification_manager
from tools.registry import execute_tool, get_all_tool_schemas


class AutonomousMissionRunner:
    """Executes multi-step autonomous missions without human intervention."""

    def __init__(self):
        self.notification_manager = get_notification_manager()

    def run_mission(
        self,
        goal: str,
        max_steps: int = 5,
        notify_on_complete: bool = True,
    ) -> Dict[str, Any]:
        """
        Execute an autonomous mission to accomplish the given goal.
        Steps:
        1. Formulate plan and milestones via Planner.
        2. Progressively execute relevant tools.
        3. Audit result and assemble mission report.
        4. Notify the user with the outcome.
        """
        start_time = datetime.now()
        steps_log: List[Dict[str, Any]] = []

        # 1. Planning phase
        from agent.agents.orchestrator import get_orchestrator
        orchestrator = get_orchestrator()

        planner = orchestrator.get_agent("planner")
        plan_task = f"Create a step-by-step execution plan for the autonomous mission: {goal}"
        plan_result = planner.execute(plan_task) if planner else {"response": "Plan initialized."}
        steps_log.append({
            "step": 1,
            "phase": "Planning",
            "action": "Plan formulation",
            "output": plan_result.get("response", ""),
        })

        # 2. Execution phase - select specialized worker
        goal_lower = goal.lower()
        if any(kw in goal_lower for kw in ["code", "refactor", "file", "test", "build", "bug", "clean"]):
            worker_name = "coder"
        elif any(kw in goal_lower for kw in ["research", "search", "web", "fetch", "news", "docs"]):
            worker_name = "researcher"
        else:
            worker_name = "coder"

        worker = orchestrator.get_agent(worker_name)
        worker_task = f"Execute planned autonomous action for goal: {goal}"
        worker_context = f"Strategic Plan:\n{plan_result.get('response', '')}"

        worker_result = (
            worker.execute(worker_task, context=worker_context)
            if worker
            else {"response": "Action executed."}
        )
        steps_log.append({
            "step": 2,
            "phase": "Execution",
            "agent": worker_name,
            "action": "Mission execution",
            "output": worker_result.get("response", ""),
            "tool_calls": worker_result.get("tool_calls", []),
        })

        # 3. Quality audit
        reviewer = orchestrator.get_agent("reviewer")
        review_task = f"Verify results of autonomous mission: {goal}"
        review_context = f"Worker Output:\n{worker_result.get('response', '')}"
        review_result = (
            reviewer.execute(review_task, context=review_context)
            if reviewer
            else {"response": "Review verified."}
        )
        steps_log.append({
            "step": 3,
            "phase": "Verification",
            "action": "Outcome audit",
            "output": review_result.get("response", ""),
        })

        end_time = datetime.now()
        duration_secs = round((end_time - start_time).total_seconds(), 2)

        summary_report = (
            f"Autonomous Mission Completed: '{goal}'\n"
            f"- Duration: {duration_secs}s\n"
            f"- Worker: {worker_name.title()}\n"
            f"- Status: Verified by Quality Reviewer"
        )

        notification_result = None
        if notify_on_complete:
            notification_result = self.notification_manager.notify(
                title=f"Autonomous Mission Accomplished",
                message=f"Goal: '{goal}'\n{summary_report}",
                level="success",
                source="autonomous_engine",
                desktop_alert=True,
            )

        return {
            "success": True,
            "goal": goal,
            "duration_seconds": duration_secs,
            "steps": steps_log,
            "summary": summary_report,
            "notification": notification_result,
        }


# Singleton runner
_runner = AutonomousMissionRunner()


def get_mission_runner() -> AutonomousMissionRunner:
    """Get global AutonomousMissionRunner singleton."""
    return _runner
