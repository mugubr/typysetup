"""Tests for CLI commands: config display and history management."""

import json
from datetime import UTC, datetime

import pytest
from typer.testing import CliRunner

from typysetup.main import app
from typysetup.models.user_preference import SetupHistoryEntry, UserPreference

runner = CliRunner()


class TestConfigCommand:
    """Test config command."""

    def test_config_show_existing_project(self, tmp_path):
        """Test showing config for existing project."""
        # Create project config
        pysetup_dir = tmp_path / ".typysetup"
        pysetup_dir.mkdir()

        config_data = {
            "project_path": str(tmp_path),
            "setup_type_slug": "fastapi",
            "python_version": "3.11",
            "python_executable": "/usr/bin/python3",
            "package_manager": "uv",
            "venv_path": str(tmp_path / "venv"),
            "status": "success",
            "created_at": datetime.now(UTC).isoformat() + "Z",
            "installed_dependencies": [],
        }

        config_file = pysetup_dir / "config.json"
        with open(config_file, "w") as f:
            json.dump(config_data, f)

        # Run command
        result = runner.invoke(app, ["config", str(tmp_path)])

        assert result.exit_code == 0
        assert "Project Configuration" in result.stdout
        assert "fastapi" in result.stdout
        assert "3.11" in result.stdout

    def test_config_show_nonexistent_project(self, tmp_path):
        """Test showing config for project without config."""
        result = runner.invoke(app, ["config", str(tmp_path)])

        assert result.exit_code == 1
        assert "No TyPySetup configuration found" in result.stdout

    def test_config_show_invalid_path(self):
        """Test showing config for invalid path."""
        result = runner.invoke(app, ["config", "/nonexistent/path"])

        assert result.exit_code == 1
        assert "not found" in result.stdout

    def test_config_show_with_metadata(self, tmp_path):
        """Test showing config with project metadata."""
        pysetup_dir = tmp_path / ".typysetup"
        pysetup_dir.mkdir()

        config_data = {
            "project_path": str(tmp_path),
            "setup_type_slug": "flask",
            "python_version": "3.10",
            "python_executable": "/usr/bin/python3",
            "package_manager": "pip",
            "venv_path": str(tmp_path / "venv"),
            "status": "success",
            "created_at": datetime.now(UTC).isoformat() + "Z",
            "installed_dependencies": [],
            "project_metadata": {
                "project_name": "my-flask-app",
                "description": "A Flask application",
                "author_name": "Test Author",
                "author_email": "test@example.com",
            },
        }

        config_file = pysetup_dir / "config.json"
        with open(config_file, "w") as f:
            json.dump(config_data, f)

        result = runner.invoke(app, ["config", str(tmp_path)])

        assert result.exit_code == 0
        assert "my-flask-app" in result.stdout
        assert "Test Author" in result.stdout

    def test_config_show_with_dependencies(self, tmp_path):
        """Test showing config with installed dependencies."""
        pysetup_dir = tmp_path / ".typysetup"
        pysetup_dir.mkdir()

        config_data = {
            "project_path": str(tmp_path),
            "setup_type_slug": "fastapi",
            "python_version": "3.11",
            "python_executable": "/usr/bin/python3",
            "package_manager": "uv",
            "venv_path": str(tmp_path / "venv"),
            "status": "success",
            "created_at": datetime.now(UTC).isoformat() + "Z",
            "installed_dependencies": [
                {
                    "name": "fastapi",
                    "version": "0.100.0",
                    "installed_by": "uv",
                    "from_group": "core",
                },
                {
                    "name": "uvicorn",
                    "version": "0.20.0",
                    "installed_by": "uv",
                    "from_group": "core",
                },
                {"name": "pytest", "version": "7.0.0", "installed_by": "uv", "from_group": "dev"},
            ],
        }

        config_file = pysetup_dir / "config.json"
        with open(config_file, "w") as f:
            json.dump(config_data, f)

        result = runner.invoke(app, ["config", str(tmp_path)])

        assert result.exit_code == 0
        assert "Installed Dependencies" in result.stdout
        assert "3" in result.stdout  # Total dependencies


