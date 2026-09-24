"""Developer tools - git, tests, project scaffolding, Pomodoro, dependency management."""

import json
import os
import subprocess
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from tools.registry import register_tool

PROJECT_ROOT = Path(__file__).resolve().parent.parent
POMODORO_FILE = PROJECT_ROOT / "data" / "pomodoro.json"


# ── Git Tools ──────────────────────────────────────────────────────────────────

@register_tool({
    "name": "git_status",
    "description": "Show the current git status of the workspace (modified, staged, untracked files).",
    "input_schema": {"type": "object", "properties": {}, "required": []},
})
def git_status() -> Dict[str, Any]:
    """Run git status in the workspace."""
    try:
        result = subprocess.run(
            ["git", "status", "--short", "--branch"],
            cwd=str(PROJECT_ROOT), capture_output=True, text=True, timeout=10
        )
        return {
            "success": result.returncode == 0,
            "output": result.stdout or result.stderr,
        }
    except Exception as exc:
        return {"success": False, "error": str(exc)}


@register_tool({
    "name": "git_log",
    "description": "Show recent git commit history.",
    "input_schema": {
        "type": "object",
        "properties": {
            "limit": {"type": "integer", "description": "Number of commits to show (default: 10)."},
        },
        "required": [],
    },
})
def git_log(limit: int = 10) -> Dict[str, Any]:
    """Show git commit log."""
    try:
        result = subprocess.run(
            ["git", "log", f"--max-count={limit}", "--oneline", "--decorate"],
            cwd=str(PROJECT_ROOT), capture_output=True, text=True, timeout=10
        )
        return {"success": result.returncode == 0, "output": result.stdout or result.stderr}
    except Exception as exc:
        return {"success": False, "error": str(exc)}


@register_tool({
    "name": "git_diff",
    "description": "Show unstaged or staged changes in the workspace.",
    "input_schema": {
        "type": "object",
        "properties": {
            "staged": {"type": "boolean", "description": "Show staged changes (default: false = unstaged)."},
            "file_path": {"type": "string", "description": "Optional specific file path to diff."},
        },
        "required": [],
    },
})
def git_diff(staged: bool = False, file_path: Optional[str] = None) -> Dict[str, Any]:
    """Show git diff."""
    try:
        cmd = ["git", "diff"]
        if staged:
            cmd.append("--cached")
        if file_path:
            cmd.append(file_path)
        result = subprocess.run(cmd, cwd=str(PROJECT_ROOT), capture_output=True, text=True, timeout=15)
        output = result.stdout or result.stderr
        return {"success": result.returncode == 0, "output": output[:5000]}
    except Exception as exc:
        return {"success": False, "error": str(exc)}


@register_tool({
    "name": "git_commit",
    "description": "Stage all changes and create a git commit with the given message.",
    "input_schema": {
        "type": "object",
        "properties": {
            "message": {"type": "string", "description": "Commit message."},
            "add_all": {"type": "boolean", "description": "Stage all changes before committing (default: true)."},
        },
        "required": ["message"],
    },
})
def git_commit(message: str, add_all: bool = True) -> Dict[str, Any]:
    """Stage and commit changes."""
    try:
        if add_all:
            add_result = subprocess.run(
                ["git", "add", "-A"], cwd=str(PROJECT_ROOT), capture_output=True, text=True, timeout=10
            )
            if add_result.returncode != 0:
                return {"success": False, "error": f"git add failed: {add_result.stderr}"}

        commit_result = subprocess.run(
            ["git", "commit", "-m", message],
            cwd=str(PROJECT_ROOT), capture_output=True, text=True, timeout=15
        )
        return {
            "success": commit_result.returncode == 0,
            "output": commit_result.stdout or commit_result.stderr,
        }
    except Exception as exc:
        return {"success": False, "error": str(exc)}


