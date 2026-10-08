# Jarvis 24/7 Autonomous Deployment Guide (10-Step Hermes Agent Architecture)

This guide documents how Jarvis implements and operates across all 10 steps of the **Hermes Agent** autonomous worker architecture, powered by **Google Gemini**.

---

## 🛠️ 10-Step Breakdown & Implementation

### 01. Get a VPS (Host the Agent 24/7)
Host Jarvis on an always-on cloud server (such as Hostinger, DigitalOcean, Hetzner, or AWS EC2).
- Jarvis includes automated systemd service units:
  - `jarvis-api.service`: Serves the REST API and web dashboard on port `8000`.
  - `jarvis-daemon.service`: Always-on autonomous worker running background missions, calendar alerts, and Telegram polling.
- Automated deployment:
  ```bash
  sudo bash scripts/deploy_vps.sh
  ```
- Or run with Docker:
  ```bash
  docker compose up -d
  ```

### 02. Install Framework
Deploy the agent code and python virtual environment:
```bash
git clone <repo-url> jarvis
cd jarvis
python3 -m venv venv
./venv/bin/pip install -r requirements.txt
```

### 03. Connect the AI Brain (Google Gemini)
Jarvis uses **Google Gemini** as its primary reasoning engine.
- Supported models: `gemini-2.5-flash`, `gemini-2.5-pro`, `gemini-1.5-flash`, `gemini-1.5-pro`.
- Set your key in `.env`:
  ```env
  GEMINI_API_KEY=your_gemini_api_key_here
  GEMINI_MODEL=gemini-2.5-flash
  JARVIS_AI_PROVIDER=gemini
  ```
- Get an API key from [Google AI Studio](https://aistudio.google.com/).

### 04. Give it Structured Memory
Jarvis stores permanent memories and contextual knowledge in:
- `memory/memory.json`: Structured facts, project guidelines, user preferences, and working state.
- `SYSTEM.md`: Core system instructions, operating rules, and permission policies.
- Tools: `remember`, `recall`, `list_memories`, `forget`.

### 05. Give it Tools
Jarvis connects the Gemini brain to software tools via permissions:
- **Terminal & Dev Tools**: `execute_bash`, `run_command`, `git_status`, `git_diff`.
- **Filesystem Tools**: `read_file`, `write_file`, `edit_file`, `search_files`, `list_directory`.
- **Web & Analysis**: `search_web`, `fetch_webpage`, `analyze_codebase`.
- **Vision Tools**: `analyze_screenshot`, `analyze_image_file` powered by Gemini Vision.

### 06. Connect Telegram (Remote Control & Phone Alerts)
Control Jarvis from anywhere and receive push notifications on your phone:
- Configure in `.env`:
  ```env
  TELEGRAM_BOT_TOKEN=your_bot_token_from_botfather
  TELEGRAM_CHAT_ID=your_chat_id
  ```
- Send commands directly to your bot: `/status`, `/tasks`, `/stop`, or any natural question.
- Jarvis dispatches reminders, mission summaries, and alerts straight to Telegram.

### 07. Define Business Responsibilities
Jarvis features specialized agents for commercial and day-to-day operations:
- **BusinessAgent**: Lead management, client qualification, and outreach proposals.
- **CompetitorTrackerAgent**: Competitor tracking, price change alerts, and market digests.
- **ResearcherAgent**: Deep documentation and online research.
- **CoderAgent**: Software engineering, refactoring, and bug fixes.
- **ReviewerAgent**: Code quality and safety verification.

### 08. Connect Your Apps (Gmail, Calendar, Drive, CRM)
Jarvis interfaces with business software suites:
- **Gmail / Email**: `send_email`, `draft_email`, `list_email_drafts`, `gmail_search_messages`.
- **Google Calendar**: `calendar_list_events`, `create_calendar_event`, `list_reminders`.
- **Google Drive**: `gdrive_list_files`, `gdrive_upload_file`, `gdrive_read_file`.
- **CRM & Pipeline**: `crm_add_lead`, `crm_list_leads`, `crm_update_lead`, `crm_get_pipeline_summary`.

### 09. Automate It (Permanent Workflows & Multi-Agent Skills)
Instruct Jarvis to save recurring tasks as permanent multi-agent skills:
- Tools: `create_workflow`, `list_workflows`, `execute_workflow`.
- Reusable workflows are saved to `data/workflows.json` and can combine multiple tools and agents.

### 10. Make it Proactive (Autonomous Triggers & Background Schedules)
Jarvis doesn't wait to be prompted:
- **Autonomous Task Scheduler**: Runs intervals (`interval:60`) or daily cron (`daily:08:00`).
- **Always-On Daemon**: Continuously evaluates pending agenda reminders, executes scheduled missions, and pushes morning briefings to your phone.

