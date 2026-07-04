"""Unit tests for PreferencesCommand - user preferences management."""

import io
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import typer
from rich.console import Console

from typysetup.commands.preferences_cmd import PreferencesCommand
from typysetup.core import PreferenceManager
from typysetup.models import UserPreference
from typysetup.models.user_preference import SetupHistoryEntry


@pytest.fixture(autouse=True)
def isolated_home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Isolate HOME so the developer's real preferences are never touched."""
    monkeypatch.setenv("HOME", str(tmp_path))
    return tmp_path


@pytest.fixture
def preferences_command(tmp_path: Path) -> PreferencesCommand:
    """Provide a PreferencesCommand with tmp-backed manager and captured console."""
    manager = PreferenceManager(preferences_path=tmp_path / "preferences.json")
    command = PreferencesCommand(preference_manager=manager)
    command.console = Console(file=io.StringIO(), width=200)
    return command


def get_output(command: PreferencesCommand) -> str:
    """Return the plain text captured by the command's console."""
    return command.console.file.getvalue()


def make_history_entry(**overrides) -> SetupHistoryEntry:
    """Build a SetupHistoryEntry with sensible defaults."""
    data = {
        "timestamp": datetime(2026, 1, 15, 10, 30),
        "setup_type_slug": "fastapi",
        "project_path": "/home/user/projects/my_api",
        "success": True,
        "duration_seconds": 1.5,
    }
    data.update(overrides)
    return SetupHistoryEntry(**data)


class TestPreferencesCommandShow:
    """Tests for the --show flow."""

    def test_show_with_fresh_preferences_displays_defaults(
        self, preferences_command: PreferencesCommand
    ) -> None:
        """Test that --show creates defaults and displays them when no file exists."""
        # Arrange / Act
        preferences_command.execute(show=True, reset=False)

        # Assert
        output = get_output(preferences_command)
        assert "User Preferences" in output
        assert "Current Preferences" in output
        assert "uv" in output  # default preferred manager
        assert "No setup history yet." in output
        assert "Preferences file:" in output

    def test_show_displays_saved_preferences_and_history(
        self, preferences_command: PreferencesCommand
    ) -> None:
        """Test that --show renders saved setup types and history entries."""
        # Arrange
        prefs = UserPreference(preferred_manager="pip", preferred_python_version="3.12")
        prefs.add_preferred_setup_type("fastapi")
        prefs.add_to_history(make_history_entry(project_name="my_api"))
        prefs.add_to_history(
            make_history_entry(
                setup_type_slug="data-science",
                project_name=None,
                success=False,
                duration_seconds=None,
            )
        )
        preferences_command.preference_manager.save_preferences(prefs)

        # Act
        preferences_command.execute(show=True, reset=False)

        # Assert
        output = get_output(preferences_command)
        assert "pip" in output
        assert "3.12" in output
        assert "Preferred Setup Types" in output
        assert "1. fastapi" in output
        assert "Recent Setup History" in output
        assert "Success" in output
        assert "Failed" in output
        assert "N/A" in output  # missing duration
        assert "my_api" in output  # project name and path fallback
        assert "Showing last 2 of 2 total entries" in output

    def test_show_limits_history_display_to_last_ten(
        self, preferences_command: PreferencesCommand
    ) -> None:
        """Test that --show displays at most the 10 most recent history entries."""
        # Arrange
        prefs = UserPreference()
        for i in range(12):
            prefs.add_to_history(make_history_entry(project_path=f"/tmp/project_{i}"))
        preferences_command.preference_manager.save_preferences(prefs)

        # Act
        preferences_command.execute(show=True, reset=False)

        # Assert
        output = get_output(preferences_command)
        assert "Showing last 10 of 12 total entries" in output

    def test_show_raises_exit_when_loading_fails(self) -> None:
        """Test that --show exits with code 1 and reports load errors."""
        # Arrange
        failing_manager = MagicMock(spec=PreferenceManager)
        failing_manager.load_preferences.side_effect = OSError("disk on fire")
        command = PreferencesCommand(preference_manager=failing_manager)
        command.console = Console(file=io.StringIO(), width=200)

        # Act / Assert
        with pytest.raises(typer.Exit) as exc_info:
            command.execute(show=True, reset=False)

        assert exc_info.value.exit_code == 1
        assert "Error loading preferences: disk on fire" in get_output(command)