@register_tool({
    "name": "git_push",
    "description": "Push committed changes to the remote git repository.",
    "input_schema": {
        "type": "object",
        "properties": {
            "remote": {"type": "string", "description": "Remote name (default: origin)."},
            "branch": {"type": "string", "description": "Branch name (default: current branch)."},
        },
        "required": [],
    },
})
def git_push(remote: str = "origin", branch: str = "") -> Dict[str, Any]:
    """Push to remote."""
    try:
        cmd = ["git", "push", remote]
        if branch:
            cmd.append(branch)
        result = subprocess.run(cmd, cwd=str(PROJECT_ROOT), capture_output=True, text=True, timeout=30)
        return {"success": result.returncode == 0, "output": result.stdout or result.stderr}
    except Exception as exc:
        return {"success": False, "error": str(exc)}


@register_tool({
    "name": "git_create_branch",
    "description": "Create and switch to a new git branch.",
    "input_schema": {
        "type": "object",
        "properties": {
            "branch_name": {"type": "string", "description": "Name of the new branch."},
        },
        "required": ["branch_name"],
    },
})
def git_create_branch(branch_name: str) -> Dict[str, Any]:
    """Create and checkout a new branch."""
    try:
        result = subprocess.run(
            ["git", "checkout", "-b", branch_name],
            cwd=str(PROJECT_ROOT), capture_output=True, text=True, timeout=10
        )
        return {"success": result.returncode == 0, "output": result.stdout or result.stderr}
    except Exception as exc:
        return {"success": False, "error": str(exc)}


# ── Test Runner ────────────────────────────────────────────────────────────────

@register_tool({
    "name": "run_tests",
    "description": "Run the project test suite using pytest and return results.",
    "input_schema": {
        "type": "object",
        "properties": {
            "test_path": {"type": "string", "description": "Specific test file or directory (default: tests/)."},
            "verbose": {"type": "boolean", "description": "Show verbose output (default: true)."},
            "keyword": {"type": "string", "description": "Run only tests matching this keyword (-k filter)."},
        },
        "required": [],
    },
})
def run_tests(test_path: str = "tests/", verbose: bool = True, keyword: Optional[str] = None) -> Dict[str, Any]:
    """Run pytest test suite."""
    try:
        cmd = ["python", "-m", "pytest", test_path]
        if verbose:
            cmd.append("-v")
        if keyword:
            cmd.extend(["-k", keyword])
        cmd.extend(["--tb=short", "--no-header"])

        result = subprocess.run(
            cmd, cwd=str(PROJECT_ROOT), capture_output=True, text=True, timeout=120
        )
        output = result.stdout + result.stderr
        passed = output.count(" passed")
        failed = output.count(" failed")
        errors = output.count(" error")

        return {
            "success": result.returncode == 0,
            "returncode": result.returncode,
            "output": output[:5000],
            "summary": {
                "passed": passed,
                "failed": failed,
                "errors": errors,
            },
        }
    except subprocess.TimeoutExpired:
        return {"success": False, "error": "Tests timed out after 120s."}
    except Exception as exc:
        return {"success": False, "error": str(exc)}


# ── Dependency Management ──────────────────────────────────────────────────────

@register_tool({
    "name": "install_package",
    "description": "Install a Python package using pip in the current environment.",
    "input_schema": {
        "type": "object",
        "properties": {
            "package": {"type": "string", "description": "Package name to install (e.g. 'requests', 'numpy==1.26')."},
        },
        "required": ["package"],
    },
})
def install_package(package: str) -> Dict[str, Any]:
    """Install a pip package."""
    pkg = package.strip()
    if not pkg or any(c in pkg for c in [";", "&", "|", "`", "$"]):
        return {"success": False, "error": "Invalid package name."}

    try:
        result = subprocess.run(
            ["pip", "install", pkg],
            cwd=str(PROJECT_ROOT), capture_output=True, text=True, timeout=120
        )
        return {
            "success": result.returncode == 0,
            "output": result.stdout[-2000:] or result.stderr[-1000:],
        }
    except Exception as exc:
        return {"success": False, "error": str(exc)}


