"""Advanced file management tools for JARVIS.

Supports moving files to trash/recycle bin, finding large files,
finding duplicate files by hash, and organizing files by type/date.
"""

import hashlib
import os
from pathlib import Path
import shutil
from typing import Any, Dict, List, Optional

from tools.registry import register_tool

PROJECT_ROOT = Path(__file__).resolve().parent.parent
TRASH_DIR = PROJECT_ROOT / "data" / "trash"


def _safe_resolve(path_str: str) -> Path:
    p = Path(path_str)
    if not p.is_absolute():
        p = (PROJECT_ROOT / p).resolve()
    else:
        p = p.resolve()
    return p


@register_tool({
    "name": "trash_file",
    "description": "Safely move a file to the recycle bin / trash folder instead of permanent deletion.",
    "input_schema": {
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "Path to the file to move to trash."},
        },
        "required": ["path"],
    },
})
def trash_file(path: str) -> Dict[str, Any]:
    """Move file to system trash or local project trash."""
    target = _safe_resolve(path)
    if not target.exists():
        return {"success": False, "error": f"File not found: {path}"}

    # Try gio trash (standard Linux GNOME/FreeDesktop trash)
    if shutil.which("gio"):
        try:
            res = shutil.os.system(f"gio trash '{target}' >/dev/null 2>&1")
            if res == 0:
                return {
                    "success": True,
                    "target": str(target),
                    "destination": "System Trash (FreeDesktop / gio)",
                    "message": f"Successfully moved '{target.name}' to system recycle bin.",
                }
        except Exception:
            pass

    # Fallback to local project trash
    TRASH_DIR.mkdir(parents=True, exist_ok=True)
    trash_dest = TRASH_DIR / target.name
    counter = 1
    while trash_dest.exists():
        trash_dest = TRASH_DIR / f"{target.stem}_{counter}{target.suffix}"
        counter += 1

    try:
        shutil.move(str(target), str(trash_dest))
        return {
            "success": True,
            "target": str(target),
            "destination": str(trash_dest.relative_to(PROJECT_ROOT)),
            "message": f"Moved '{target.name}' to project trash at {trash_dest.relative_to(PROJECT_ROOT)}.",
        }
    except Exception as exc:
        return {"success": False, "error": f"Failed to move file to trash: {str(exc)}"}


@register_tool({
    "name": "find_large_files",
    "description": "Find files larger than a specified size in megabytes within a directory.",
    "input_schema": {
        "type": "object",
        "properties": {
            "directory": {"type": "string", "description": "Directory to search (default: workspace root)."},
            "min_size_mb": {"type": "number", "description": "Minimum file size in megabytes (default: 50.0)."},
            "limit": {"type": "integer", "description": "Maximum number of results to return (default: 20)."},
        },
        "required": [],
    },
})
def find_large_files(directory: str = ".", min_size_mb: float = 50.0, limit: int = 20) -> Dict[str, Any]:
    """Scan directory for files larger than threshold."""
    search_dir = _safe_resolve(directory)
    if not search_dir.exists() or not search_dir.is_dir():
        return {"success": False, "error": f"Invalid directory: {directory}"}

    min_bytes = int(min_size_mb * 1024 * 1024)
    large_files = []

    try:
        for root, dirs, files in os.walk(search_dir):
            # Skip hidden and cache dirs
            dirs[:] = [d for d in dirs if not d.startswith(".") and d not in ("node_modules", "venv", ".venv")]
            for file in files:
                filepath = Path(root) / file
                try:
                    size = filepath.stat().st_size
                    if size >= min_bytes:
                        size_mb = round(size / (1024 * 1024), 2)
                        rel_path = str(filepath.relative_to(PROJECT_ROOT)) if filepath.is_relative_to(PROJECT_ROOT) else str(filepath)
                        large_files.append({
                            "path": rel_path,
                            "size_mb": size_mb,
                            "size_bytes": size,
                        })
                except (OSError, PermissionError):
                    continue

        large_files.sort(key=lambda x: x["size_bytes"], reverse=True)
        return {
            "success": True,
            "directory": str(search_dir),
            "min_size_mb": min_size_mb,
            "count": len(large_files[:limit]),
            "files": large_files[:limit],
        }
    except Exception as exc:
        return {"success": False, "error": f"Failed scanning large files: {str(exc)}"}


