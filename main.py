"""Jarvis CLI - Interactive CLI interface with Rich formatting and tool monitoring."""

import sys
from pathlib import Path

try:
    from rich.console import Console
    from rich.markdown import Markdown
    from rich.panel import Panel
    from rich.table import Table
    from rich.theme import Theme

    custom_theme = Theme({
        "info": "dim cyan",
        "warning": "magenta",
        "danger": "bold red",
        "tool": "bold yellow",
        "jarvis": "bold cyan",
        "user": "bold green",
    })
    console = Console(theme=custom_theme)
    HAS_RICH = True
except ImportError:
    HAS_RICH = False
    console = None

from agent.core import Jarvis
from config import MODEL
from security import get_emergency_stop, get_permission_manager
from tools.registry import execute_tool, get_registered_tools


def print_banner():
    """Print welcoming startup banner."""
    if HAS_RICH:
        banner_text = (
            f"[bold cyan]JARVIS v0.2[/bold cyan] — Personal AI Assistant\n"
            f"[dim]Model: {MODEL} | Type [bold]/help[/bold] for commands[/dim]"
        )
        console.print(
            Panel(banner_text, title=" SYSTEM ONLINE", border_style="cyan")
        )
    else:
        print("=" * 60)
        print(f"JARVIS v0.2 ONLINE (Model: {MODEL})")
        print("Commands: /help, /memory, /tools, /clear, /exit")
        print("=" * 60)


def print_help():
    """Display available CLI slash commands and capabilities."""
    if HAS_RICH:
        table = Table(title="Jarvis CLI Commands", border_style="dim cyan")
        table.add_column("Command", style="bold green")
        table.add_column("Description", style="white")
        table.add_row("/help", "Show this help table")
        table.add_row("/agents", "List specialized AI subagents (Coder, Researcher, Planner, Reviewer)")
        table.add_row("/autonomous", "Inspect scheduled background missions")
        table.add_row("/notifications", "View notifications and alerts")
        table.add_row("/memory", "Inspect all long-term memories")
        table.add_row("/tools", "List all registered tools and descriptions")
        table.add_row("/status", "System + security status report")
        table.add_row("/security", "Show permission model and emergency state")
        table.add_row("/audit", "Show the recent action audit log")
        table.add_row("/stop", "EMERGENCY STOP - halt all commands and automations")
        table.add_row("/resume", "Release the emergency stop")
        table.add_row("/serious", "Toggle serious mode (confirm every change)")
        table.add_row("/dashboard", "Launch or display the Cyber Web Dashboard")
        table.add_row("/clear", "Reset conversation history")
        table.add_row("/exit, exit", "Exit the assistant session")
        console.print(table)
    else:
        print("\nCommands:")
        print("  /help          - Show help")
        print("  /agents        - View specialized AI subagents")
        print("  /autonomous    - View scheduled autonomous missions")
        print("  /notifications - View alerts and notifications")
        print("  /memory        - View long-term memory")
        print("  /tools         - List registered tools")
        print("  /status        - System + security status")
        print("  /security      - Permission model & emergency state")
        print("  /audit         - Recent action audit log")
        print("  /stop          - EMERGENCY STOP")
        print("  /resume        - Release emergency stop")
        print("  /serious       - Toggle serious mode")
        print("  /clear         - Clear conversation history")
        print("  /exit          - Quit\n")


def print_tools():
    """Display all registered tools and their descriptions."""
    tools = get_registered_tools()
    if HAS_RICH:
        table = Table(title=f"Registered Tools ({len(tools)})", border_style="yellow")
        table.add_column("Tool Name", style="bold yellow")
        table.add_column("Description", style="white")
        for name, item in sorted(tools.items()):
            table.add_row(name, item["schema"].get("description", ""))
        console.print(table)
    else:
        print("\nRegistered Tools:")
        for name, item in sorted(tools.items()):
            print(f"  - {name}: {item['schema'].get('description', '')}")
        print()


def print_memory(jarvis: Jarvis):
    """Display persistent long-term memories."""
    data = jarvis.memory_manager.load()
    total_items = sum(len(v) for v in data.values())

    if HAS_RICH:
        if total_items == 0:
            console.print("[dim italic]No active memories stored yet. Tell Jarvis to remember something![/dim italic]")
            return

        for category, items in data.items():
            if not items:
                continue
            cat_name = category.replace("_", " ").title()
            table = Table(title=f"Category: {cat_name}", border_style="blue")
            table.add_column("#", style="dim", width=4)
            table.add_column("Memory Item", style="white")
            for idx, item in enumerate(items, start=1):
                table.add_row(str(idx), str(item))
            console.print(table)
    else:
        print("\nStored Memories:")
        if total_items == 0:
            print("  (Empty memory)")
        for category, items in data.items():
            if items:
                print(f"  [{category.upper()}]:")
                for idx, item in enumerate(items, 1):
                    print(f"    {idx}. {item}")
        print()


