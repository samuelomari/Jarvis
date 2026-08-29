# JARVIS v0.1 - Personal AI Assistant

Jarvis is a personal AI assistant built with Claude, designed as an incremental development project. This is **Stage 1** - the basic working prototype.

## Architecture

```
               JARVIS v0.1
                    │
        ┌───────────┼───────────┐
        │           │           │
     Claude      Memory        Tools
     (API)       (JSON)    (Python)
        │           │           │
        └───────────┼───────────┘
                    │
              CLI Interface
```

## Project Structure

```
jarvis/
├── main.py                 # Entry point - CLI interface
├── config.py              # Configuration (model, API keys, tools)
├── SYSTEM.md              # System prompt & personality definition
│
├── agent/
│   ├── __init__.py
│   └── core.py           # Core Jarvis agent loop with tool execution
│
├── tools/
│   ├── __init__.py
│   └── basic.py          # Initial tools (get_current_time)
│
├── memory/
│   └── memory.json       # Persistent memory storage
│
├── venv/                 # Python virtual environment
├── logs/                 # Log files (empty)
├── data/                 # Data files (empty)
│
├── requirements.txt      # Python dependencies
├── .env                  # API key (gitignored)
└── .gitignore
```

## Setup

### 1. Get your API key

1. Go to [console.anthropic.com](https://console.anthropic.com/)
2. Create an account or log in
3. Navigate to the API Keys section
4. Create a new API key

### 2. Configure environment

Edit `.env`:

```
ANTHROPIC_API_KEY=your_api_key_here
```

**Never commit `.env` to git** (it's in `.gitignore`)

### 3. Activate virtual environment

```bash
cd ~/jarvis
source venv/bin/activate
```

You'll see `(venv)` at the start of your terminal prompt.

### 4. Run Jarvis

```bash
python3 main.py
```

You should see:

```
==================================================
JARVIS ONLINE
Type 'exit' to shut down.
==================================================

You:
```

### 5. Test it

Try asking:

```
What time is it?
```

Jarvis will use the `get_current_time` tool and respond with the current time.

Other things to try:

```
You: What's 2 + 2?
You: Tell me a joke.
You: What can you do?
You: exit
```

## How It Works

This is the core **agent loop**:

1. **User input** → Sent to Claude
2. **Claude processes** → Reads `SYSTEM.md`, understands available tools
3. **Claude decides** → "I need to use `get_current_time`"
4. **Tool execution** → Python runs `get_current_time()`
5. **Tool result** → Returned to Claude
6. **Claude responds** → Generates final answer
7. **Display response** → Shown to user

## Understanding the Code

### `config.py`

Defines the Claude model, API key, and available tools for the agent:

```python
MODEL = "claude-3-5-sonnet-20241022"
TOOLS = [
    {
        "name": "get_current_time",
        "description": "Get the current local date and time.",
        # ...
    }
]
```

Claude sees this tool definition and can request it when needed.

### `tools/basic.py`

Implements the actual Python functions that tools execute:

```python
def get_current_time():
    """Return the current local date and time."""
    return datetime.now().strftime(...)
```

### `agent/core.py`

The main agent loop - connects Claude to tools:

```python
response = self.client.messages.create(
    model=MODEL,
    system=self.load_system(),  # Loads SYSTEM.md
    messages=self.messages,
    tools=TOOLS  # Defines available tools
)

# If Claude wants a tool:
if response.stop_reason == "tool_use":
    result = self.run_tool(tool_name, tool_input)
    # Send result back to Claude
```

### `SYSTEM.md`

The system prompt that defines Jarvis's personality, capabilities, and rules:

```markdown
# JARVIS SYSTEM IDENTITY

You are Jarvis, a personal AI assistant...

## Operating Rules

1. Never expose API keys...
2. Ask for confirmation before important actions...
```

Claude reads this every time you chat with Jarvis.

## Capabilities & Tools (Stage 2)

Jarvis v0.2 includes the following built-in tools:

| Tool | Category | Description |
|---|---|---|
| `get_current_time` | Utility | Fetches the current local date and time. |
| `remember` | Memory | Saves facts, preferences, goals, or notes to persistent JSON storage. |
| `recall` | Memory | Searches and retrieves stored memories across categories. |
| `forget` | Memory | Deletes specific memories by index or query match. |
| `read_file` | Filesystem | Reads file contents or line slices within the project workspace. |
| `write_file` | Filesystem | Creates or safely updates files in the project workspace. |
| `list_directory` | Filesystem | Formats directory tree views with file sizes and depth controls. |
| `search_files` | Filesystem | Searches for text snippets across project workspace files. |

## CLI Commands

Inside the Jarvis interactive terminal session:
- `/help` — Display command cheat sheet
- `/memory` — Inspect all long-term memories in structured tables
- `/tools` — List registered tools and schemas
- `/clear` — Clear current conversation message history
- `/exit` — Shut down Jarvis

## Running Tests

Run the automated pytest test suite:

```bash
source venv/bin/activate
pytest tests/ -v
```

## Next Steps

We are ready for **Stage 3**:

- [x] Persistent memory system (`remember`, `recall`, `forget`)
- [x] File operations (`read_file`, `write_file`, `list_directory`, `search_files`)
- [x] Project awareness & dynamic context injection
- [ ] Skills system
- [ ] Web research
- [ ] Calendar & reminders

## Troubleshooting

### "ModuleNotFoundError: No module named 'anthropic'"

Make sure you activated the virtual environment:

```bash
source venv/bin/activate
```

You should see `(venv)` in your terminal prompt.

### "Invalid API key"

Check your `.env` file:

```bash
cat .env
```

Make sure it contains a valid key from [console.anthropic.com](https://console.anthropic.com/).

### Claude won't respond

Check that:

1. Your API key is correct
2. You have internet access
3. Your Anthropic account has credits

## Development Philosophy

This project follows an **incremental development** approach:

1. Build a working version first (this stage)
2. Understand how it works
3. Add one feature at a time
4. Test each addition
5. Only then move to the next phase

This prevents over-engineering and ensures each version is actually useful.

## File Structure Philosophy

- **`config.py`** - What the model sees (tool definitions, constants)
- **`tools/*.py`** - What Python executes (actual implementations)
- **`agent/core.py`** - The connection between the two
- **`SYSTEM.md`** - Personality & behavior (change this to customize Jarvis)

This separation means:

- You can swap models without changing tool implementations
- You can add tools without understanding the agent loop
- You can modify personality by editing one file

## Resources

- [Anthropic Claude API Docs](https://docs.anthropic.com/)
- [Claude Tool Use Guide](https://docs.anthropic.com/claude/guide/tool-use)
- [Python Anthropic SDK](https://github.com/anthropics/anthropic-sdk-python)

## License

Personal project - feel free to modify and extend.
# Jarvis