@register_tool({
    "name": "find_duplicate_files",
    "description": "Find duplicate files in a directory by comparing MD5 hashes of file contents.",
    "input_schema": {
        "type": "object",
        "properties": {
            "directory": {"type": "string", "description": "Directory to scan for duplicates."},
            "limit": {"type": "integer", "description": "Max duplicate sets to return (default: 10)."},
        },
        "required": [],
    },
})
def find_duplicate_files(directory: str = ".", limit: int = 10) -> Dict[str, Any]:
    """Find identical files by hash."""
    search_dir = _safe_resolve(directory)
    if not search_dir.exists() or not search_dir.is_dir():
        return {"success": False, "error": f"Invalid directory: {directory}"}

    hashes: Dict[str, List[str]] = {}

    try:
        for root, dirs, files in os.walk(search_dir):
            dirs[:] = [d for d in dirs if not d.startswith(".") and d not in ("node_modules", "venv", ".venv")]
            for file in files:
                filepath = Path(root) / file
                try:
                    if filepath.is_file() and filepath.stat().st_size > 0:
                        hasher = hashlib.md5()
                        with open(filepath, "rb") as f:
                            for chunk in iter(lambda: f.read(65536), b""):
                                hasher.update(chunk)
                        digest = hasher.hexdigest()
                        rel_p = str(filepath.relative_to(PROJECT_ROOT)) if filepath.is_relative_to(PROJECT_ROOT) else str(filepath)
                        hashes.setdefault(digest, []).append(rel_p)
                except (OSError, PermissionError):
                    continue

        duplicates = [{"hash": h, "files": file_list} for h, file_list in hashes.items() if len(file_list) > 1]
        return {
            "success": True,
            "directory": str(search_dir),
            "duplicate_groups_found": len(duplicates),
            "duplicates": duplicates[:limit],
        }
    except Exception as exc:
        return {"success": False, "error": f"Failed detecting duplicates: {str(exc)}"}


@register_tool({
    "name": "organize_folder",
    "description": "Organize files in a folder into subdirectories based on their file extension (e.g. documents, images, code).",
    "input_schema": {
        "type": "object",
        "properties": {
            "directory": {"type": "string", "description": "Folder path to organize."},
        },
        "required": ["directory"],
    },
})
def organize_folder(directory: str) -> Dict[str, Any]:
    """Categorize loose files in a folder by extension."""
    target_dir = _safe_resolve(directory)
    if not target_dir.exists() or not target_dir.is_dir():
        return {"success": False, "error": f"Invalid folder: {directory}"}

    CATEGORIES = {
        "Documents": [".pdf", ".docx", ".doc", ".txt", ".md", ".csv", ".xlsx"],
        "Images": [".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg"],
        "Audio_Video": [".mp3", ".wav", ".mp4", ".mkv", ".mov"],
        "Archives": [".zip", ".tar", ".gz", ".7z", ".rar"],
        "Code": [".py", ".js", ".ts", ".html", ".css", ".json", ".sh"],
    }

    moved_count = 0
    details = []

    try:
        for item in list(target_dir.iterdir()):
            if item.is_file() and not item.name.startswith("."):
                ext = item.suffix.lower()
                dest_subfolder = "Other"
                for category, extensions in CATEGORIES.items():
                    if ext in extensions:
                        dest_subfolder = category
                        break

                cat_dir = target_dir / dest_subfolder
                cat_dir.mkdir(exist_ok=True)
                dest_path = cat_dir / item.name
                shutil.move(str(item), str(dest_path))
                moved_count += 1
                details.append(f"{item.name} -> {dest_subfolder}/")

        return {
            "success": True,
            "directory": str(target_dir),
            "files_organized": moved_count,
            "actions": details,
        }
    except Exception as exc:
        return {"success": False, "error": f"Failed organizing folder: {str(exc)}"}
