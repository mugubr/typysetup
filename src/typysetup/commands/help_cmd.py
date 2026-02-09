"""Help command - show detailed help and usage examples."""

from typing import Optional

from rich.console import Console


class HelpCommand:
    """Handles displaying detailed help and usage examples.

    Provides topic-based help for setup, workflows,
    preferences, and general usage.
    """

    def __init__(self):
        """Initialize the help command handler."""
        self.console = Console()

    def execute(self, topic: Optional[str]) -> None:
        """Execute the help command.

        Args:
            topic: Specific help topic, or None for general help.
        """
        if not topic:
            self._show_general_help()
        elif topic.lower() == "setup":
            self._show_setup_help()
        elif topic.lower() == "workflows":
            self._show_workflows_help()
        elif topic.lower() == "preferences":
            self._show_preferences_help()
        else:
            self._show_unknown_topic(topic)

    def _show_general_help(self) -> None:
        """Display general help information."""
        self.console.print("[bold blue]TyPySetup - Python Environment Setup CLI[/bold blue]\n")
        self.console.print(
            "A powerful CLI tool for automating Python environment setup with VSCode integration.\n"
        )

        self._show_quick_start()
        self._show_common_commands()
        self._show_common_workflows()
        self._show_help_topics()

    def _show_quick_start(self) -> None:
        """Display quick start instructions."""
        self.console.print("[bold cyan]Quick Start:[/bold cyan]")
        self.console.print(
            "  1. [dim]typysetup list[/dim]                    # See available project types"
        )
        self.console.print(
            "  2. [dim]typysetup setup /path/to/project[/dim]  # Start interactive setup"
        )
        self.console.print(
            "  3. [dim]cd /path/to/project && source venv/bin/activate[/dim]  "
            "# Activate environment\n"
        )

    def _show_common_commands(self) -> None:
        """Display common commands list."""
        self.console.print("[bold cyan]Common Commands:[/bold cyan]")
        self.console.print(
            "  [cyan]typysetup setup <path>[/cyan]       Run interactive setup wizard"
        )
        self.console.print("  [cyan]typysetup list[/cyan]               List available setup types")
        self.console.print("  [cyan]typysetup preferences --show[/cyan] View your preferences")
        self.console.print("  [cyan]typysetup config <path>[/cyan]      Show project configuration")
        self.console.print(
            "  [cyan]typysetup history[/cyan]            View recent setup history\n"
        )

    def _show_common_workflows(self) -> None:
        """Display common workflow examples."""
        self.console.print("[bold cyan]Common Workflows:[/bold cyan]")
        self.console.print("  • [bold]New FastAPI Project:[/bold]")
        self.console.print("    [dim]mkdir my-api && typysetup setup my-api[/dim]")
        self.console.print("    [dim]# Select 'FastAPI' from the menu[/dim]\n")

        self.console.print("  • [bold]Data Science Project:[/bold]")
        self.console.print("    [dim]typysetup setup ml-project[/dim]")
        self.console.print("    [dim]# Select 'Data Science' from the menu[/dim]\n")

        self.console.print("  • [bold]Check Configuration:[/bold]")
        self.console.print("    [dim]typysetup config /path/to/project[/dim]\n")

    def _show_help_topics(self) -> None:
        """Display available help topics."""
        self.console.print("[bold cyan]Get Help on Specific Topics:[/bold cyan]")
        self.console.print("  [dim]typysetup help setup[/dim]       # Detailed setup command help")
        self.console.print("  [dim]typysetup help workflows[/dim]   # Common workflow examples")
        self.console.print("  [dim]typysetup help preferences[/dim] # Managing preferences\n")
        self.console.print("[dim]For command-specific help, use: typysetup <command> --help[/dim]")

    def _show_setup_help(self) -> None:
        """Display setup command help."""
        self.console.print("[bold blue]Setup Command Help[/bold blue]\n")
        self.console.print("[bold]Usage:[/bold] typysetup setup <path> [options]\n")

        self.console.print("[bold cyan]What it does:[/bold cyan]")
        self.console.print("  • Guides you through interactive project type selection")
        self.console.print("  • Creates Python virtual environment")
        self.console.print("  • Installs dependencies (uv/pip/poetry)")
        self.console.print("  • Generates VSCode configuration")
        self.console.print("  • Saves preferences for future use\n")

        self.console.print("[bold cyan]Options:[/bold cyan]")
        self.console.print("  [cyan]--verbose, -v[/cyan]  Enable detailed logging output\n")

        self.console.print("[bold cyan]Examples:[/bold cyan]")
        self.console.print("  [dim]# Basic setup[/dim]")
        self.console.print("  typysetup setup my-project\n")
        self.console.print("  [dim]# Setup with verbose output[/dim]")
        self.console.print("  typysetup setup my-project --verbose\n")
        self.console.print("  [dim]# Setup existing directory[/dim]")
        self.console.print("  typysetup setup /home/user/existing-project\n")

    def _show_workflows_help(self) -> None:
        """Display workflows help."""
        self.console.print("[bold blue]Common Workflows[/bold blue]\n")

        self.console.print("[bold cyan]1. Starting a New FastAPI Project[/bold cyan]")
        self.console.print("  mkdir my-api")
        self.console.print("  cd my-api")
        self.console.print("  typysetup setup .")
        self.console.print("  [dim]# Select 'FastAPI' from the menu[/dim]")
        self.console.print("  [dim]# Choose package manager (uv recommended)[/dim]")
        self.console.print("  source venv/bin/activate")
        self.console.print("  code .  [dim]# Open in VSCode[/dim]\n")

        self.console.print("[bold cyan]2. Data Science Project with Jupyter[/bold cyan]")
        self.console.print("  typysetup setup ml-analysis")
        self.console.print("  [dim]# Select 'Data Science'[/dim]")
        self.console.print("  cd ml-analysis")
        self.console.print("  source venv/bin/activate")
        self.console.print("  jupyter notebook  [dim]# Start Jupyter[/dim]\n")

        self.console.print("[bold cyan]3. CLI Tool Development[/bold cyan]")
        self.console.print("  typysetup setup my-cli-tool")
        self.console.print("  [dim]# Select 'CLI Tool'[/dim]")
        self.console.print("  cd my-cli-tool")
        self.console.print("  source venv/bin/activate")
        self.console.print("  [dim]# Start coding with Typer/Click[/dim]\n")

        self.console.print("[bold cyan]4. Checking Existing Project[/bold cyan]")
        self.console.print("  typysetup config /path/to/project")
        self.console.print("  [dim]# View setup configuration[/dim]\n")

        self.console.print("[bold cyan]5. Viewing Setup History[/bold cyan]")
        self.console.print("  typysetup history")
        self.console.print("  typysetup history --limit 20 --verbose")
        self.console.print("  [dim]# See all your recent setups[/dim]\n")

    def _show_preferences_help(self) -> None:
        """Display preferences help."""
        self.console.print("[bold blue]Managing Preferences[/bold blue]\n")

        self.console.print("[bold cyan]View Current Preferences:[/bold cyan]")
        self.console.print("  typysetup preferences --show\n")

        self.console.print("[bold cyan]Reset to Defaults:[/bold cyan]")
        self.console.print("  typysetup preferences --reset\n")

        self.console.print("[bold cyan]What Gets Saved:[/bold cyan]")
        self.console.print("  • Preferred package manager (uv/pip/poetry)")
        self.console.print("  • Preferred Python version")
        self.console.print("  • Favorite setup types")
        self.console.print("  • Setup history (last 20 setups)")
        self.console.print("  • VSCode config merge preferences\n")

        self.console.print("[bold cyan]Preferences Location:[/bold cyan]")
        self.console.print("  Linux/macOS: [dim]~/.typysetup/preferences.json[/dim]")
        self.console.print("  Windows:     [dim]%APPDATA%\\typysetup\\preferences.json[/dim]\n")

    def _show_unknown_topic(self, topic: str) -> None:
        """Display message for unknown help topic.

        Args:
            topic: The unknown topic that was requested.
        """
        self.console.print(f"[yellow]Unknown help topic: {topic}[/yellow]")
        self.console.print(
            "\n[dim]Available topics: setup, list, preferences, config, history, workflows[/dim]"
        )
        self.console.print("[dim]Run 'typysetup help' for general help[/dim]")
