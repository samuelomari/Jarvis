"""Permanent Workflow & Multi-Agent Skill Automation for Jarvis (Step 09)."""

import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from tools.registry import execute_tool, register_tool

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
WORKFLOWS_FILE = DATA_DIR / "workflows.json"


def _ensure_workflows_file():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    if not WORKFLOWS_FILE.exists():
        # Seed with starter autonomous workflows
        starter_workflows = [
            {
                "id": "wf_morning_briefing",
                "name": "morning_briefing",
                "description": "Daily executive briefing: inspects calendar, reminders, leads, and sends a summary report.",
                "trigger": "daily:08:00",
                "steps": [
                    {"action": "tool", "target": "calendar_list_events", "args": {"max_results": 5}},
                    {"action": "tool", "target": "crm_get_pipeline_summary", "args": {}},
                    {"action": "tool", "target": "send_telegram_message", "args": {"message": "☀️ Morning Briefing: Calendar and CRM synced."}},
                ],
                "created_at": datetime.now().isoformat(),
            },
            {
                "id": "wf_competitor_intel",
                "name": "competitor_intel",
                "description": "Surveillance workflow: queries market updates and compiles a competitive brief.",
                "trigger": "interval:1440",
                "steps": [
                    {"action": "agent", "target": "competitor_tracker", "task": "Synthesize latest competitor developments and pricing adjustments"},
                    {"action": "tool", "target": "send_telegram_message", "args": {"message": "🎯 Competitor Intelligence briefing compiled."}},
                ],
                "created_at": datetime.now().isoformat(),
            },
        ]
        WORKFLOWS_FILE.write_text(json.dumps(starter_workflows, indent=2), encoding="utf-8")


def _load_workflows() -> List[Dict[str, Any]]:
    _ensure_workflows_file()
    try:
        return json.loads(WORKFLOWS_FILE.read_text(encoding="utf-8"))
    except Exception:
        return []


def _save_workflows(workflows: List[Dict[str, Any]]):
    _ensure_workflows_file()
    WORKFLOWS_FILE.write_text(json.dumps(workflows, indent=2), encoding="utf-8")


@register_tool({
    "name": "create_workflow",
    "description": "Create and permanently persist a reusable multi-step autonomous workflow or multi-agent skill.",
    "input_schema": {
        "type": "object",
        "properties": {
            "name": {"type": "string", "description": "Unique identifier/name for the workflow."},
            "description": {"type": "string", "description": "Purpose and execution description."},
            "steps": {
                "type": "array",
                "description": "List of steps. Each step has 'action' ('tool' or 'agent'), 'target' (tool or agent name), and 'args' or 'task'.",
                "items": {"type": "object"},
            },
            "trigger": {
                "type": "string",
                "description": "Optional schedule or trigger expression (e.g. 'daily:09:00', 'interval:60', 'manual').",
            },
        },
        "required": ["name", "steps"],
    },
})
def create_workflow(
    name: str,
    steps: List[Dict[str, Any]],
    description: str = "",
    trigger: str = "manual",
) -> Dict[str, Any]:
    """Create and persist a new permanent workflow."""
    workflows = _load_workflows()
    clean_name = name.strip().lower().replace(" ", "_")

    # Update if already exists, else append
    for wf in workflows:
        if wf["name"] == clean_name:
            wf["description"] = description
            wf["steps"] = steps
            wf["trigger"] = trigger
            wf["updated_at"] = datetime.now().isoformat()
            _save_workflows(workflows)
            return {"success": True, "workflow": wf, "message": f"Workflow '{clean_name}' updated."}

    new_wf = {
        "id": f"wf_{uuid.uuid4().hex[:6]}",
        "name": clean_name,
        "description": description or f"Autonomous workflow {clean_name}",
        "steps": steps,
        "trigger": trigger,
        "created_at": datetime.now().isoformat(),
    }
    workflows.append(new_wf)
    _save_workflows(workflows)

    return {"success": True, "workflow": new_wf, "message": f"Workflow '{clean_name}' created successfully."}


@register_tool({
    "name": "list_workflows",
    "description": "List all registered permanent autonomous workflows and multi-agent skills.",
    "input_schema": {
        "type": "object",
        "properties": {},
        "required": [],
    },
})
def list_workflows() -> Dict[str, Any]:
    """List all permanent workflows."""
    workflows = _load_workflows()
    return {"success": True, "count": len(workflows), "workflows": workflows}


@register_tool({
    "name": "execute_workflow",
    "description": "Run an existing permanent workflow or multi-agent skill sequentially.",
    "input_schema": {
        "type": "object",
        "properties": {
            "name": {"type": "string", "description": "Name of the workflow to run."},
        },
        "required": ["name"],
    },
})
def execute_workflow(name: str) -> Dict[str, Any]:
    """Execute all steps in a specified workflow."""
    workflows = _load_workflows()
    clean_name = name.strip().lower().replace(" ", "_")
    target_wf = next((w for w in workflows if w["name"] == clean_name), None)

    if not target_wf:
        return {"success": False, "error": f"Workflow '{name}' not found."}

    execution_log = []
    from agent.agents.orchestrator import get_orchestrator
    orchestrator = get_orchestrator()

    for idx, step in enumerate(target_wf.get("steps", []), 1):
        action_type = step.get("action", "tool")
        target = step.get("target")

        if action_type == "tool":
            args = step.get("args", {})
            res = execute_tool(target, args)
            execution_log.append({"step": idx, "type": "tool", "target": target, "result": res})
        elif action_type == "agent":
            task = step.get("task", f"Execute action for workflow {clean_name}")
            res = orchestrator.delegate(agent_name=target, task=task)
            execution_log.append({"step": idx, "type": "agent", "target": target, "result": res})
        else:
            execution_log.append({"step": idx, "error": f"Unknown action type: {action_type}"})

    return {
        "success": True,
        "workflow": clean_name,
        "steps_executed": len(execution_log),
        "log": execution_log,
    }