def print_agents():
    """Display available AI Subagents."""
    from agent.agents.orchestrator import get_orchestrator
    agents = get_orchestrator().list_agents()
    if HAS_RICH:
        table = Table(title=f"Specialized AI Subagents ({len(agents)})", border_style="bold magenta")
        table.add_column("Agent", style="bold magenta")
        table.add_column("Role", style="bold cyan")
        table.add_column("Description", style="white")
        for a in agents:
            table.add_row(a["name"], a["role"], a["description"])
        console.print(table)
    else:
        print("\nSpecialized AI Subagents:")
        for a in agents:
            print(f"  - {a['name']} ({a['role']}): {a['description']}")
        print()


def print_autonomous():
    """Display scheduled autonomous missions."""
    from autonomous.scheduler import get_scheduler
    tasks = get_scheduler().list_tasks()
    if HAS_RICH:
        table = Table(title=f"Scheduled Autonomous Missions ({len(tasks)})", border_style="bold green")
        table.add_column("ID", style="dim", width=12)
        table.add_column("Name", style="bold white")
        table.add_column("Type", style="cyan")
        table.add_column("Next Run", style="yellow")
        table.add_column("Runs", style="green", justify="right")
        for t in tasks:
            table.add_row(t["id"], t["name"], t["schedule_type"], str(t.get("next_run", "N/A"))[:19], str(t.get("run_count", 0)))
        console.print(table)
    else:
        print("\nScheduled Autonomous Missions:")
        for t in tasks:
            print(f"  [{t['id']}] {t['name']} ({t['schedule_type']}) - Next: {t.get('next_run', 'N/A')}")
        print()


def print_notifications():
    """Display recent notifications."""
    from notifications.manager import get_notification_manager
    mgr = get_notification_manager()
    items = mgr.list_notifications(limit=10)
    unread = mgr.get_unread_count()
    if HAS_RICH:
        table = Table(title=f"Recent Notifications ({len(items)}, {unread} unread)", border_style="bold yellow")
        table.add_column("Time", style="dim", width=19)
        table.add_column("Level", style="cyan", width=8)
        table.add_column("Title", style="bold white")
        table.add_column("Message", style="dim white")
        for n in items:
            table.add_row(n["timestamp"][:19], n["level"].upper(), n["title"], n["message"][:60])
        console.print(table)
    else:
        print(f"\nRecent Notifications ({unread} unread):")
        for n in items:
            print(f"  [{n['timestamp'][:19]}] [{n['level'].upper()}] {n['title']}: {n['message'][:60]}")
        print()


def print_security():
    """Display the active permission model and emergency state."""
    pm = get_permission_manager()
    emergency = get_emergency_stop()
    status = {
        "Auto-confirm level": f"LEVEL {pm.auto_confirm_level} ({['INFORMATION', 'SAFE_AUTOMATION', 'SYSTEM_CHANGE', 'DESTRUCTIVE'][pm.auto_confirm_level]})",
        "Serious mode": "ON" if pm.serious_mode else "OFF",
        "Emergency stop": "ENGAGED" if emergency.is_engaged else "released",
    }
    if HAS_RICH:
        table = Table(title="Security & Permission Posture", border_style="bold red")
        table.add_column("Setting", style="bold cyan")
        table.add_column("Value", style="white")
        for key, value in status.items():
            table.add_row(key, str(value))
        console.print(table)
        console.print("[dim]LEVEL 0/1 run automatically. LEVEL 2/3 require explicit confirmation.[/dim]")
    else:
        print("\nSecurity & Permission Posture:")
        for key, value in status.items():
            print(f"  {key}: {value}")
        print()


def print_audit(lines: int = 20):
    """Display the recent action audit log."""
    entries = get_permission_manager().read_audit_log(lines=lines)
    log = entries.get("log", [])
    if HAS_RICH:
        table = Table(title=f"Action Audit Log ({len(log)} shown)", border_style="dim green")
        table.add_column("Entry", style="white")
        for line in log:
            table.add_row(line)
        console.print(table if log else "[dim]No audit entries yet.[/dim]")
    else:
        print("\nAction Audit Log:")
        for line in log:
            print(f"  {line}")
        print()


def prompt_confirmation(decision) -> bool:
    """Interactive yes/no prompt shown before sensitive actions."""
    preview = decision.render_preview()
    if HAS_RICH:
        console.print(f"[warning]{preview}[/warning]")
        answer = console.input("[bold]Proceed? yes/no > [/bold]").strip().lower()
    else:
        print(preview)
        answer = input("Proceed? yes/no > ").strip().lower()
    return answer in ("yes", "y")


