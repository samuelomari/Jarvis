"""Context generator for Jarvis system prompts."""

import os
import platform
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Optional

from memory.manager import MemoryManager


def get_git_info(workspace_root: Path) -> Optional[str]:
    """Get the current git branch and latest commit info if available."""
    try:
        branch = subprocess.check_output(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            cwd=workspace_root,
            stderr=subprocess.DEVNULL,
            text=True,
        ).strip()
        commit = subprocess.check_output(
            ["git", "log", "-1", "--format=%h - %s (%cr)"],
            cwd=workspace_root,
            stderr=subprocess.DEVNULL,
            text=True,
        ).strip()
        return f"Git Branch: {branch} | Latest commit: {commit}"
    except Exception:
        return None


def build_system_prompt(
    system_file_path: Path,
    memory_manager: MemoryManager,
    workspace_root: Path,
) -> str:
    """Combine base SYSTEM.md with dynamic runtime environment context and memories."""
    base_prompt = ""
    if system_file_path.exists():
        with open(system_file_path, "r", encoding="utf-8") as f:
            base_prompt = f.read()

    now_str = datetime.now().strftime("%A, %d %B %Y %H:%M:%S")
    os_info = f"{platform.system()} {platform.release()} ({platform.machine()})"
    git_info = get_git_info(workspace_root)
    memories_summary = memory_manager.get_summary()

    context_section = [
        "\n\n## Dynamic Runtime Context",
        f"- **Current Local Time:** {now_str}",
        f"- **Operating System:** {os_info}",
        f"- **Workspace Root:** {workspace_root}",
    ]

    if git_info:
        context_section.append(f"- **Repository Info:** {git_info}")

    context_section.append("\n## Active Long-Term Memories")
    context_section.append(memories_summary)

    return base_prompt + "\n".join(context_section)

