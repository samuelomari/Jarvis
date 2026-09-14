"""Filesystem tools for Jarvis - read, write, list, and search files."""

import fnmatch
import os
import shutil
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
from tools.registry import register_tool

# Safe workspace root (defaults to jarvis root)
PROJECT_ROOT = Path(__file__).resolve().parent.parent


def _resolve_safe_path(target_path: Union[str, Path]) -> Path:
    """Resolve path and ensure it does not escape the project root."""
    path_obj = Path(target_path)
    if not path_obj.is_absolute():
        resolved = (PROJECT_ROOT / path_obj).resolve()
    else:
        resolved = path_obj.resolve()

    # Safety check: ensure path is within PROJECT_ROOT
    try:
        resolved.relative_to(PROJECT_ROOT)
    except ValueError:
        raise PermissionError(
            f"Access denied: path '{target_path}' is outside the project workspace root ({PROJECT_ROOT})."
        )

    return resolved


@register_tool({
    "name": "read_file",
    "description": "Read the contents of a file within the project workspace. Optionally specify start_line and end_line for specific line ranges.",
    "input_schema": {
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "Relative or absolute path to the file to read.",
            },
            "start_line": {
                "type": "integer",
                "description": "Optional starting line number (1-indexed).",
            },
            "end_line": {
                "type": "integer",
                "description": "Optional ending line number (1-indexed, inclusive).",
            },
        },
        "required": ["path"],
    },
})
def read_file(
    path: str,
    start_line: Optional[int] = None,
    end_line: Optional[int] = None,
) -> Dict[str, Any]:
    """Read a file's content or a slice of lines."""
    try:
        safe_path = _resolve_safe_path(path)
        if not safe_path.exists():
            return {"success": False, "error": f"File not found: {path}"}
        if not safe_path.is_file():
            return {"success": False, "error": f"Path is a directory, not a file: {path}"}

        with open(safe_path, "r", encoding="utf-8", errors="replace") as f:
            lines = f.readlines()

        total_lines = len(lines)
        s_line = max(1, start_line) if start_line is not None else 1
        e_line = min(total_lines, end_line) if end_line is not None else total_lines

        if s_line > total_lines:
            return {
                "success": False,
                "error": f"start_line ({s_line}) exceeds total lines ({total_lines}).",
            }

        selected_lines = lines[s_line - 1 : e_line]
        numbered_content = "".join(
            f"{i:4d} | {line}" for i, line in enumerate(selected_lines, start=s_line)
        )

        return {
            "success": True,
            "path": str(safe_path.relative_to(PROJECT_ROOT)),
            "total_lines": total_lines,
            "start_line": s_line,
            "end_line": e_line,
            "content": numbered_content,
        }
    except Exception as exc:
        return {"success": False, "error": f"Failed to read file: {str(exc)}"}


@register_tool({
    "name": "write_file",
    "description": "Create or update a file in the project workspace. Set overwrite=True if replacing an existing file.",
    "input_schema": {
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "Path of the file to create or write.",
            },
            "content": {
                "type": "string",
                "description": "Text content to write to the file.",
            },
            "overwrite": {
                "type": "boolean",
                "description": "Whether to overwrite the file if it already exists. Defaults to false.",
            },
        },
        "required": ["path", "content"],
    },
})
def write_file(
    path: str, content: str, overwrite: bool = False
) -> Dict[str, Any]:
    """Write text content to a file safely."""
    try:
        safe_path = _resolve_safe_path(path)

        if safe_path.exists() and not overwrite:
            return {
                "success": False,
                "error": f"File already exists at '{path}'. Set overwrite=True to overwrite.",
            }

        safe_path.parent.mkdir(parents=True, exist_ok=True)
        with open(safe_path, "w", encoding="utf-8") as f:
            f.write(content)

        return {
            "success": True,
            "message": f"Successfully wrote {len(content)} characters to '{path}'.",
            "path": str(safe_path.relative_to(PROJECT_ROOT)),
        }
    except Exception as exc:
        return {"success": False, "error": f"Failed to write file: {str(exc)}"}