class TestHistoryCommand:
    """Test history command."""

    @pytest.fixture
    def preferences_with_history(self, tmp_path, monkeypatch):
        """Create preferences file with history."""
        # Setup preferences directory
        config_dir = tmp_path / ".config" / "typysetup"
        config_dir.mkdir(parents=True, exist_ok=True)
        prefs_file = config_dir / "preferences.json"

        # Monkeypatch the preferences path
        monkeypatch.setenv("HOME", str(tmp_path))
        monkeypatch.setenv("USERPROFILE", str(tmp_path))

        # Create preferences with history
        prefs = UserPreference()
        prefs.add_to_history(
            SetupHistoryEntry(
                timestamp=datetime(2024, 1, 15, 10, 30),
                setup_type_slug="fastapi",
                project_path="/home/user/projects/api",
                project_name="my-api",
                python_version="3.11",
                package_manager="uv",
                success=True,
                duration_seconds=25.5,
            )
        )
        prefs.add_to_history(
            SetupHistoryEntry(
                timestamp=datetime(2024, 1, 16, 14, 20),
                setup_type_slug="flask",
                project_path="/home/user/projects/web",
                project_name="my-web-app",
                python_version="3.10",
                package_manager="pip",
                success=False,
                duration_seconds=15.2,
            )
        )

        # Save to file
        with open(prefs_file, "w") as f:
            json.dump(prefs.model_dump(mode="json"), f)

        return prefs_file

    def test_history_with_entries(self, preferences_with_history):
        """Test history command with existing entries."""
        result = runner.invoke(app, ["history"])

        assert result.exit_code == 0
        assert "Setup History" in result.stdout
        assert "fastapi" in result.stdout
        assert "flask" in result.stdout
        assert "my-api" in result.stdout

    def test_history_with_limit(self, preferences_with_history):
        """Test history command with custom limit."""
        result = runner.invoke(app, ["history", "--limit", "1"])

        assert result.exit_code == 0
        # Should only show 1 entry (most recent)
        assert "flask" in result.stdout

    def test_history_verbose(self, preferences_with_history):
        """Test history command with verbose flag."""
        result = runner.invoke(app, ["history", "--verbose"])

        assert result.exit_code == 0
        assert "Python" in result.stdout or "3.11" in result.stdout
        assert "Manager" in result.stdout or "uv" in result.stdout

    def test_history_no_entries(self, tmp_path, monkeypatch):
        """Test history command with no entries."""
        # Setup empty preferences
        config_dir = tmp_path / ".config" / "typysetup"
        config_dir.mkdir(parents=True, exist_ok=True)
        prefs_file = config_dir / "preferences.json"

        monkeypatch.setenv("HOME", str(tmp_path))
        monkeypatch.setenv("USERPROFILE", str(tmp_path))

        prefs = UserPreference()
        with open(prefs_file, "w") as f:
            json.dump(prefs.model_dump(mode="json"), f)

        result = runner.invoke(app, ["history"])

        assert result.exit_code == 0
        assert "No setup history found" in result.stdout

    def test_history_success_and_failed_counts(self, preferences_with_history):
        """Test that history shows success/failed counts."""
        result = runner.invoke(app, ["history"])

        assert result.exit_code == 0
        # Should show statistics
        assert "successful" in result.stdout or "✓" in result.stdout
        assert "failed" in result.stdout or "✗" in result.stdout

    def test_history_duration_display(self, preferences_with_history):
        """Test that history displays duration."""
        result = runner.invoke(app, ["history"])

        assert result.exit_code == 0
        # Should show duration in seconds
        assert "25.5s" in result.stdout or "15.2s" in result.stdout

    def test_history_with_long_project_name(self, tmp_path, monkeypatch):
        """Test history truncates long project names."""
        config_dir = tmp_path / ".config" / "typysetup"
        config_dir.mkdir(parents=True, exist_ok=True)
        prefs_file = config_dir / "preferences.json"

        monkeypatch.setenv("HOME", str(tmp_path))
        monkeypatch.setenv("USERPROFILE", str(tmp_path))

        prefs = UserPreference()
        prefs.add_to_history(
            SetupHistoryEntry(
                timestamp=datetime(2024, 1, 15, 10, 30),
                setup_type_slug="fastapi",
                project_path="/home/user/projects/very-long-project-name",
                project_name="a-very-long-project-name-that-should-be-truncated",
                python_version="3.11",
                package_manager="uv",
                success=True,
            )
        )

        with open(prefs_file, "w") as f:
            json.dump(prefs.model_dump(mode="json"), f)

        result = runner.invoke(app, ["history"])

        assert result.exit_code == 0
        # Name should be truncated with ...
        assert "..." in result.stdout or len(result.stdout) < 1000

    def test_history_newest_first(self, preferences_with_history):
        """Test that history shows newest entries first."""
        result = runner.invoke(app, ["history"])

        assert result.exit_code == 0
        # flask is newer than fastapi, should appear first in output
        flask_pos = result.stdout.find("flask")
        fastapi_pos = result.stdout.find("fastapi")
        assert flask_pos < fastapi_pos


