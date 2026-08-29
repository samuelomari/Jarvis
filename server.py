"""Jarvis Web Server & REST API backend powered by FastAPI."""

import asyncio
import os
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import psutil
import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from agent.core import Jarvis
from config import MODEL, PROJECT_ROOT
from memory.calendar_manager import CalendarManager
from memory.manager import MemoryManager
from tools.analysis import analyze_codebase
from tools.filesystem import list_directory, read_file
from tools.registry import execute_tool, get_all_tool_schemas, get_registered_tools
from tools.web_search import search_web

from contextlib import asynccontextmanager


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup and shutdown background tasks."""
    global _worker_running
    _worker_running = True
    worker_thread = threading.Thread(target=background_reminder_worker, daemon=True)
    worker_thread.start()
    yield
    _worker_running = False


# Initialize app
app = FastAPI(title="JARVIS AI Assistant System", version="0.2.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global instances
jarvis_agent = Jarvis()
memory_manager = MemoryManager()
calendar_manager = CalendarManager()
SERVER_START_TIME = time.time()
ACTIVE_TOOL_LOGS: List[Dict[str, Any]] = []

# Background Reminder Worker
_worker_running = True


def background_reminder_worker():
    """Continuously monitor and trigger pending reminders."""
    while _worker_running:
        try:
            triggered = calendar_manager.check_pending_reminders()
            for item in triggered:
                print(f"\n[ALERT] REMINDER TRIGGERED: {item.get('title')} ({item.get('remind_at')})")
        except Exception:
            pass
        time.sleep(10)


# Models
class ChatRequest(BaseModel):
    message: str


class MemoryItemRequest(BaseModel):
    category: str
    content: str


class MemoryDeleteRequest(BaseModel):
    category: str
    item_or_index: str


class CalendarEventRequest(BaseModel):
    title: str
    date: str
    time: str = "09:00"
    description: str = ""
    category: str = "general"


class ReminderRequest(BaseModel):
    title: str
    remind_at: str
    note: str = ""


class SearchRequest(BaseModel):
    query: str
    max_results: int = 5


class ReadFileRequest(BaseModel):
    path: str
    start_line: Optional[int] = None
    end_line: Optional[int] = None


# --- API Endpoints ---

@app.get("/api/health")
def health_check():
    """Health check endpoint."""
    return {"status": "online", "model": MODEL, "version": "0.2.0"}


@app.post("/api/chat")
def chat_endpoint(req: ChatRequest):
    """Handle chat messages with Jarvis and record tool activity."""
    tool_events: List[Dict[str, Any]] = []

    def on_tool(name: str, args: Dict[str, Any], result: Any):
        event = {
            "tool": name,
            "args": args,
            "result": result,
            "timestamp": datetime.now().isoformat(),
        }
        tool_events.append(event)
        ACTIVE_TOOL_LOGS.insert(0, event)
        if len(ACTIVE_TOOL_LOGS) > 100:
            ACTIVE_TOOL_LOGS.pop()

    try:
        reply = jarvis_agent.chat(req.message, on_tool_call=on_tool)
        return {
            "success": True,
            "reply": reply,
            "tool_calls": tool_events,
            "history_count": jarvis_agent.get_history_count(),
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@app.post("/api/chat/clear")
def clear_chat():
    """Clear agent conversation history."""
    jarvis_agent.clear_history()
    return {"success": True, "message": "Conversation history cleared."}


# --- Memory Endpoints ---

@app.get("/api/memory")
def get_memory():
    """Retrieve all stored memories."""
    return {"success": True, "data": memory_manager.load()}


@app.post("/api/memory")
def add_memory(req: MemoryItemRequest):
    """Store new memory item."""
    res = memory_manager.remember(category=req.category, item=req.content)
    return res


@app.delete("/api/memory")
def delete_memory(req: MemoryDeleteRequest):
    """Delete a memory item."""
    res = memory_manager.forget(category=req.category, item_or_index=req.item_or_index)
    return res


# --- Calendar & Reminders Endpoints ---

@app.get("/api/calendar/events")
def get_events(start_date: Optional[str] = None, end_date: Optional[str] = None, category: Optional[str] = None):
    """List calendar events."""
    events = calendar_manager.list_events(start_date=start_date, end_date=end_date, category=category)
    return {"success": True, "events": events}


@app.post("/api/calendar/events")
def create_event(req: CalendarEventRequest):
    """Create a new calendar event."""
    res = calendar_manager.add_event(
        title=req.title,
        date=req.date,
        time=req.time,
        description=req.description,
        category=req.category,
    )
    return res


@app.delete("/api/calendar/events/{event_id}")
def delete_event(event_id: str):
    """Delete a calendar event."""
    return calendar_manager.delete_event(event_id)


@app.get("/api/calendar/reminders")
def get_reminders(status: Optional[str] = None):
    """List reminders."""
    reminders = calendar_manager.list_reminders(status=status)
    return {"success": True, "reminders": reminders}


@app.post("/api/calendar/reminders")
def create_reminder(req: ReminderRequest):
    """Create a new reminder."""
    return calendar_manager.add_reminder(title=req.title, remind_at=req.remind_at, note=req.note)


@app.post("/api/calendar/reminders/{reminder_id}/dismiss")
def dismiss_reminder(reminder_id: str):
    """Dismiss a reminder."""
    return calendar_manager.dismiss_reminder(reminder_id)


@app.delete("/api/calendar/reminders/{reminder_id}")
def delete_reminder(reminder_id: str):
    """Delete a reminder."""
    return calendar_manager.delete_reminder(reminder_id)


# --- Project & File Endpoints ---

@app.get("/api/project/stats")
def get_project_stats():
    """Get static analysis metrics of the codebase."""
    return analyze_codebase(".")


@app.get("/api/project/tree")
def get_project_tree(path: str = ".", max_depth: int = 3):
    """Get directory tree view."""
    return list_directory(path=path, max_depth=max_depth)


@app.post("/api/project/read")
def read_project_file(req: ReadFileRequest):
    """Read file content with line boundaries."""
    return read_file(path=req.path, start_line=req.start_line, end_line=req.end_line)


# --- Web Search Endpoint ---

@app.post("/api/search")
def search_web_endpoint(req: SearchRequest):
    """Perform web search."""
    return search_web(query=req.query, max_results=req.max_results)


# --- System & Telemetry Endpoints ---

@app.get("/api/system/stats")
def get_system_stats():
    """Retrieve host machine and process telemetry."""
    try:
        cpu_pct = psutil.cpu_percent(interval=0.1)
        mem = psutil.virtual_memory()
        disk = psutil.disk_usage("/")
        uptime_secs = int(time.time() - SERVER_START_TIME)

        return {
            "success": True,
            "cpu_percent": cpu_pct,
            "memory_percent": mem.percent,
            "memory_used_mb": int(mem.used / (1024 * 1024)),
            "memory_total_mb": int(mem.total / (1024 * 1024)),
            "disk_percent": disk.percent,
            "uptime_seconds": uptime_secs,
            "model": MODEL,
            "threads": threading.active_count(),
            "recent_tool_calls": ACTIVE_TOOL_LOGS[:10],
        }
    except Exception as exc:
        return {"success": False, "error": str(exc)}


@app.get("/api/tools")
def get_tools_list():
    """List all available tools and descriptions."""
    tools = get_registered_tools()
    return {
        "success": True,
        "count": len(tools),
        "tools": [
            {"name": name, "description": data["schema"].get("description", ""), "schema": data["schema"]}
            for name, data in tools.items()
        ],
    }


# Mount Static Files & SPA route
STATIC_DIR = PROJECT_ROOT / "dashboard" / "static"
STATIC_DIR.mkdir(parents=True, exist_ok=True)

if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.get("/", response_class=HTMLResponse)
def serve_dashboard():
    """Serve the Jarvis Cyber Web Dashboard."""
    index_file = STATIC_DIR / "index.html"
    if index_file.exists():
        with open(index_file, "r", encoding="utf-8") as f:
            return f.read()
    return "<h1>Jarvis Dashboard Loading...</h1>"



if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Start Jarvis Dashboard Server")
    parser.add_argument("--host", default="0.0.0.0", help="Host address")
    parser.add_argument("--port", type=int, default=8000, help="Port number")
    args = parser.parse_args()

    print(f"\n=======================================================")
    print(f" JARVIS WEB DASHBOARD RUNNING AT: http://localhost:{args.port}")
    print(f"=======================================================\n")

    uvicorn.run("server:app", host=args.host, port=args.port, reload=False)