@register_tool({
    "name": "list_directory",
    "description": "List files and directories in the workspace with hierarchical tree formatting.",
    "input_schema": {
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "Relative directory path (defaults to '.' for project root).",
            },
            "max_depth": {
                "type": "integer",
                "description": "Maximum directory recursion depth (defaults to 2).",
            },
            "show_hidden": {
                "type": "boolean",
                "description": "Whether to include hidden files and directories (default: false).",
            },
        },
        "required": [],
    },
})
def list_directory(
    path: str = ".", max_depth: int = 2, show_hidden: bool = False
) -> Dict[str, Any]:
    """List directory entries in tree view."""
    try:
        target_dir = _resolve_safe_path(path)
        if not target_dir.exists():
            return {"success": False, "error": f"Directory not found: {path}"}
        if not target_dir.is_dir():
            return {"success": False, "error": f"Path is not a directory: {path}"}

        ignore_dirs = {".git", "__pycache__", "venv", ".pytest_cache", ".ruff_cache"}
        tree_lines = []

        def build_tree(current: Path, depth: int, prefix: str = ""):
            if depth > max_depth:
                return

            try:
                entries = sorted(list(current.iterdir()), key=lambda x: (not x.is_dir(), x.name.lower()))
            except PermissionError:
                tree_lines.append(f"{prefix}[Permission Denied]")
                return

            filtered_entries = []
            for entry in entries:
                if not show_hidden and entry.name.startswith("."):
                    continue
                if entry.name in ignore_dirs:
                    continue
                filtered_entries.append(entry)

            for i, entry in enumerate(filtered_entries):
                is_last = (i == len(filtered_entries) - 1)
                connector = "└── " if is_last else "├── "
                sub_prefix = "    " if is_last else "│   "

                if entry.is_dir():
                    tree_lines.append(f"{prefix}{connector}{entry.name}/")
                    build_tree(entry, depth + 1, prefix + sub_prefix)
                else:
                    size = entry.stat().st_size
                    tree_lines.append(f"{prefix}{connector}{entry.name} ({size} B)")

        tree_lines.append(f"{target_dir.name}/")
        build_tree(target_dir, depth=1)

        return {
            "success": True,
            "directory": str(target_dir.relative_to(PROJECT_ROOT)) if target_dir != PROJECT_ROOT else ".",
            "tree": "\n".join(tree_lines),
        }
    except Exception as exc:
        return {"success": False, "error": f"Failed to list directory: {str(exc)}"}


@register_tool({
    "name": "search_files",
    "description": "Search for text occurrences or pattern matches across files in the workspace.",
    "input_schema": {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Text query or substring to search for inside files.",
            },
            "path": {
                "type": "string",
                "description": "Directory path to search within (default: '.').",
            },
            "file_pattern": {
                "type": "string",
                "description": "Glob pattern for matching filenames (e.g. '*.py', '*.md').",
            },
        },
        "required": ["query"],
    },
})
def search_files(
    query: str, path: str = ".", file_pattern: Optional[str] = None
) -> Dict[str, Any]:
    """Search for string query across files."""
    try:
        search_root = _resolve_safe_path(path)
        if not search_root.exists() or not search_root.is_dir():
            return {"success": False, "error": f"Invalid directory path: {path}"}

        ignore_dirs = {".git", "__pycache__", "venv", ".pytest_cache"}
        matches: List[Dict[str, Any]] = []
        query_lower = query.lower()
        max_matches = 50

        for root, dirs, files in os.walk(search_root):
            dirs[:] = [d for d in dirs if d not in ignore_dirs and not d.startswith(".")]

            for file_name in files:
                if file_name.startswith("."):
                    continue

                if file_pattern and not fnmatch.fnmatch(file_name, file_pattern):
                    continue

                full_path = Path(root) / file_name
                try:
                    with open(full_path, "r", encoding="utf-8", errors="ignore") as f:
                        for line_num, line in enumerate(f, start=1):
                            if query_lower in line.lower():
                                matches.append({
                                    "file": str(full_path.relative_to(PROJECT_ROOT)),
                                    "line": line_num,
                                    "snippet": line.strip()[:150],
                                })
                                if len(matches) >= max_matches:
                                    break
                except Exception:
                    continue

                if len(matches) >= max_matches:
                    break
            if len(matches) >= max_matches:
                break

        return {
            "success": True,
            "query": query,
            "match_count": len(matches),
            "matches": matches,
            "capped": len(matches) >= max_matches,
        }
    except Exception as exc:
        return {"success": False, "error": f"Failed searching files: {str(exc)}"}


