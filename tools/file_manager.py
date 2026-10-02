"""File manager - find files, locate large files, detect duplicates, organize folders.

Deletions are routed through the system recycle bin (``gio trash`` or
``trash-put``); permanent deletion is never performed by these tools.
Scans are restricted to the workspace or the user's home directory and never
enter system directories.
"""

import fnmatch
import hashlib
import os
import shutil
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional

from tools.registry import register_tool

PROJECT_ROOT = Path(__file__).resolve().parent.parent
HOME_DIR = Path.home()

BLOCKED_ROOTS = (
    Path("/etc"), Path("/usr"), Path("/bin"), Path("/sbin"), Path("/var"),
    Path("/boot"), Path("/sys"), Path("/proc"), Path("/dev"), Path("/root"),
)

SKIP_DIRS = {".git", ".venv", "venv", "__pycache__", ".pytest_cache", "node_modules", ".cache"}


def _resolve_scan_root(path: str) -> Path:
    """Resolve a scan root, allowing only the workspace or the user's home."""
    candidate = Path(path)
    if not candidate.is_absolute():
        candidate = PROJECT_ROOT / candidate
    candidate = candidate.expanduser().resolve()

    for blocked in BLOCKED_ROOTS:
        try:
            candidate.relative_to(blocked)
            raise PermissionError(f"Access to system directory '{blocked}' is denied.")
        except ValueError:
            continue

    allowed = False
    for base in (PROJECT_ROOT.resolve(), HOME_DIR.resolve()):
        try:
            candidate.relative_to(base)
            allowed = True
            break
        except ValueError:
            continue
    if not allowed:
        raise PermissionError(f"Path '{candidate}' is outside the workspace and home directory.")
    if not candidate.is_dir():
        raise NotADirectoryError(f"Not a directory: {candidate}")
    return candidate


def _walk(root: Path, max_files: int = 20000):
    """Yield files under root, skipping noisy directories."""
    count = 0
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS and not d.startswith(".git")]
        for name in filenames:
            yield Path(dirpath) / name
            count += 1
            if count >= max_files:
                return


@register_tool({
    "name": "find_files",
    "description": "Find files by name pattern (glob) and optional extensions within the workspace or home directory.",
    "input_schema": {
        "type": "object",
        "properties": {
            "name_pattern": {"type": "string", "description": "Glob pattern for the filename (e.g. '*.py', 'assignment*')."},
            "path": {"type": "string", "description": "Directory to search (default: workspace root)."},
            "extensions": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Optional list of extensions to include (e.g. ['.py', '.js']).",
            },
            "limit": {"type": "integer", "description": "Maximum results (default: 100)."},
        },
        "required": ["name_pattern"],
    },
})
def find_files(
    name_pattern: str,
    path: str = ".",
    extensions: Optional[List[str]] = None,
    limit: int = 100,
) -> Dict[str, Any]:
    """Find files matching a glob pattern."""
    try:
        root = _resolve_scan_root(path)
        matches: List[Dict[str, Any]] = []
        for file_path in _walk(root):
            if not fnmatch.fnmatch(file_path.name, name_pattern):
                continue
            if extensions and file_path.suffix.lower() not in {e.lower() for e in extensions}:
                continue
            try:
                size = file_path.stat().st_size
            except OSError:
                continue
            matches.append({"path": str(file_path), "size_bytes": size})
            if len(matches) >= limit:
                break
        return {"success": True, "root": str(root), "count": len(matches), "matches": matches}
    except Exception as exc:
        return {"success": False, "error": str(exc)}


@register_tool({
    "name": "find_large_files",
    "description": "Find files larger than a size threshold (in MB) within the workspace or home directory.",
    "input_schema": {
        "type": "object",
        "properties": {
            "min_size_mb": {"type": "number", "description": "Minimum size in megabytes (default: 100)."},
            "path": {"type": "string", "description": "Directory to search (default: workspace root)."},
            "limit": {"type": "integer", "description": "Maximum results (default: 50)."},
        },
        "required": [],
    },
})
def find_large_files(min_size_mb: float = 100.0, path: str = ".", limit: int = 50) -> Dict[str, Any]:
    """Find files exceeding the size threshold."""
    try:
        root = _resolve_scan_root(path)
        threshold = float(min_size_mb) * 1024 * 1024
        results: List[Dict[str, Any]] = []
        for file_path in _walk(root):
            try:
                size = file_path.stat().st_size
            except OSError:
                continue
            if size >= threshold:
                results.append({"path": str(file_path), "size_mb": round(size / (1024 * 1024), 2)})
        results.sort(key=lambda item: item["size_mb"], reverse=True)
        return {
            "success": True,
            "root": str(root),
            "threshold_mb": min_size_mb,
            "count": len(results[:limit]),
            "files": results[:limit],
        }
    except Exception as exc:
        return {"success": False, "error": str(exc)}


