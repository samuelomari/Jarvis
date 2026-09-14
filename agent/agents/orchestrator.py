"""Orchestrator for managing, delegating to, and coordinating specialized AI subagents."""

from typing import Any, Dict, List, Optional
from agent.agents.base import BaseAgent
from agent.agents.specialized import CoderAgent, PlannerAgent, ResearcherAgent, ReviewerAgent


class AgentOrchestrator:
    """Coordinates and orchestrates specialized AI agents."""

    def __init__(self):
        self._agents: Dict[str, BaseAgent] = {}
        self._register_default_agents()

    def _register_default_agents(self) -> None:
        """Register the default suite of specialized agents."""
        self.register_agent(CoderAgent())
        self.register_agent(ResearcherAgent())
        self.register_agent(PlannerAgent())
        self.register_agent(ReviewerAgent())

    def register_agent(self, agent: BaseAgent) -> None:
        """Register an agent instance by name."""
        self._agents[agent.name.lower()] = agent

    def get_agent(self, name: str) -> Optional[BaseAgent]:
        """Retrieve an agent by name."""
        return self._agents.get(name.lower())

    def list_agents(self) -> List[Dict[str, Any]]:
        """List metadata for all registered agents."""
        return [
            {
                "name": agent.name,
                "role": agent.role,
                "description": agent.description,
                "allowed_tools_count": len(agent.allowed_tools),
                "tools": agent.allowed_tools,
            }
            for agent in self._agents.values()
        ]

    def delegate(
        self,
        agent_name: str,
        task: str,
        context: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Delegate a task to a specific subagent."""
        agent = self.get_agent(agent_name)
        if not agent:
            available = list(self._agents.keys())
            return {
                "success": False,
                "error": f"Subagent '{agent_name}' not found. Available agents: {', '.join(available)}",
            }

        return agent.execute(task=task, context=context)

    def run_collaborative_workflow(
        self,
        goal: str,
        workflow_type: str = "full",
    ) -> Dict[str, Any]:
        """
        Execute a multi-agent collaborative pipeline.
        Default pipeline:
        1. Planner: Formulates milestones and execution strategy.
        2. Worker (Coder or Researcher depending on goal): Executes implementation/research.
        3. Reviewer: Audits the resulting output and checks for issues.
        """
        stages: List[Dict[str, Any]] = []

        # Stage 1: Planning
        planner = self.get_agent("planner")
        plan_res = (
            planner.execute(f"Formulate a structured action plan for: {goal}")
            if planner
            else {"response": "Plan created."}
        )
        stages.append({"stage": "plan", "agent": "planner", "result": plan_res})

        # Determine primary worker
        goal_lower = goal.lower()
        worker_name = "researcher" if any(w in goal_lower for w in ["research", "find", "search", "learn", "compare"]) else "coder"
        worker = self.get_agent(worker_name)
        worker_context = f"Strategic Plan:\n{plan_res.get('response', '')}"

        worker_res = (
            worker.execute(f"Execute steps for: {goal}", context=worker_context)
            if worker
            else {"response": "Execution completed."}
        )
        stages.append({"stage": "execution", "agent": worker_name, "result": worker_res})

        # Stage 3: Review
        reviewer = self.get_agent("reviewer")
        review_context = f"Goal: {goal}\nExecution Result:\n{worker_res.get('response', '')}"
        review_res = (
            reviewer.execute("Review and verify the execution output for quality, bugs, and completeness", context=review_context)
            if reviewer
            else {"response": "Review completed."}
        )
        stages.append({"stage": "review", "agent": "reviewer", "result": review_res})

        summary = (
            f"# Multi-Agent Collaborative Report: {goal}\n\n"
            f"### 1. Plan ({planner.role if planner else 'Planner'})\n{plan_res.get('response', '')}\n\n"
            f"### 2. Execution ({worker.role if worker else worker_name.title()})\n{worker_res.get('response', '')}\n\n"
            f"### 3. Quality & Security Review ({reviewer.role if reviewer else 'Reviewer'})\n{review_res.get('response', '')}\n"
        )

        return {
            "success": True,
            "goal": goal,
            "workflow": workflow_type,
            "stages": stages,
            "report": summary,
        }


# Global orchestrator instance
_orchestrator = AgentOrchestrator()


def get_orchestrator() -> AgentOrchestrator:
    """Retrieve global AgentOrchestrator instance."""
    return _orchestrator