def on_tool_executed(name: str, args: dict, result: dict):
    """Callback hook to print tool execution activity in the terminal."""
    args_summary = ", ".join(f"{k}={repr(v)[:40]}" for k, v in args.items())
    if HAS_RICH:
        console.print(f"[tool] Tool Call:[/tool] [bold]{name}[/bold]({args_summary})")
    else:
        print(f"-> Tool Call: {name}({args_summary})")


def main():
    """Start the Jarvis interactive CLI."""
    jarvis = Jarvis()
    print_banner()

    while True:
        try:
            if HAS_RICH:
                user_input = console.input("\n[user]You > [/user]").strip()
            else:
                user_input = input("\nYou: ").strip()

            if not user_input:
                continue

            # Command routing
            cmd = user_input.lower()
            if cmd in ("/exit", "/quit", "exit", "quit"):
                if HAS_RICH:
                    console.print("[cyan]Jarvis shutting down. Goodbye, Samuel![/cyan]")
                else:
                    print("Jarvis shutting down. Goodbye!")
                break

            if cmd == "/help":
                print_help()
                continue

            if cmd == "/tools":
                print_tools()
                continue

            if cmd == "/agents":
                print_agents()
                continue

            if cmd == "/autonomous":
                print_autonomous()
                continue

            if cmd in ("/notifications", "/alerts"):
                print_notifications()
                continue

            if cmd == "/memory":
                print_memory(jarvis)
                continue

            if cmd == "/security":
                print_security()
                continue

            if cmd == "/audit":
                print_audit()
                continue

            if cmd in ("/status", "/system"):
                result = execute_tool("system_status")
                verdict = result.get("security", {}) if isinstance(result, dict) else {}
                if HAS_RICH:
                    console.print(f"[bold cyan]System status:[/bold cyan] emergency={'ENGAGED' if verdict.get('emergency', {}).get('engaged') else 'released'} | serious_mode={verdict.get('serious_mode')}")
                    console.print(result)
                else:
                    print(result)
                continue

            if cmd in ("/stop", "/emergency", "/cancel"):
                result = get_emergency_stop().engage("CLI /stop command")
                if HAS_RICH:
                    console.print(f"[danger]EMERGENCY STOP:[/danger] {result['message']}")
                else:
                    print(f"EMERGENCY STOP: {result['message']}")
                continue

            if cmd in ("/resume", "/release"):
                result = get_emergency_stop().release()
                if HAS_RICH:
                    console.print(f"[green]CONTROL RESTORED:[/green] {result['message']}")
                else:
                    print(f"CONTROL RESTORED: {result['message']}")
                continue

            if cmd == "/serious":
                pm = get_permission_manager()
                result = pm.set_serious_mode(not pm.serious_mode)
                if HAS_RICH:
                    console.print(f"[warning]{result['message']}[/warning]")
                else:
                    print(result["message"])
                continue

            if cmd == "/dashboard":
                if HAS_RICH:
                    console.print("[bold cyan] Jarvis Web Dashboard is available at:[/bold cyan] [underline]http://localhost:8000[/underline]")
                    console.print("[dim]Run `python3 server.py` in a separate terminal to start the dashboard server.[/dim]")
                else:
                    print("Jarvis Web Dashboard: http://localhost:8000 (Run `python3 server.py` to start)")
                continue

            if cmd == "/clear":
                jarvis.clear_history()
                if HAS_RICH:
                    console.print("[green][OK] Conversation history cleared.[/green]")
                else:
                    print("Conversation history cleared.")
                continue

            # Chat with agent
            if HAS_RICH:
                with console.status("[dim cyan]Jarvis is thinking...[/dim cyan]", spinner="dots"):
                    response = jarvis.chat(
                        user_input,
                        on_tool_call=on_tool_executed,
                        confirm_callback=prompt_confirmation,
                    )

                console.print("\n[jarvis]Jarvis >[/jarvis]")
                console.print(Markdown(response))
            else:
                print("\nJarvis is thinking...")
                response = jarvis.chat(
                    user_input,
                    on_tool_call=on_tool_executed,
                    confirm_callback=prompt_confirmation,
                )
                print(f"\nJarvis:\n{response}")

        except (KeyboardInterrupt, EOFError):
            if HAS_RICH:
                console.print("\n[cyan]Jarvis session closed. Goodbye![/cyan]")
            else:
                print("\nJarvis session closed. Goodbye!")
            break
        except Exception as error:
            if HAS_RICH:
                console.print(f"\n[danger]Error:[/danger] {error}")
            else:
                print(f"\nError: {error}")


if __name__ == "__main__":
    main()
