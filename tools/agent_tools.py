"""Tools for interacting with specialized AI subagents and multi-agent workflows."""

from tools.registry import register_tool


def _get_orch():
    from agent.agents.orchestrator import get_orchestrator
    return get_orchestrator()


@register_tool({
    "name": "delegate_task",
    "description": "Delegate a specialized task to a designated AI subagent (coder, researcher, planner, reviewer).",
    "input_schema": {
        "type": "object",
        "properties": {
            "agent_name": {
                "type": "string",
                "description": "Target subagent identifier: 'coder', 'researcher', 'planner', or 'reviewer'.",
            },
            "task": {
                "type": "string",
                "description": "The specific task or objective for the subagent to execute.",
            },
            "context": {
                "type": "string",
                "description": "Optional background context, existing code, or constraints.",
            },
        },
        "required": ["agent_name", "task"],
    },
})
def delegate_task(
    agent_name: str, task: str, context: Optional[str] = None
) -> Dict[str, Any]:
    """Delegate a task to a specialized agent."""
    orchestrator = _get_orch()
    return orchestrator.delegate(agent_name=agent_name, task=task, context=context)


@register_tool({
    "name": "list_available_agents",
    "description": "List all registered AI subagents with their specializations, roles, and allowed tools.",
    "input_schema": {
        "type": "object",
        "properties": {},
        "required": [],
    },
})
def list_available_agents() -> Dict[str, Any]:
    """List registered agents."""
    orchestrator = _get_orch()
    agents = orchestrator.list_agents()
    return {
        "success": True,
        "count": len(agents),
        "agents": agents,
    }


@register_tool({
    "name": "run_multi_agent_workflow",
    "description": "Execute a collaborative pipeline across Planner, Worker (Coder/Researcher), and Reviewer agents.",
    "input_schema": {
        "type": "object",
        "properties": {
            "goal": {
                "type": "string",
                "description": "High-level objective or project goal to execute collaboratively.",
            },
            "workflow_type": {
                "type": "string",
                "description": "Workflow model (defaults to 'full').",
            },
        },
        "required": ["goal"],
    },
})
def run_multi_agent_workflow(goal: str, workflow_type: str = "full") -> Dict[str, Any]:
    """Execute multi-agent collaborative pipeline."""
    orchestrator = _get_orch()
    return orchestrator.run_collaborative_workflow(goal=goal, workflow_type=workflow_type)