@register_tool({
    "name": "list_installed_packages",
    "description": "List all installed Python packages in the current environment.",
    "input_schema": {"type": "object", "properties": {}, "required": []},
})
def list_installed_packages() -> Dict[str, Any]:
    """List pip packages."""
    try:
        result = subprocess.run(
            ["pip", "list", "--format=columns"],
            capture_output=True, text=True, timeout=15
        )
        return {"success": True, "output": result.stdout}
    except Exception as exc:
        return {"success": False, "error": str(exc)}


# ── Project Scaffolding ────────────────────────────────────────────────────────

@register_tool({
    "name": "scaffold_project",
    "description": "Create a new project directory structure with boilerplate files for a given project type.",
    "input_schema": {
        "type": "object",
        "properties": {
            "project_name": {"type": "string", "description": "Name of the new project."},
            "project_type": {
                "type": "string",
                "description": "Project type: 'python', 'node', 'react', 'fastapi', 'flask'.",
            },
            "base_path": {"type": "string", "description": "Parent directory (default: current workspace)."},
        },
        "required": ["project_name", "project_type"],
    },
})
def scaffold_project(project_name: str, project_type: str, base_path: str = ".") -> Dict[str, Any]:
    """Scaffold a new project with boilerplate."""
    name = project_name.strip().replace(" ", "_")
    ptype = project_type.strip().lower()

    base = PROJECT_ROOT / base_path if not Path(base_path).is_absolute() else Path(base_path)
    project_dir = base / name

    if project_dir.exists():
        return {"success": False, "error": f"Directory '{project_dir}' already exists."}

    templates: Dict[str, Dict[str, str]] = {
        "python": {
            "README.md": f"# {name}\n\nA Python project.\n",
            "main.py": f'"""Entry point for {name}."""\n\n\ndef main():\n    print("Hello from {name}")\n\n\nif __name__ == "__main__":\n    main()\n',
            "requirements.txt": "",
            ".gitignore": "__pycache__/\n*.pyc\n.env\nvenv/\n",
            "tests/__init__.py": "",
            "tests/test_main.py": f'"""Tests for {name}."""\n\n\ndef test_placeholder():\n    assert True\n',
        },
        "fastapi": {
            "README.md": f"# {name}\n\nA FastAPI project.\n",
            "main.py": f'"""FastAPI app for {name}."""\n\nfrom fastapi import FastAPI\n\napp = FastAPI(title="{name}")\n\n\n@app.get("/")\ndef root():\n    return {{"message": "Hello from {name}"}}\n',
            "requirements.txt": "fastapi\nuvicorn\n",
            ".gitignore": "__pycache__/\n*.pyc\n.env\nvenv/\n",
        },
        "flask": {
            "README.md": f"# {name}\n\nA Flask project.\n",
            "app.py": f'"""Flask app for {name}."""\n\nfrom flask import Flask\n\napp = Flask(__name__)\n\n\n@app.route("/")\ndef index():\n    return "Hello from {name}"\n\n\nif __name__ == "__main__":\n    app.run(debug=True)\n',
            "requirements.txt": "flask\n",
            ".gitignore": "__pycache__/\n*.pyc\n.env\nvenv/\n",
        },
        "node": {
            "README.md": f"# {name}\n\nA Node.js project.\n",
            "index.js": f'console.log("Hello from {name}");\n',
            "package.json": json.dumps({"name": name, "version": "1.0.0", "main": "index.js", "scripts": {"start": "node index.js"}}, indent=2) + "\n",
            ".gitignore": "node_modules/\n.env\n",
        },
        "react": {
            "README.md": f"# {name}\n\nA React project.\n",
            "package.json": json.dumps({"name": name, "version": "0.1.0", "private": True, "dependencies": {"react": "^18.0.0", "react-dom": "^18.0.0"}, "scripts": {"start": "react-scripts start", "build": "react-scripts build"}}, indent=2) + "\n",
            "src/App.jsx": f'export default function App() {{\n  return <h1>Hello from {name}</h1>;\n}}\n',
            "src/index.jsx": 'import React from "react";\nimport ReactDOM from "react-dom/client";\nimport App from "./App";\n\nReactDOM.createRoot(document.getElementById("root")).render(<App />);\n',
            "public/index.html": f'<!DOCTYPE html>\n<html>\n<head><title>{name}</title></head>\n<body><div id="root"></div></body>\n</html>\n',
            ".gitignore": "node_modules/\nbuild/\n.env\n",
        },
    }

    if ptype not in templates:
        return {"success": False, "error": f"Unknown project type '{ptype}'. Choose: python, fastapi, flask, node, react."}

    created_files = []
    try:
        for rel_path, content in templates[ptype].items():
            file_path = project_dir / rel_path
            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.write_text(content, encoding="utf-8")
            created_files.append(rel_path)

        return {
            "success": True,
            "message": f"Project '{name}' ({ptype}) scaffolded at {project_dir}.",
            "path": str(project_dir),
            "files_created": created_files,
        }
    except Exception as exc:
        return {"success": False, "error": f"Scaffolding failed: {str(exc)}"}


