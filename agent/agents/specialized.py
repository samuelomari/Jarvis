"""Concrete specialized subagents for software engineering, research, planning, and review."""

from typing import Optional
from agent.agents.base import BaseAgent


class CoderAgent(BaseAgent):
    """Specialized agent for software engineering, refactoring, and code analysis."""

    def __init__(self):
        system_prompt = (
            "You are the Coder Agent, a world-class principal software engineer. "
            "Your responsibilities: write clean, idiomatic, maintainable code, implement new features, "
            "perform refactorings, debug complex errors, inspect AST symbols, and edit files safely. "
            "Always follow best practices, verify syntax, include docstrings, and handle edge cases."
        )
        allowed_tools = [
            "read_file",
            "write_file",
            "edit_file",
            "append_file",
            "delete_file",
            "copy_file",
            "move_file",
            "list_directory",
            "search_files",
            "analyze_codebase",
            "inspect_symbols",
            "create_directory",
        ]
        super().__init__(
            name="coder",
            role="Software Engineer & Architect",
            description="Designs code, writes features, fixes bugs, inspects AST structures, and edits project files.",
            system_prompt=system_prompt,
            allowed_tools=allowed_tools,
        )

    def _generate_mock_output(self, task: str, context: Optional[str]) -> str:
        return (
            f"### [Coder Agent] Implementation Analysis\n\n"
            f"- **Task:** {task}\n"
            f"- **Status:** Code reviewed and verified against project architecture.\n"
            f"- **Recommendation:** Ensure automated test coverage is updated for all modified routines."
        )


class ResearcherAgent(BaseAgent):
    """Specialized agent for web research, technical documentation lookup, and information gathering."""

    def __init__(self):
        system_prompt = (
            "You are the Researcher Agent, an expert research analyst and technical synthesizer. "
            "Your responsibilities: execute targeted web searches, extract high-signal technical content "
            "from online documentation, gather facts, verify claims with external sources, and present "
            "structured, comprehensive briefings with clear citations."
        )
        allowed_tools = [
            "search_web",
            "fetch_webpage",
            "remember",
            "recall",
            "read_file",
            "search_files",
        ]
        super().__init__(
            name="researcher",
            role="Technical Research Specialist",
            description="Searches online documentation, fetches web content, synthesizes technical briefings, and stores knowledge.",
            system_prompt=system_prompt,
            allowed_tools=allowed_tools,
        )

    def _generate_mock_output(self, task: str, context: Optional[str]) -> str:
        return (
            f"### [Researcher Agent] Briefing\n\n"
            f"- **Research Query:** {task}\n"
            f"- **Findings:** Aggregated key technical patterns and best practices.\n"
            f"- **Summary:** Reference architecture and documentation points compiled successfully."
        )


class PlannerAgent(BaseAgent):
    """Specialized agent for strategic planning, milestone definition, and task breakdown."""

    def __init__(self):
        system_prompt = (
            "You are the Planner Agent, an agile technical project manager and systems strategist. "
            "Your responsibilities: take ambitious or ambiguous goals, analyze constraints and dependencies, "
            "break them into structured, actionable phases with clear deliverables, and identify potential risks "
            "and mitigation strategies."
        )
        allowed_tools = [
            "read_file",
            "list_directory",
            "analyze_codebase",
            "recall",
            "list_calendar_events",
            "list_reminders",
        ]
        super().__init__(
            name="planner",
            role="Strategic Project Planner",
            description="Breaks complex goals into sequential milestones, manages schedules, and coordinates deliverables.",
            system_prompt=system_prompt,
            allowed_tools=allowed_tools,
        )

    def _generate_mock_output(self, task: str, context: Optional[str]) -> str:
        return (
            f"### [Planner Agent] Action Plan\n\n"
            f"**Goal:** {task}\n\n"
            f"1. **Phase 1 (Preparation):** Inspect existing requirements and environment.\n"
            f"2. **Phase 2 (Execution):** Implement changes incrementally with modular boundaries.\n"
            f"3. **Phase 3 (Verification):** Execute test suites and validate output."
        )


class ReviewerAgent(BaseAgent):
    """Specialized agent for code review, security auditing, and quality assurance."""

    def __init__(self):
        system_prompt = (
            "You are the Reviewer Agent, a senior security auditor and QA lead. "
            "Your responsibilities: rigorously examine proposed code, plans, and implementations for "
            "bugs, security vulnerabilities, edge cases, regression risks, formatting inconsistencies, "
            "and compliance with project rules."
        )
        allowed_tools = [
            "read_file",
            "search_files",
            "inspect_symbols",
            "analyze_codebase",
        ]
        super().__init__(
            name="reviewer",
            role="Quality & Security Reviewer",
            description="Audits code and documentation for correctness, edge cases, security vulnerabilities, and quality standards.",
            system_prompt=system_prompt,
            allowed_tools=allowed_tools,
        )

    def _generate_mock_output(self, task: str, context: Optional[str]) -> str:
        return (
            f"### [Reviewer Agent] Quality & Security Audit\n\n"
            f"- **Target:** {task}\n"
            f"- **Security Checklist:** Input validation verified; safe workspace boundaries enforced.\n"
            f"- **Quality Assessment:** Ready for production with all test assertions passing."
        )
