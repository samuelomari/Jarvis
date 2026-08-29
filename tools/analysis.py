"""Project and codebase analysis tools for Jarvis."""

import ast
import os
from pathlib import Path
from typing import Any, Dict, List, Optional
from tools.registry import register_tool

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def _resolve_safe_path(target_path: str) -> Path:
    """Resolve path and ensure it stays within the workspace root."""
    path_obj = Path(target_path)
    if not path_obj.is_absolute():
        resolved = (PROJECT_ROOT / path_obj).resolve()
    else:
        resolved = path_obj.resolve()

    try:
        resolved.relative_to(PROJECT_ROOT)
    except ValueError:
        raise PermissionError(f"Access denied: path '{target_path}' is outside project root.")
    return resolved


@register_tool({
    "name": "analyze_codebase",
    "description": "Analyze the codebase structure, file count, lines of code by language, and project architecture overview.",
    "input_schema": {
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "Directory path to analyze (defaults to '.' for project root).",
            },
        },
        "required": [],
    },
})
def analyze_codebase(path: str = ".") -> Dict[str, Any]:
    """Perform static analysis on the project workspace."""
    try:
        root = _resolve_safe_path(path)
        if not root.exists() or not root.is_dir():
            return {"success": False, "error": f"Directory not found: {path}"}

        ignore_dirs = {".git", "venv", "__pycache__", ".pytest_cache", "node_modules", "dist", "build"}
        stats = {
            "total_files": 0,
            "total_lines": 0,
            "languages": {},
            "top_files": [],
        }

        ext_map = {
            ".py": "Python",
            ".js": "JavaScript",
            ".ts": "TypeScript",
            ".html": "HTML",
            ".css": "CSS",
            ".json": "JSON",
            ".md": "Markdown",
            ".sh": "Shell",
            ".txt": "Text",
            ".ini": "Config",
            ".yml": "YAML",
            ".yaml": "YAML",
        }

        for dirpath, dirnames, filenames in os.walk(root):
            dirnames[:] = [d for d in dirnames if d not in ignore_dirs and not d.startswith(".")]

            for fname in filenames:
                if fname.startswith("."):
                    continue
                fpath = Path(dirpath) / fname
                ext = fpath.suffix.lower()
                lang = ext_map.get(ext, "Other")

                try:
                    with open(fpath, "r", encoding="utf-8", errors="ignore") as f:
                        lines = len(f.readlines())
                except Exception:
                    lines = 0

                stats["total_files"] += 1
                stats["total_lines"] += lines

                if lang not in stats["languages"]:
                    stats["languages"][lang] = {"files": 0, "lines": 0}
                stats["languages"][lang]["files"] += 1
                stats["languages"][lang]["lines"] += lines

                rel_path = str(fpath.relative_to(PROJECT_ROOT))
                stats["top_files"].append({"file": rel_path, "lines": lines, "language": lang})

        # Sort top files by lines
        stats["top_files"].sort(key=lambda x: x["lines"], reverse=True)
        stats["top_files"] = stats["top_files"][:15]

        return {
            "success": True,
            "root": str(root.relative_to(PROJECT_ROOT)) if root != PROJECT_ROOT else ".",
            "summary": {
                "total_files": stats["total_files"],
                "total_lines": stats["total_lines"],
                "languages": stats["languages"],
            },
            "largest_files": stats["top_files"],
        }
    except Exception as exc:
        return {"success": False, "error": f"Analysis failed: {str(exc)}"}


@register_tool({
    "name": "inspect_symbols",
    "description": "Parse a Python source file using AST to extract defined classes, methods, functions, and imports.",
    "input_schema": {
        "type": "object",
        "properties": {
            "file_path": {
                "type": "string",
                "description": "Path to the Python file to inspect.",
            },
        },
        "required": ["file_path"],
    },
})
def inspect_symbols(file_path: str) -> Dict[str, Any]:
    """Inspect classes and functions in a Python source file."""
    try:
        target = _resolve_safe_path(file_path)
        if not target.exists():
            return {"success": False, "error": f"File not found: {file_path}"}
        if target.suffix.lower() != ".py":
            return {"success": False, "error": "Only Python (.py) files are supported for symbol inspection."}

        with open(target, "r", encoding="utf-8") as f:
            code = f.read()

        tree = ast.parse(code, filename=str(target))

        classes = []
        functions = []
        imports = []

        for node in tree.body:
            if isinstance(node, ast.ClassDef):
                methods = [m.name for m in node.body if isinstance(m, (ast.FunctionDef, ast.AsyncFunctionDef))]
                doc = ast.get_docstring(node) or ""
                classes.append({
                    "name": node.name,
                    "methods": methods,
                    "docstring": doc.split("\n")[0] if doc else "",
                    "line": node.lineno,
                })
            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                doc = ast.get_docstring(node) or ""
                functions.append({
                    "name": node.name,
                    "args": [a.arg for a in node.args.args],
                    "docstring": doc.split("\n")[0] if doc else "",
                    "line": node.lineno,
                })
            elif isinstance(node, ast.Import):
                for n in node.names:
                    imports.append(n.name)
            elif isinstance(node, ast.ImportFrom):
                mod = node.module or ""
                for n in node.names:
                    imports.append(f"{mod}.{n.name}")

        return {
            "success": True,
            "file": str(target.relative_to(PROJECT_ROOT)),
            "classes": classes,
            "functions": functions,
            "imports": imports,
        }
    except Exception as exc:
        return {"success": False, "error": f"Symbol inspection failed: {str(exc)}"}