# ── Pomodoro Timer ─────────────────────────────────────────────────────────────

def _load_pomodoro() -> Dict[str, Any]:
    POMODORO_FILE.parent.mkdir(parents=True, exist_ok=True)
    if not POMODORO_FILE.exists():
        return {"sessions": [], "active": None}
    try:
        return json.loads(POMODORO_FILE.read_text())
    except Exception:
        return {"sessions": [], "active": None}


def _save_pomodoro(data: Dict[str, Any]) -> None:
    POMODORO_FILE.write_text(json.dumps(data, indent=2))


@register_tool({
    "name": "start_pomodoro",
    "description": "Start a Pomodoro focus timer session (default 25 minutes).",
    "input_schema": {
        "type": "object",
        "properties": {
            "task_name": {"type": "string", "description": "What you are focusing on."},
            "duration_minutes": {"type": "integer", "description": "Focus duration in minutes (default: 25)."},
        },
        "required": ["task_name"],
    },
})
def start_pomodoro(task_name: str, duration_minutes: int = 25) -> Dict[str, Any]:
    """Start a Pomodoro session."""
    data = _load_pomodoro()
    session = {
        "id": uuid.uuid4().hex[:8],
        "task": task_name.strip(),
        "duration_minutes": duration_minutes,
        "started_at": datetime.now().isoformat(),
        "ends_at": None,
        "status": "active",
    }
    from datetime import timedelta
    ends = datetime.now() + timedelta(minutes=duration_minutes)
    session["ends_at"] = ends.isoformat()
    data["active"] = session
    data.setdefault("sessions", []).append(session)
    _save_pomodoro(data)
    return {
        "success": True,
        "message": f"Pomodoro started: '{task_name}' for {duration_minutes} minutes. Ends at {ends.strftime('%H:%M:%S')}.",
        "session": session,
    }


