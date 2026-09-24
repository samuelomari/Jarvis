"""Project registry and status summaries for the JARVIS command center."""

import json
import subprocess
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional

from config import PROJECT_ROOT

PROJECTS_FILE = PROJECT_ROOT / "data" / "projects.json"
IGNORED_DIRS = {".git", ".venv", "venv", "node_modules", "__pycache__", "data"}


def _load() -> List[Dict[str, Any]]:
    if not PROJECTS_FILE.exists():
        return []
    try:
        data = json.loads(PROJECTS_FILE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    return data if isinstance(data, list) else []


def _save(projects: List[Dict[str, Any]]) -> None:
    PROJECTS_FILE.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", dir=PROJECTS_FILE.parent, delete=False, encoding="utf-8") as tmp:
        json.dump(projects, tmp, indent=2)
        tmp.flush()
        temp_name = tmp.name
    Path(temp_name).replace(PROJECTS_FILE)


def _resolve(path: str) -> Path:
    candidate = (PROJECT_ROOT / path).resolve()
    candidate.relative_to(PROJECT_ROOT.resolve())
    return candidate


def _git_status(path: Path) -> Dict[str, Any]:
    try:
        result = subprocess.run(
            ["git", "status", "--short", "--branch"],
            cwd=path,
            capture_output=True,
            text=True,
            timeout=10,
        )
        lines = result.stdout.splitlines()
        return {
            "available": result.returncode == 0,
            "branch": lines[0].removeprefix("## ").strip() if lines else None,
            "changes": len(lines[1:]) if len(lines) > 1 else 0,
        }
    except (OSError, subprocess.SubprocessError):
        return {"available": False, "branch": None, "changes": 0}


def _project_types(path: Path) -> List[str]:
    manifests = {
        "package.json": "node",
        "pyproject.toml": "python",
        "requirements.txt": "python",
        "Cargo.toml": "rust",
        "go.mod": "go",
    }
    return sorted({kind for filename, kind in manifests.items() if (path / filename).exists()})


def summarize(path: str) -> Dict[str, Any]:
    project = _resolve(path)
    if not project.is_dir():
        return {"success": False, "error": f"Project directory does not exist: {path}"}
    relative = str(project.relative_to(PROJECT_ROOT)) or "."
    return {
        "success": True,
        "project": {
            "path": relative,
            "name": project.name or PROJECT_ROOT.name,
            "types": _project_types(project),
            "git": _git_status(project),
            "has_tests": (project / "tests").is_dir() or (project / "pytest.ini").exists(),
            "files": sorted(item.name for item in project.iterdir())[:100],
        },
    }


def list_projects() -> Dict[str, Any]:
    registered = _load()
    paths = {item.get("path", ".") for item in registered if isinstance(item, dict)}
    paths.add(".")
    for item in PROJECT_ROOT.iterdir():
        if item.is_dir() and item.name not in IGNORED_DIRS and not item.name.startswith("."):
            paths.add(item.name)

    projects = []
    for path in sorted(paths):
        try:
            result = summarize(path)
        except (OSError, ValueError):
            continue
        if result["success"]:
            projects.append(result["project"])
    return {"success": True, "count": len(projects), "projects": projects}


def register_project(name: str, path: str) -> Dict[str, Any]:
    clean_name = name.strip()
    if not clean_name:
        return {"success": False, "error": "Project name cannot be empty."}
    try:
        project = _resolve(path)
    except (OSError, ValueError) as exc:
        return {"success": False, "error": f"Invalid project path: {exc}"}
    if not project.is_dir():
        return {"success": False, "error": f"Project directory does not exist: {path}"}

    relative = str(project.relative_to(PROJECT_ROOT)) or "."
    projects = [item for item in _load() if item.get("path") != relative]
    projects.append({"name": clean_name, "path": relative})
    _save(projects)
    return {"success": True, "project": {"name": clean_name, "path": relative}}