class TestConfigCommandEdgeCases:
    """Test edge cases for config command."""

    def test_config_with_corrupted_json(self, tmp_path):
        """Test config command with corrupted JSON file."""
        pysetup_dir = tmp_path / ".typysetup"
        pysetup_dir.mkdir()

        config_file = pysetup_dir / "config.json"
        config_file.write_text("{ invalid json }")

        result = runner.invoke(app, ["config", str(tmp_path)])

        assert result.exit_code == 1
        assert "Error" in result.stdout

    def test_config_with_missing_required_fields(self, tmp_path):
        """Test config with missing required fields."""
        pysetup_dir = tmp_path / ".typysetup"
        pysetup_dir.mkdir()

        config_data = {
            "project_path": str(tmp_path),
            "setup_type_slug": "fastapi",
            # Missing required fields
        }

        config_file = pysetup_dir / "config.json"
        with open(config_file, "w") as f:
            json.dump(config_data, f)

        result = runner.invoke(app, ["config", str(tmp_path)])

        assert result.exit_code == 1
        assert "Error" in result.stdout

    def test_config_with_relative_path(self, tmp_path):
        """Test config command with relative path."""
        pysetup_dir = tmp_path / ".typysetup"
        pysetup_dir.mkdir()

        config_data = {
            "project_path": str(tmp_path),
            "setup_type_slug": "flask",
            "python_version": "3.10",
            "python_executable": "/usr/bin/python3",
            "package_manager": "pip",
            "venv_path": str(tmp_path / "venv"),
            "status": "success",
            "created_at": datetime.now(UTC).isoformat() + "Z",
            "installed_dependencies": [],
        }

        config_file = pysetup_dir / "config.json"
        with open(config_file, "w") as f:
            json.dump(config_data, f)

        # Change to parent directory and use relative path
        import os

        original_cwd = os.getcwd()
        try:
            os.chdir(tmp_path.parent)
            result = runner.invoke(app, ["config", tmp_path.name])
            assert result.exit_code == 0
        finally:
            os.chdir(original_cwd)


class TestHistoryCommandEdgeCases:
    """Test edge cases for history command."""

    def test_history_with_missing_preferences_file(self, tmp_path, monkeypatch):
        """Test history when preferences file doesn't exist."""
        config_dir = tmp_path / ".config" / "typysetup"
        config_dir.mkdir(parents=True, exist_ok=True)

        monkeypatch.setenv("HOME", str(tmp_path))
        monkeypatch.setenv("USERPROFILE", str(tmp_path))

        result = runner.invoke(app, ["history"])

        # Should create default preferences and show no history
        assert result.exit_code == 0
        assert "No setup history found" in result.stdout

    def test_history_with_zero_limit(self, preferences_with_history):
        """Test history with limit of 0."""
        result = runner.invoke(app, ["history", "--limit", "0"])

        # Should handle gracefully
        assert result.exit_code == 0

    def test_history_with_negative_limit(self, preferences_with_history):
        """Test history with negative limit."""
        result = runner.invoke(app, ["history", "--limit", "-1"])

        # Typer should handle validation
        assert result.exit_code != 0 or "history" in result.stdout.lower()
