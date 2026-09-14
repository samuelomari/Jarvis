"""Unit tests for Jarvis AI Subagents and Orchestrator."""

import pytest
from agent.agents.base import BaseAgent
from agent.agents.specialized import CoderAgent, ResearcherAgent, PlannerAgent, ReviewerAgent
from agent.agents.orchestrator import AgentOrchestrator, get_orchestrator
from tools.agent_tools import delegate_task, list_available_agents, run_multi_agent_workflow


def test_specialized_agents_metadata():
    """Test specialized agent roles and tool filters."""
    coder = CoderAgent()
    assert coder.name == "coder"
    assert "Software Engineer" in coder.role
    assert "edit_file" in coder.allowed_tools
    assert "analyze_codebase" in coder.allowed_tools

    researcher = ResearcherAgent()
    assert researcher.name == "researcher"
    assert "search_web" in researcher.allowed_tools

    planner = PlannerAgent()
    assert planner.name == "planner"

    reviewer = ReviewerAgent()
    assert reviewer.name == "reviewer"


def test_agent_execution_mock():
    """Test offline/mock execution of specialized agent."""
    coder = CoderAgent()
    res = coder.execute("Refactor database adapter to use connection pooling")
    assert res["success"] is True
    assert res["agent"] == "coder"
    assert "Implementation Analysis" in res["response"] or len(res["response"]) > 0


def test_orchestrator_delegation():
    """Test orchestrator agent registration, listing, and delegation."""
    orch = AgentOrchestrator()
    agents = orch.list_agents()
    names = [a["name"] for a in agents]
    assert "coder" in names
    assert "researcher" in names
    assert "planner" in names
    assert "reviewer" in names

    # Delegate to coder
    res = orch.delegate("coder", "Implement user authentication endpoint")
    assert res["success"] is True
    assert res["agent"] == "coder"

    # Delegate to non-existent agent
    invalid = orch.delegate("unknown_agent_xyz", "Do something")
    assert invalid["success"] is False
    assert "not found" in invalid["error"]


def test_collaborative_multi_agent_workflow():
    """Test running end-to-end multi-agent pipeline."""
    orch = AgentOrchestrator()
    res = orch.run_collaborative_workflow("Build an automated backup service for project data")
    assert res["success"] is True
    assert len(res["stages"]) == 3
    assert any(s["stage"] == "plan" for s in res["stages"])
    assert any(s["stage"] == "execution" for s in res["stages"])
    assert any(s["stage"] == "review" for s in res["stages"])
    assert "Multi-Agent Collaborative Report" in res["report"]


def test_agent_tools_execution():
    """Test tool wrappers."""
    list_res = list_available_agents()
    assert list_res["success"] is True
    assert list_res["count"] >= 4

    del_res = delegate_task("researcher", "Find best practices for async FastAPI")
    assert del_res["success"] is True

    flow_res = run_multi_agent_workflow("Create data synchronization script")
    assert flow_res["success"] is True
    assert "report" in flow_res
