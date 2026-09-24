"""Guarded developer workflow orchestration for the dashboard and chat agent."""

import json
import shlex
import subprocess
from pathlib import Path
from typing import Any, Dict, List

from config import PROJECT_ROOT


def _workspace_path(path: str) -> Path:
    """Resolve a project path without allowing it to escape the workspace."""
    candidate = (PROJECT_ROOT / path).resolve() if not Path(path).is_absolute() else Path(path).resolve()
    candidate.relative_to(PROJECT_ROOT.resolve())
    return candidate


def _run(command: List[str], cwd: Path, timeout: int = 120) -> Dict[str, Any]:
    """Run a non-shell developer command and preserve its output."""
    try:
        result = subprocess.run(
            command,
            cwd=str(cwd),
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        return {
            "success": result.returncode == 0,
            "command": shlex.join(command),
            "returncode": result.returncode,
            "output": (result.stdout + result.stderr)[-5000:],
        }
    except subprocess.TimeoutExpired:
        return {
            "success": False,
            "command": shlex.join(command),
            "error": f"Command timed out after {timeout} seconds.",
        }
    except OSError as exc:
        return {"success": False, "command": shlex.join(command), "error": str(exc)}


def prepare_project(
    path: str = ".",
    run_tests: bool = True,
    install_dependencies: bool = False,
    start_server: bool = False,
) -> Dict[str, Any]:
    """Inspect a project, optionally install dependencies, and run its tests.

    Server startup is intentionally reported as a planned action rather than
    detached from the API request; long-running processes need a dedicated
    process manager and explicit lifecycle controls.
    """
    try:
        project = _workspace_path(path)
    except (OSError, ValueError) as exc:
        return {"success": False, "error": f"Invalid project path: {exc}"}

    if not project.is_dir():
        return {"success": False, "error": f"Project directory does not exist: {path}"}

    manifests = {
        "package.json": "node",
        "requirements.txt": "python",
        "pyproject.toml": "python",
        "Pipfile": "python",
    }
    detected = [kind for filename, kind in manifests.items() if (project / filename).exists()]
    steps: List[Dict[str, Any]] = []

    steps.append({
        "name": "inspect",
        "success": True,
        "details": {
            "path": str(project.relative_to(PROJECT_ROOT)),
            "project_types": sorted(set(detected)),
            "files": sorted(item.name for item in project.iterdir())[:100],
        },
    })

    status = _run(["git", "status", "--short", "--branch"], project, timeout=15)
    status["name"] = "git_status"
    steps.append(status)

    if install_dependencies:
        if (project / "package-lock.json").exists():
            steps.append(dict(_run(["npm", "ci"], project), name="install_dependencies"))
        elif (project / "package.json").exists():
            steps.append(dict(_run(["npm", "install"], project), name="install_dependencies"))
        elif (project / "requirements.txt").exists():
            steps.append(dict(_run(["python", "-m", "pip", "install", "-r", "requirements.txt"], project), name="install_dependencies"))
        else:
            steps.append({"name": "install_dependencies", "success": False, "error": "No supported dependency manifest found."})
    else:
        steps.append({"name": "install_dependencies", "success": True, "skipped": True, "reason": "Explicit confirmation required."})

    if run_tests:
        if (project / "pytest.ini").exists() or (project / "tests").is_dir():
            steps.append(dict(_run(["python", "-m", "pytest", "-q"], project), name="tests"))
        elif (project / "package.json").exists():
            steps.append(dict(_run(["npm", "test", "--", "--runInBand"], project), name="tests"))
        else:
            steps.append({"name": "tests", "success": True, "skipped": True, "reason": "No supported test layout detected."})
    else:
        steps.append({"name": "tests", "success": True, "skipped": True, "reason": "Disabled by request."})

    if start_server:
        steps.append({
            "name": "start_server",
            "success": True,
            "planned": True,
            "reason": "Use the project-specific run command after reviewing the inspection and test results.",
        })
    else:
        steps.append({"name": "start_server", "success": True, "skipped": True, "reason": "Disabled by request."})

    failures = [step for step in steps if step.get("success") is False]
    return {
        "success": not failures,
        "project": str(project.relative_to(PROJECT_ROOT)),
        "steps": steps,
        "failed_steps": [step["name"] for step in failures],
        "message": "Developer workflow completed." if not failures else "Developer workflow found issues.",
    }