class TestPreferencesCommandDisplayHelpers:
    """Tests for the display helper methods with real UserPreference instances."""

    def test_main_table_shows_not_set_for_missing_values(
        self, preferences_command: PreferencesCommand
    ) -> None:
        """Test that unset manager/python version render as 'Not set'."""
        # Arrange
        prefs = UserPreference(preferred_python_version=None)
        prefs.preferred_manager = None

        # Act
        preferences_command._display_main_preferences_table(prefs)

        # Assert
        output = get_output(preferences_command)
        assert "Not set" in output
        assert "merge" in output  # merge mode default
        assert "Yes" in output  # first_run default

    def test_preferred_setup_types_skipped_when_empty(
        self, preferences_command: PreferencesCommand
    ) -> None:
        """Test that the setup types section is omitted when the list is empty."""
        # Arrange
        prefs = UserPreference()

        # Act
        preferences_command._display_preferred_setup_types(prefs)

        # Assert
        assert "Preferred Setup Types" not in get_output(preferences_command)

    def test_setup_history_uses_path_tail_when_name_missing(
        self, preferences_command: PreferencesCommand
    ) -> None:
        """Test that history rows fall back to the last path segment as project name."""
        # Arrange
        prefs = UserPreference()
        prefs.add_to_history(
            make_history_entry(project_name=None, project_path="/srv/apps/tail_project")
        )

        # Act
        preferences_command._display_setup_history(prefs)

        # Assert
        output = get_output(preferences_command)
        assert "tail_project" in output
        assert "1.5s" in output


class TestPreferencesCommandReset:
    """Tests for the --reset flow."""

    def test_reset_confirmed_restores_defaults(
        self, preferences_command: PreferencesCommand
    ) -> None:
        """Test that a confirmed reset writes default preferences back to disk."""
        # Arrange
        modified = UserPreference(preferred_python_version="3.12", first_run=False)
        preferences_command.preference_manager.save_preferences(modified)

        with patch("questionary.confirm") as mock_confirm:
            mock_confirm.return_value.ask.return_value = True

            # Act
            preferences_command.execute(show=False, reset=True)

        # Assert
        output = get_output(preferences_command)
        assert "Preferences reset to defaults successfully!" in output
        reloaded = preferences_command.preference_manager.load_preferences()
        assert reloaded.preferred_python_version is None
        assert reloaded.first_run is True

    def test_reset_cancelled_keeps_existing_preferences(
        self, preferences_command: PreferencesCommand
    ) -> None:
        """Test that declining the confirmation leaves preferences untouched."""
        # Arrange
        modified = UserPreference(preferred_python_version="3.12")
        preferences_command.preference_manager.save_preferences(modified)

        with patch("questionary.confirm") as mock_confirm:
            mock_confirm.return_value.ask.return_value = False

            # Act
            preferences_command.execute(show=False, reset=True)

        # Assert
        assert "Reset cancelled." in get_output(preferences_command)
        reloaded = preferences_command.preference_manager.load_preferences()
        assert reloaded.preferred_python_version == "3.12"

    def test_reset_raises_exit_when_manager_fails(self) -> None:
        """Test that a failing reset exits with code 1 and reports the error."""
        # Arrange
        failing_manager = MagicMock(spec=PreferenceManager)
        failing_manager.reset_to_defaults.side_effect = OSError("read-only fs")
        command = PreferencesCommand(preference_manager=failing_manager)
        command.console = Console(file=io.StringIO(), width=200)

        with patch("questionary.confirm") as mock_confirm:
            mock_confirm.return_value.ask.return_value = True

            # Act / Assert
            with pytest.raises(typer.Exit) as exc_info:
                command.execute(show=False, reset=True)

        assert exc_info.value.exit_code == 1
        assert "Error resetting preferences: read-only fs" in get_output(command)


class TestPreferencesCommandHelp:
    """Tests for the default help output."""

    def test_execute_without_flags_shows_help(
        self, preferences_command: PreferencesCommand
    ) -> None:
        """Test that executing with no flags prints usage help."""
        # Arrange / Act
        preferences_command.execute(show=False, reset=False)

        # Assert
        output = get_output(preferences_command)
        assert "TyPySetup Preferences" in output
        assert "--show" in output
        assert "--reset" in output
        assert "typysetup preferences --show" in output

    def test_default_constructor_uses_isolated_home(self, isolated_home: Path) -> None:
        """Test that a default-constructed command targets the isolated HOME."""
        # Arrange / Act
        command = PreferencesCommand()

        # Assert
        prefs_path = command.preference_manager.preferences_path
        assert str(prefs_path).startswith(str(isolated_home))