@register_tool({
    "name": "edit_file",
    "description": "Surgically edit a file in the workspace by replacing target_content with replacement_content. Optionally constrain search within start_line and end_line.",
    "input_schema": {
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "Path of the file to edit.",
            },
            "target_content": {
                "type": "string",
                "description": "The exact string or lines to replace in the file.",
            },
            "replacement_content": {
                "type": "string",
                "description": "The new replacement text.",
            },
            "start_line": {
                "type": "integer",
                "description": "Optional starting line number (1-indexed) to scope the search.",
            },
            "end_line": {
                "type": "integer",
                "description": "Optional ending line number (1-indexed, inclusive) to scope the search.",
            },
        },
        "required": ["path", "target_content", "replacement_content"],
    },
})
def edit_file(
    path: str,
    target_content: str,
    replacement_content: str,
    start_line: Optional[int] = None,
    end_line: Optional[int] = None,
) -> Dict[str, Any]:
    """Replace target text in a file safely."""
    try:
        safe_path = _resolve_safe_path(path)
        if not safe_path.exists():
            return {"success": False, "error": f"File not found: {path}"}
        if not safe_path.is_file():
            return {"success": False, "error": f"Path is not a file: {path}"}

        with open(safe_path, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()

        if start_line is not None or end_line is not None:
            lines = content.splitlines(keepends=True)
            total_lines = len(lines)
            s_line = max(1, start_line) if start_line is not None else 1
            e_line = min(total_lines, end_line) if end_line is not None else total_lines

            if s_line > total_lines:
                return {"success": False, "error": f"start_line ({s_line}) exceeds total lines ({total_lines})."}

            prefix = "".join(lines[:s_line - 1])
            window = "".join(lines[s_line - 1:e_line])
            suffix = "".join(lines[e_line:])

            count = window.count(target_content)
            if count == 0:
                return {"success": False, "error": f"Target content not found within lines {s_line}-{e_line}."}
            if count > 1:
                return {"success": False, "error": f"Target content found {count} times within lines {s_line}-{e_line}. Please narrow the range or use unique target text."}

            new_window = window.replace(target_content, replacement_content, 1)
            new_content = prefix + new_window + suffix
        else:
            count = content.count(target_content)
            if count == 0:
                return {"success": False, "error": "Target content not found in file."}
            if count > 1:
                return {"success": False, "error": f"Target content found {count} times in file. Please specify start_line/end_line or provide more unique surrounding text."}

            new_content = content.replace(target_content, replacement_content, 1)

        with open(safe_path, "w", encoding="utf-8") as f:
            f.write(new_content)

        return {
            "success": True,
            "message": f"Successfully edited '{path}'.",
            "path": str(safe_path.relative_to(PROJECT_ROOT)),
        }
    except Exception as exc:
        return {"success": False, "error": f"Failed to edit file: {str(exc)}"}


@register_tool({
    "name": "append_file",
    "description": "Append text content to the end of a file in the workspace. Creates file if it does not exist.",
    "input_schema": {
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "Path of the file to append to.",
            },
            "content": {
                "type": "string",
                "description": "Text content to append.",
            },
        },
        "required": ["path", "content"],
    },
})
def append_file(path: str, content: str) -> Dict[str, Any]:
    """Append text content to a file."""
    try:
        safe_path = _resolve_safe_path(path)
        safe_path.parent.mkdir(parents=True, exist_ok=True)
        with open(safe_path, "a", encoding="utf-8") as f:
            f.write(content)
        return {
            "success": True,
            "message": f"Successfully appended {len(content)} characters to '{path}'.",
            "path": str(safe_path.relative_to(PROJECT_ROOT)),
        }
    except Exception as exc:
        return {"success": False, "error": f"Failed to append to file: {str(exc)}"}


