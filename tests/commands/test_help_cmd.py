"""Unit tests for HelpCommand - topic-based help rendering."""

import io

import pytest
from rich.console import Console

from typysetup.commands.help_cmd import HelpCommand


@pytest.fixture
def help_command() -> HelpCommand:
    """Provide a HelpCommand with a captured, wide Rich console."""
    command = HelpCommand()
    command.console = Console(file=io.StringIO(), width=200)
    return command


def get_output(command: HelpCommand) -> str:
    """Return the plain text captured by the command's console."""
    return command.console.file.getvalue()


class TestHelpCommandGeneralHelp:
    """Tests for general help output (no topic)."""

    def test_execute_without_topic_shows_general_help(self, help_command: HelpCommand) -> None:
        """Test that executing with no topic renders the general help overview."""
        # Arrange / Act
        help_command.execute(None)

        # Assert
        output = get_output(help_command)
        assert "TyPySetup - Python Environment Setup CLI" in output
        assert "automating Python environment setup" in output

    def test_general_help_includes_quick_start_section(self, help_command: HelpCommand) -> None:
        """Test that general help lists quick start steps."""
        # Arrange / Act
        help_command.execute(None)

        # Assert
        output = get_output(help_command)
        assert "Quick Start:" in output
        assert "typysetup list" in output
        assert "typysetup setup /path/to/project" in output

    def test_general_help_includes_common_commands(self, help_command: HelpCommand) -> None:
        """Test that general help lists the common commands."""
        # Arrange / Act
        help_command.execute(None)

        # Assert
        output = get_output(help_command)
        assert "Common Commands:" in output
        assert "typysetup setup <path>" in output
        assert "typysetup preferences --show" in output
        assert "typysetup history" in output

    def test_general_help_includes_workflows_and_topics(self, help_command: HelpCommand) -> None:
        """Test that general help lists workflows and available help topics."""
        # Arrange / Act
        help_command.execute(None)

        # Assert
        output = get_output(help_command)
        assert "Common Workflows:" in output
        assert "New FastAPI Project:" in output
        assert "Data Science Project:" in output
        assert "Get Help on Specific Topics:" in output
        assert "typysetup help workflows" in output


class TestHelpCommandTopics:
    """Tests for topic-specific help output."""

    def test_setup_topic_shows_setup_help(self, help_command: HelpCommand) -> None:
        """Test that the setup topic renders setup usage, options, and examples."""
        # Arrange / Act
        help_command.execute("setup")

        # Assert
        output = get_output(help_command)
        assert "Setup Command Help" in output
        assert "typysetup setup <path>" in output
        assert "--verbose, -v" in output
        assert "Creates Python virtual environment" in output
        assert "typysetup setup my-project --verbose" in output

    def test_topic_matching_is_case_insensitive(self, help_command: HelpCommand) -> None:
        """Test that topic names are matched case-insensitively."""
        # Arrange / Act
        help_command.execute("SETUP")

        # Assert
        output = get_output(help_command)
        assert "Setup Command Help" in output
        assert "Unknown help topic" not in output

    def test_workflows_topic_shows_workflow_examples(self, help_command: HelpCommand) -> None:
        """Test that the workflows topic renders all numbered workflows."""
        # Arrange / Act
        help_command.execute("workflows")

        # Assert
        output = get_output(help_command)
        assert "Common Workflows" in output
        assert "1. Starting a New FastAPI Project" in output
        assert "2. Data Science Project with Jupyter" in output
        assert "3. CLI Tool Development" in output
        assert "4. Checking Existing Project" in output
        assert "5. Viewing Setup History" in output

    def test_preferences_topic_shows_preferences_help(self, help_command: HelpCommand) -> None:
        """Test that the preferences topic renders management commands and file location."""
        # Arrange / Act
        help_command.execute("preferences")

        # Assert
        output = get_output(help_command)
        assert "Managing Preferences" in output
        assert "typysetup preferences --show" in output
        assert "typysetup preferences --reset" in output
        assert "preferences.json" in output

    def test_unknown_topic_shows_available_topics(self, help_command: HelpCommand) -> None:
        """Test that an unknown topic shows a warning and the list of valid topics."""
        # Arrange / Act
        help_command.execute("bogus")

        # Assert
        output = get_output(help_command)
        assert "Unknown help topic: bogus" in output
        assert "Available topics: setup, list, preferences, config, history, workflows" in output
        assert "Run 'typysetup help' for general help" in output


class TestHelpCommandCli:
    """Tests for the help command wired through the Typer app."""

    def test_help_command_via_cli_runner(self, cli_runner) -> None:
        """Test that 'typysetup help' runs successfully through the CLI."""
        # Arrange
        from typysetup.main import app

        # Act
        result = cli_runner.invoke(app, ["help"])

        # Assert
        assert result.exit_code == 0
        assert "TyPySetup" in result.output

    def test_help_topic_via_cli_runner(self, cli_runner) -> None:
        """Test that 'typysetup help setup' renders the setup topic through the CLI."""
        # Arrange
        from typysetup.main import app

        # Act
        result = cli_runner.invoke(app, ["help", "setup"])

        # Assert
        assert result.exit_code == 0
        assert "Setup Command Help" in result.output