@register_tool({
    "name": "find_duplicate_files",
    "description": "Detect duplicate files (identical content) within the workspace or home directory using size then hash comparison.",
    "input_schema": {
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "Directory to search (default: workspace root)."},
            "min_size_kb": {"type": "number", "description": "Ignore files smaller than this (default: 1 KB)."},
            "limit": {"type": "integer", "description": "Maximum duplicate groups to return (default: 50)."},
        },
        "required": [],
    },
})
def find_duplicate_files(path: str = ".", min_size_kb: float = 1.0, limit: int = 50) -> Dict[str, Any]:
    """Find groups of files with identical content."""
    try:
        root = _resolve_scan_root(path)
        min_size = float(min_size_kb) * 1024

        by_size: Dict[int, List[Path]] = {}
        for file_path in _walk(root):
            try:
                size = file_path.stat().st_size
            except OSError:
                continue
            if size < min_size:
                continue
            by_size.setdefault(size, []).append(file_path)

        groups: List[Dict[str, Any]] = []
        wasted = 0
        for size, files in by_size.items():
            if len(files) < 2:
                continue
            by_hash: Dict[str, List[Path]] = {}
            for file_path in files:
                try:
                    digest = hashlib.md5(file_path.read_bytes()[: 4 * 1024 * 1024]).hexdigest()
                except OSError:
                    continue
                by_hash.setdefault(digest, []).append(file_path)
            for digest, dupes in by_hash.items():
                if len(dupes) >= 2:
                    groups.append({
                        "hash": digest,
                        "size_bytes": size,
                        "count": len(dupes),
                        "files": [str(p) for p in dupes],
                    })
                    wasted += size * (len(dupes) - 1)
            if len(groups) >= limit:
                break

        return {
            "success": True,
            "root": str(root),
            "duplicate_groups": len(groups),
            "wasted_bytes": wasted,
            "groups": groups[:limit],
        }
    except Exception as exc:
        return {"success": False, "error": str(exc)}


@register_tool({
    "name": "organize_directory",
    "description": "Plan (dry run by default) or perform moving files in a directory into subfolders grouped by extension.",
    "input_schema": {
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "Directory to organize (default: workspace root)."},
            "dry_run": {"type": "boolean", "description": "When true (default) only the plan is returned; set false to move files."},
            "confirmed": {"type": "boolean", "description": "Must be true when dry_run is false."},
        },
        "required": ["path"],
    },
})
def organize_directory(path: str, dry_run: bool = True, confirmed: bool = False) -> Dict[str, Any]:
    """Organize files into subfolders by extension."""
    if not dry_run and not confirmed:
        return {
            "success": False,
            "needs_confirmation": True,
            "error": "Moving files requires confirmation (confirmed=true).",
        }
    try:
        root = _resolve_scan_root(path)
        plan: List[Dict[str, str]] = []
        for entry in sorted(root.iterdir()):
            if not entry.is_file() or entry.name.startswith("."):
                continue
            folder = entry.suffix.lstrip(".").lower() or "misc"
            plan.append({"file": entry.name, "destination": f"{folder}/{entry.name}"})

        if dry_run:
            return {"success": True, "dry_run": True, "root": str(root), "planned_moves": len(plan), "plan": plan}

        moved = 0
        for item in plan:
            destination = root / item["destination"]
            destination.parent.mkdir(parents=True, exist_ok=True)
            if destination.exists():
                continue
            shutil.move(str(root / item["file"]), str(destination))
            moved += 1
        return {"success": True, "dry_run": False, "root": str(root), "moved": moved, "plan": plan}
    except Exception as exc:
        return {"success": False, "error": str(exc)}


@register_tool({
    "name": "move_to_trash",
    "description": "Move a file or folder to the system recycle bin (never permanently deletes). Requires explicit confirmation.",
    "input_schema": {
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "Path of the file or folder to move to the recycle bin."},
            "confirmed": {"type": "boolean", "description": "Must be true to confirm the move."},
        },
        "required": ["path"],
    },
})
def move_to_trash(path: str, confirmed: bool = False) -> Dict[str, Any]:
    """Move a path to the recycle bin after confirmation."""
    if not confirmed:
        return {
            "success": False,
            "needs_confirmation": True,
            "error": f"Moving '{path}' to the recycle bin requires explicit confirmation.",
        }
    try:
        candidate = Path(path)
        if not candidate.is_absolute():
            candidate = PROJECT_ROOT / candidate
        candidate = candidate.resolve()
        if not candidate.exists():
            return {"success": False, "error": f"Path not found: {path}"}

        if shutil.which("gio"):
            proc = subprocess.run(["gio", "trash", str(candidate)], capture_output=True, text=True, timeout=10)
            if proc.returncode == 0:
                return {"success": True, "message": f"Moved '{path}' to the recycle bin.", "backend": "gio"}
        if shutil.which("trash-put"):
            proc = subprocess.run(["trash-put", str(candidate)], capture_output=True, text=True, timeout=10)
            if proc.returncode == 0:
                return {"success": True, "message": f"Moved '{path}' to the recycle bin.", "backend": "trash-put"}

        return {
            "success": False,
            "error": "No recycle-bin tool found (install gio or trash-cli). Refusing to permanently delete.",
        }
    except Exception as exc:
        return {"success": False, "error": str(exc)}

