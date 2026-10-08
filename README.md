# JARVIS - Autonomous Personal AI Worker & Assistant

Jarvis is an autonomous AI worker built with **Google Gemini** as its primary AI brain, designed to run 24/7 on a server or locally to automate workflows, manage business operations, track competitors, execute terminal commands, and communicate seamlessly via a web dashboard and Telegram mobile bridge.

---

## 🛠️ The 10-Step Hermes Agent Architecture

Jarvis implements the complete 10-step autonomous worker framework:

1. **Host 24/7 on a VPS**
   - Deploy non-stop on any Linux VPS (Hostinger, DigitalOcean, AWS, Hetzner).
   - Pre-built systemd service units (`jarvis-api.service`, `jarvis-daemon.service`) and Docker Compose configuration.
   - One-click installer: `sudo bash scripts/deploy_vps.sh`

2. **Framework & Engine**
   - Headless background daemon (`daemon.py`) and FastAPI REST / WebSocket server (`server.py`).
   - Clean permission security chokepoint and emergency brake (`/stop`).

3. **AI Brain: Google Gemini**
   - Powered natively by **Google Gemini** (`gemini-2.5-flash`, `gemini-2.5-pro`, `gemini-1.5-flash`, `gemini-1.5-pro`).
   - Full function calling, multimodal vision analysis (`analyze_screenshot`), and intelligent multi-turn agent loop.
   - Offline fallback mode supported out of the box.

4. **Structured Memory & Localized Knowledge**
   - Long-term memory store (`memory/memory.json`) for persistent user preferences, project guidelines, and operational notes.
   - Identity and safety policies codified in `SYSTEM.md`.

5. **Tool Suite**
   - **Terminal**: Shell execution, git commands, system status monitoring.
   - **Filesystem**: File reading, editing, AST analysis, tree exploration.
   - **Web & Research**: Real-time web search and webpage extraction.
   - **Vision**: Screenshot and image inspection via Gemini Vision.

6. **Telegram Mobile Bridge**
   - Control Jarvis from your phone anywhere in the world.
   - Receive push notifications, morning briefings, and autonomous mission completion alerts.
   - Run commands (`/status`, `/tasks`, `/stop`) or chat directly with your AI worker.

7. **Business & Operations Specialists**
   - **BusinessAgent**: Lead management, client qualification, outreach proposals, CRM maintenance.
   - **CompetitorTrackerAgent**: Competitor website monitoring, pricing tracking, market intelligence digests.
   - **ResearcherAgent**, **CoderAgent**, **PlannerAgent**, **ReviewerAgent**.

8. **App & Cloud Integrations**
   - **Gmail / Email**: Drafting, sending, and searching emails (`send_email`, `draft_email`).
   - **Google Calendar**: Agenda listing, scheduling events, reminders.
   - **Google Drive**: Cloud document upload, listing, and reading.
   - **CRM Pipeline**: Track prospective leads and pipeline statuses (`new`, `contacted`, `qualified`, `proposal`, `won`, `lost`).

9. **Permanent Workflows & Skills**
   - Reusable multi-agent skills defined and stored permanently in `data/workflows.json`.
   - String together tools, research, coding, and notifications into automated pipelines.

10. **Proactive Autonomous Triggers**
    - Autonomous scheduler running interval and cron missions.
    - Proactive morning briefings, calendar reminders, and automated competitor checks without waiting to be prompted.

---

## 🔒 Security Architecture (Permission Manager)

Every action flows through a strict permission boundary:

```
AI Assistant -> Permission Manager -> Approved Tool / API -> Operating System
```

- **`security/permission_manager.py`**: Classifies each tool into four permission levels (`INFORMATION`, `SAFE_AUTOMATION`, `SYSTEM_CHANGES`, `DESTRUCTIVE`). Level 0/1 run automatically; Level 2/3 require explicit confirmation.
- **`security/emergency.py`**: Global, thread-safe emergency stop. Saying *"Jarvis stop"*, *"Jarvis cancel"*, or executing `/stop` halts commands and blocks all tool executions.
- **Enforcement Point**: `tools/registry.execute_tool` gates all actions, preventing the language model from bypassing safety checks.
- **Audit Log**: Every execution is recorded in `data/command_audit.log` with credentials and secrets redacted.

---

## 🚀 Quick Start

### 1. Configure Environment (`.env`)

Copy the template:
```bash
cp .env.example .env
```

Add your Google Gemini API key:
```env
GEMINI_API_KEY=your_gemini_api_key_here
GEMINI_MODEL=gemini-2.5-flash
JARVIS_AI_PROVIDER=gemini

# Optional: Telegram mobile bridge
TELEGRAM_BOT_TOKEN=your_telegram_bot_token
TELEGRAM_CHAT_ID=your_telegram_chat_id
```

> **Note:** If `GEMINI_API_KEY` is left blank, Jarvis automatically falls back to offline mock mode for testing and local development.

### 2. Run Locally

```bash
# Start CLI Assistant
./venv/bin/python main.py

# Start Web Dashboard & API (http://localhost:8000)
./venv/bin/uvicorn server:app --host 0.0.0.0 --port 8000

# Start 24/7 Autonomous Daemon
./venv/bin/python daemon.py
```

### 3. Deploy to a 24/7 VPS Server (Hostinger / Ubuntu)

```bash
sudo bash scripts/deploy_vps.sh
```

Or using Docker:

```bash
docker compose up -d
```

---

## 💻 Interactive CLI Commands

Inside the terminal CLI (`python main.py`):
- `/help` — Display command cheat sheet
- `/memory` — Inspect all long-term memories in formatted tables
- `/tools` — List all registered tools and schemas
- `/status` — System + security status report
- `/security` — Permission model and emergency state
- `/audit` — Recent action audit log
- `/stop` — EMERGENCY STOP (halts commands and automations)
- `/resume` — Release the emergency stop
- `/serious` — Toggle strict confirmation mode
- `/dashboard` — Display web dashboard URL
- `/clear` — Clear current conversation message history
- `/exit` — Shut down Jarvis

---

## 🧪 Testing

Run the full pytest suite:

```bash
./venv/bin/pytest
```

---

## 🗺️ Roadmap Status

- [x] **Stage 1**: Core LLM Tool Agent Loop
- [x] **Stage 2**: Persistent Long-Term Memory System
- [x] **Stage 3**: File Reading & Codebase Static Analysis (AST parsing)
- [x] **Stage 4**: Live Web Search & Webpage Extractor
- [x] **Stage 5**: Calendar & Timed Reminders System
- [x] **Stage 6-9**: Cybernetic Web Dashboard UI & Always-On Daemon
- [x] **Stage 10**: Permission Manager, Emergency Stop & Audit Log
- [x] **Gemini Brain**: Google Gemini 2.5 Flash / Pro native migration
- [x] **Hermes Worker**: 10-Step Autonomous Agent Deployment & Telegram Mobile Bridge
