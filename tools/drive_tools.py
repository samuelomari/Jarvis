"""Google Drive and cloud storage tools for Jarvis - list, read, upload documents."""

import json
import os
import shutil
from pathlib import Path
from typing import Any, Dict, List, Optional

from tools.registry import register_tool

PROJECT_ROOT = Path(__file__).resolve().parent.parent
GDRIVE_DIR = PROJECT_ROOT / "data" / "gdrive"


def _ensure_gdrive_dir() -> Path:
    GDRIVE_DIR.mkdir(parents=True, exist_ok=True)
    return GDRIVE_DIR


@register_tool({
    "name": "gdrive_list_files",
    "description": "List documents and spreadsheets stored in Google Drive / cloud workspace.",
    "input_schema": {
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "Optional search filter for filename or file type."},
            "limit": {"type": "integer", "description": "Maximum number of files to return."},
        },
        "required": [],
    },
})
def gdrive_list_files(query: Optional[str] = None, limit: int = 20) -> Dict[str, Any]:
    """List cloud storage files."""
    folder = _ensure_gdrive_dir()
    files = []

    for item in folder.glob("*"):
        if item.is_file():
            if query and query.lower() not in item.name.lower():
                continue
            files.append({
                "name": item.name,
                "size_bytes": item.stat().st_size,
                "path": str(item),
            })
            if len(files) >= limit:
                break

    return {
        "success": True,
        "count": len(files),
        "files": files,
        "storage_root": str(folder),
    }


@register_tool({
    "name": "gdrive_upload_file",
    "description": "Upload or sync a local file into Google Drive / cloud storage.",
    "input_schema": {
        "type": "object",
        "properties": {
            "source_path": {"type": "string", "description": "Local file path to upload."},
            "destination_name": {"type": "string", "description": "Optional custom name in drive."},
        },
        "required": ["source_path"],
    },
})
def gdrive_upload_file(source_path: str, destination_name: Optional[str] = None) -> Dict[str, Any]:
    """Upload or copy a file into cloud storage."""
    src = Path(source_path).expanduser().resolve()
    if not src.is_file():
        return {"success": False, "error": f"Source file does not exist: {source_path}"}

    dest_folder = _ensure_gdrive_dir()
    dest_filename = destination_name or src.name
    dest = dest_folder / dest_filename

    shutil.copy2(src, dest)
    return {
        "success": True,
        "message": f"File '{dest_filename}' uploaded to cloud storage successfully.",
        "cloud_path": str(dest),
        "size_bytes": dest.stat().st_size,
    }


@register_tool({
    "name": "gdrive_read_file",
    "description": "Read text or document contents stored in Google Drive.",
    "input_schema": {
        "type": "object",
        "properties": {
            "filename": {"type": "string", "description": "Name of the file to read from drive."},
        },
        "required": ["filename"],
    },
})
def gdrive_read_file(filename: str) -> Dict[str, Any]:
    """Read a document from cloud storage."""
    folder = _ensure_gdrive_dir()
    target = folder / filename

    if not target.is_file():
        # Case-insensitive search
        matches = [f for f in folder.glob("*") if f.name.lower() == filename.lower()]
        if matches:
            target = matches[0]
        else:
            return {"success": False, "error": f"File '{filename}' not found in Google Drive folder."}

    try:
        content = target.read_text(encoding="utf-8")
        return {"success": True, "filename": target.name, "content": content}
    except Exception as exc:
        return {"success": False, "error": f"Failed to read file: {str(exc)}"}

