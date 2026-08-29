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
from tools.registry import get_registered_tools


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
        table.add_row("/memory", "Inspect all long-term memories")
        table.add_row("/tools", "List all registered tools and descriptions")
        table.add_row("/dashboard", "Launch or display the Cyber Web Dashboard")
        table.add_row("/clear", "Reset conversation history")
        table.add_row("/exit, exit", "Exit the assistant session")
        console.print(table)
    else:
        print("\nCommands:")
        print("  /help   - Show help")
        print("  /memory - View long-term memory")
        print("  /tools  - List registered tools")
        print("  /clear  - Clear conversation history")
        print("  /exit   - Quit\n")


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

            if cmd == "/memory":
                print_memory(jarvis)
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
                    response = jarvis.chat(user_input, on_tool_call=on_tool_executed)

                console.print("\n[jarvis]Jarvis >[/jarvis]")
                console.print(Markdown(response))
            else:
                print("\nJarvis is thinking...")
                response = jarvis.chat(user_input, on_tool_call=on_tool_executed)
                print(f"\nJarvis:\n{response}")

        except KeyboardInterrupt:
            if HAS_RICH:
                console.print("\n[yellow]Session interrupted. Type /exit to quit.[/yellow]")
            else:
                print("\nSession interrupted. Type /exit to quit.")
        except Exception as error:
            if HAS_RICH:
                console.print(f"\n[danger]Error:[/danger] {error}")
            else:
                print(f"\nError: {error}")


if __name__ == "__main__":
    main()
