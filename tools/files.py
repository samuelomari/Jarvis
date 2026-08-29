"""Stage 3: File reading and project analysis tools."""

import os
from pathlib import Path
from typing import Optional

from tools.registry import register_tool


@register_tool({
    "name": "list_files",
    "description": "List files and directories in a given path. Useful for exploring project structure.",
    "input_schema": {
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "Directory path to list (relative to project root)"
            },
            "depth": {
                "type": "integer",
                "description": "How many levels deep to show (default: 2)"
            }
        },
        "required": ["path"],
    },
})
def list_files(path: str, depth: int = 2) -> str:
    """List files in a directory."""
    try:
        target_path = Path(path).resolve()
        if not target_path.exists():
            return f"Path not found: {path}"
        
        if not target_path.is_dir():
            return f"Not a directory: {path}"
        
        results = []
        for i, item in enumerate(sorted(target_path.iterdir())):
            if item.name.startswith("."):
                continue
            indent = "  " * (depth - 1) if depth > 1 else ""
            if item.is_dir():
                results.append(f"{indent}📁 {item.name}/")
            else:
                results.append(f"{indent}📄 {item.name}")
            
            if i >= 20:  # Limit output
                results.append(f"... and {len(list(target_path.iterdir())) - i} more items")
                break
        
        return f"**Contents of {path}:**\n" + "\n".join(results)
    except Exception as e:
        return f"Error listing files: {str(e)}"


@register_tool({
    "name": "read_file",
    "description": "Read the contents of a file.",
    "input_schema": {
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "File path to read"
            },
            "lines": {
                "type": "string",
                "description": "Optional: line range like '1-20' or '5' for single line"
            }
        },
        "required": ["path"],
    },
})
def read_file(path: str, lines: Optional[str] = None) -> str:
    """Read file contents."""
    try:
        target_path = Path(path).resolve()
        if not target_path.exists():
            return f"File not found: {path}"
        
        if not target_path.is_file():
            return f"Not a file: {path}"
        
        with open(target_path, "r", encoding="utf-8") as f:
            content = f.read()
        
        if lines:
            # Parse line range
            try:
                if "-" in lines:
                    start, end = map(int, lines.split("-"))
                else:
                    start = end = int(lines)
                
                file_lines = content.split("\n")
                selected = file_lines[start-1:end]
                content = "\n".join(selected)
            except (ValueError, IndexError):
                pass
        
        # Limit output
        if len(content) > 5000:
            content = content[:5000] + "\n\n... (truncated)"
        
        return f"**File: {path}**\n```\n{content}\n```"
    except Exception as e:
        return f"Error reading file: {str(e)}"


@register_tool({
    "name": "search_files",
    "description": "Search for files matching a pattern in a directory.",
    "input_schema": {
        "type": "object",
        "properties": {
            "directory": {
                "type": "string",
                "description": "Directory to search in"
            },
            "pattern": {
                "type": "string",
                "description": "File name pattern to search for (e.g., '*.py' or 'README*')"
            }
        },
        "required": ["directory", "pattern"],
    },
})
def search_files(directory: str, pattern: str) -> str:
    """Search for files matching a pattern."""
    try:
        target_dir = Path(directory).resolve()
        if not target_dir.is_dir():
            return f"Directory not found: {directory}"
        
        matches = list(target_dir.glob(f"**/{pattern}"))
        
        if not matches:
            return f"No files found matching '{pattern}' in {directory}"
        
        results = [f"- {m.relative_to(target_dir)}" for m in matches[:20]]
        return f"**Found {len(matches)} files matching '{pattern}':**\n" + "\n".join(results)
    except Exception as e:
        return f"Error searching files: {str(e)}"


@register_tool({
    "name": "analyze_project",
    "description": "Analyze a project structure and provide summary.",
    "input_schema": {
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "Project directory path"
            }
        },
        "required": ["path"],
    },
})
def analyze_project(path: str) -> str:
    """Analyze project structure."""
    try:
        project_path = Path(path).resolve()
        if not project_path.is_dir():
            return f"Directory not found: {path}"
        
        # Count files by type
        file_types = {}
        total_files = 0
        
        for item in project_path.rglob("*"):
            if item.is_file() and not item.name.startswith("."):
                total_files += 1
                ext = item.suffix or "no_extension"
                file_types[ext] = file_types.get(ext, 0) + 1
        
        # Find important files
        important_files = []
        for name in ["README.md", "package.json", "requirements.txt", "setup.py", "Dockerfile"]:
            if (project_path / name).exists():
                important_files.append(name)
        
        summary = f"**Project Analysis: {path}**\n\n"
        summary += f"📊 **Total Files:** {total_files}\n\n"
        summary += "**File Types:**\n"
        for ext, count in sorted(file_types.items(), key=lambda x: x[1], reverse=True)[:10]:
            summary += f"- {ext}: {count}\n"
        
        if important_files:
            summary += f"\n**Important Files Found:**\n"
            for f in important_files:
                summary += f"- ✓ {f}\n"
        
        return summary
    except Exception as e:
        return f"Error analyzing project: {str(e)}"