@register_tool({
    "name": "check_pomodoro",
    "description": "Check the status of the current Pomodoro timer session.",
    "input_schema": {"type": "object", "properties": {}, "required": []},
})
def check_pomodoro() -> Dict[str, Any]:
    """Check active Pomodoro session."""
    data = _load_pomodoro()
    active = data.get("active")
    if not active:
        return {"success": True, "status": "no_active_session", "message": "No active Pomodoro session."}

    ends_at = datetime.fromisoformat(active["ends_at"])
    now = datetime.now()
    remaining = (ends_at - now).total_seconds()

    if remaining <= 0:
        active["status"] = "completed"
        data["active"] = None
        _save_pomodoro(data)
        return {
            "success": True,
            "status": "completed",
            "message": f"Pomodoro for '{active['task']}' is complete! Time for a break.",
            "session": active,
        }

    mins = int(remaining // 60)
    secs = int(remaining % 60)
    return {
        "success": True,
        "status": "active",
        "task": active["task"],
        "remaining": f"{mins}m {secs}s",
        "remaining_seconds": int(remaining),
        "ends_at": active["ends_at"],
    }


@register_tool({
    "name": "list_pomodoro_sessions",
    "description": "List recent Pomodoro focus sessions.",
    "input_schema": {
        "type": "object",
        "properties": {
            "limit": {"type": "integer", "description": "Number of sessions to return (default: 10)."},
        },
        "required": [],
    },
})
def list_pomodoro_sessions(limit: int = 10) -> Dict[str, Any]:
    """List Pomodoro history."""
    data = _load_pomodoro()
    sessions = data.get("sessions", [])[-limit:]
    return {"success": True, "count": len(sessions), "sessions": sessions}


# ── Dev Server Monitor ─────────────────────────────────────────────────────────

@register_tool({
    "name": "check_port",
    "description": "Check if a specific port is open/in use on localhost.",
    "input_schema": {
        "type": "object",
        "properties": {
            "port": {"type": "integer", "description": "Port number to check."},
        },
        "required": ["port"],
    },
})
def check_port(port: int) -> Dict[str, Any]:
    """Check if a port is in use."""
    import socket
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(1)
            result = s.connect_ex(("127.0.0.1", port))
            in_use = result == 0
        return {
            "success": True,
            "port": port,
            "in_use": in_use,
            "status": "open" if in_use else "closed",
            "message": f"Port {port} is {'in use (server running)' if in_use else 'free (no server)'}.",
        }
    except Exception as exc:
        return {"success": False, "error": str(exc)}


@register_tool({
    "name": "generate_code",
    "description": "Generate boilerplate code for a given language and purpose and write it to a file.",
    "input_schema": {
        "type": "object",
        "properties": {
            "language": {"type": "string", "description": "Programming language (python, javascript, typescript, bash)."},
            "purpose": {"type": "string", "description": "What the code should do (e.g. 'REST API endpoint', 'CLI argument parser')."},
            "output_file": {"type": "string", "description": "Optional file path to write the generated code."},
        },
        "required": ["language", "purpose"],
    },
})
def generate_code(language: str, purpose: str, output_file: Optional[str] = None) -> Dict[str, Any]:
    """Generate code template and optionally write to file."""
    lang = language.strip().lower()
    templates_map = {
        "python": f'"""Module: {purpose}."""\n\nfrom typing import Any\n\n\ndef main() -> None:\n    """Entry point for {purpose}."""\n    pass\n\n\nif __name__ == "__main__":\n    main()\n',
        "javascript": f'// {purpose}\n\n"use strict";\n\nfunction main() {{\n  // TODO: implement {purpose}\n}}\n\nmain();\n',
        "typescript": f'// {purpose}\n\nfunction main(): void {{\n  // TODO: implement {purpose}\n}}\n\nmain();\n',
        "bash": f'#!/usr/bin/env bash\n# {purpose}\n\nset -euo pipefail\n\nmain() {{\n  echo "Running: {purpose}"\n}}\n\nmain "$@"\n',
    }

    code = templates_map.get(lang, f"# {purpose}\n# Language: {language}\n\n# TODO: implement\n")

    result: Dict[str, Any] = {"success": True, "language": lang, "purpose": purpose, "code": code}

    if output_file:
        try:
            out_path = PROJECT_ROOT / output_file
            out_path.parent.mkdir(parents=True, exist_ok=True)
            out_path.write_text(code, encoding="utf-8")
            result["file_written"] = str(out_path.relative_to(PROJECT_ROOT))
        except Exception as exc:
            result["file_error"] = str(exc)

    return result