@register_tool({
    "name": "delete_file",
    "description": "Safely delete a file in the workspace.",
    "input_schema": {
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "Path of the file to delete.",
            },
        },
        "required": ["path"],
    },
})
def delete_file(path: str) -> Dict[str, Any]:
    """Delete a file safely."""
    try:
        safe_path = _resolve_safe_path(path)
        if not safe_path.exists():
            return {"success": False, "error": f"File not found: {path}"}
        if safe_path.is_dir():
            return {"success": False, "error": f"Path is a directory, not a file: {path}"}

        # Guard critical files
        rel_str = str(safe_path.relative_to(PROJECT_ROOT))
        protected = {".env", ".gitignore", "SYSTEM.md", "README.md", "main.py", "config.py", "server.py", "daemon.py"}
        if rel_str in protected or rel_str.startswith(".git/"):
            return {"success": False, "error": f"Cannot delete protected core project file: {rel_str}"}

        safe_path.unlink()
        return {
            "success": True,
            "message": f"Successfully deleted '{path}'.",
            "path": rel_str,
        }
    except Exception as exc:
        return {"success": False, "error": f"Failed to delete file: {str(exc)}"}


@register_tool({
    "name": "copy_file",
    "description": "Copy a file from source_path to destination_path within the workspace.",
    "input_schema": {
        "type": "object",
        "properties": {
            "source_path": {"type": "string", "description": "Source file path."},
            "destination_path": {"type": "string", "description": "Destination file path."},
            "overwrite": {"type": "boolean", "description": "Whether to overwrite if destination exists (default: false)."},
        },
        "required": ["source_path", "destination_path"],
    },
})
def copy_file(source_path: str, destination_path: str, overwrite: bool = False) -> Dict[str, Any]:
    """Copy a file within the workspace."""
    try:
        src = _resolve_safe_path(source_path)
        dst = _resolve_safe_path(destination_path)
        if not src.exists() or not src.is_file():
            return {"success": False, "error": f"Source file does not exist: {source_path}"}
        if dst.exists() and not overwrite:
            return {"success": False, "error": f"Destination file already exists: {destination_path}. Set overwrite=True."}
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
        return {
            "success": True,
            "message": f"Successfully copied '{source_path}' to '{destination_path}'.",
            "source": str(src.relative_to(PROJECT_ROOT)),
            "destination": str(dst.relative_to(PROJECT_ROOT)),
        }
    except Exception as exc:
        return {"success": False, "error": f"Failed to copy file: {str(exc)}"}


@register_tool({
    "name": "move_file",
    "description": "Move or rename a file from source_path to destination_path within the workspace.",
    "input_schema": {
        "type": "object",
        "properties": {
            "source_path": {"type": "string", "description": "Source file path."},
            "destination_path": {"type": "string", "description": "Destination file path."},
            "overwrite": {"type": "boolean", "description": "Whether to overwrite if destination exists (default: false)."},
        },
        "required": ["source_path", "destination_path"],
    },
})
def move_file(source_path: str, destination_path: str, overwrite: bool = False) -> Dict[str, Any]:
    """Move or rename a file within the workspace."""
    try:
        src = _resolve_safe_path(source_path)
        dst = _resolve_safe_path(destination_path)
        if not src.exists() or not src.is_file():
            return {"success": False, "error": f"Source file does not exist: {source_path}"}
        if dst.exists() and not overwrite:
            return {"success": False, "error": f"Destination file already exists: {destination_path}. Set overwrite=True."}
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(src, dst)
        return {
            "success": True,
            "message": f"Successfully moved '{source_path}' to '{destination_path}'.",
            "source": str(src.relative_to(PROJECT_ROOT)),
            "destination": str(dst.relative_to(PROJECT_ROOT)),
        }
    except Exception as exc:
        return {"success": False, "error": f"Failed to move file: {str(exc)}"}


@register_tool({
    "name": "create_directory",
    "description": "Create a new directory (and intermediate parent directories) in the workspace.",
    "input_schema": {
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "Directory path to create."},
        },
        "required": ["path"],
    },
})
def create_directory(path: str) -> Dict[str, Any]:
    """Create a new directory."""
    try:
        target_dir = _resolve_safe_path(path)
        target_dir.mkdir(parents=True, exist_ok=True)
        return {
            "success": True,
            "message": f"Directory '{path}' is ready.",
            "path": str(target_dir.relative_to(PROJECT_ROOT)) if target_dir != PROJECT_ROOT else ".",
        }
    except Exception as exc:
        return {"success": False, "error": f"Failed to create directory: {str(exc)}"}

