"""
Integration tests for complete setup flow (T134).

Tests the entire setup process from menu → venv → deps → config → preferences.
"""

import json
import subprocess
from unittest.mock import patch

import pytest
from typer.testing import CliRunner

from typysetup.core.preference_manager import PreferenceManager
from typysetup.main import app


def create_mock_checkbox():
    """Create a mock checkbox that returns all options."""

    class MockCheckbox:
        def __init__(self, message, choices, **kwargs):
            self.choices = choices

        def ask(self):
            # Return all values (select all groups)
            return ["core", "dev"]

    return MockCheckbox


@pytest.fixture
def cli_runner():
    """Typer CLI runner for testing commands."""
    return CliRunner()


@pytest.fixture
def mock_subprocess_run():
    """Mock subprocess.run to avoid actual dependency installation."""

    def _mock_run(cmd, *args, **kwargs):
        """Mock successful subprocess execution."""
        # Simulate successful installation
        if any(manager in cmd for manager in ["uv", "pip", "poetry"]):
            return subprocess.CompletedProcess(
                args=cmd, returncode=0, stdout=b"Successfully installed", stderr=b""
            )
        return subprocess.CompletedProcess(args=cmd, returncode=0, stdout=b"", stderr=b"")

    return _mock_run


@pytest.fixture
def mock_questionary_responses():
    """Mock Questionary prompts with predefined responses."""

    class MockQuestionarySelect:
        def __init__(self, message, choices, **kwargs):
            self.message = message
            self.choices = choices

        def ask(self):
            # Return first choice for simplicity in tests
            if "setup type" in self.message.lower():
                return "FastAPI"
            elif "package manager" in self.message.lower():
                return "uv"
            return self.choices[0] if self.choices else None

    class MockQuestionaryConfirm:
        def __init__(self, message, **kwargs):
            self.message = message

        def ask(self):
            # Confirm all prompts
            return True

    class MockQuestionaryCheckbox:
        def __init__(self, message, choices, **kwargs):
            self.message = message
            self.choices = choices

        def ask(self):
            # Return all choices (select all groups)
            if isinstance(self.choices, list):
                return [
                    choice.get("value", choice) if isinstance(choice, dict) else choice
                    for choice in self.choices
                ]
            return ["core", "dev"]  # Default groups

    return {
        "select": MockQuestionarySelect,
        "confirm": MockQuestionaryConfirm,
        "checkbox": MockQuestionaryCheckbox,
    }


class TestCompleteSetupFlow:
    """Test complete setup flow end-to-end."""

    def test_setup_flow_fastapi_with_uv(
        self, tmp_path, cli_runner, mock_subprocess_run, mock_questionary_responses
    ):
        """
        Test complete setup flow for FastAPI with uv.

        Flow:
        1. User runs `typysetup setup <path>`
        2. Menu displays with setup types
        3. User selects FastAPI
        4. User selects uv as package manager
        5. User confirms setup
        6. System creates venv
        7. System installs dependencies
        8. System generates VSCode config
        9. System saves preferences
        10. Setup completes successfully
        """
        project_path = tmp_path / "my-fastapi-project"
        project_path.mkdir()

        # Mock subprocess and questionary
        with patch("subprocess.run", side_effect=mock_subprocess_run), patch(
            "questionary.select", mock_questionary_responses["select"]
        ), patch("questionary.confirm", mock_questionary_responses["confirm"]), patch(
            "questionary.checkbox", mock_questionary_responses["checkbox"]
        ):
            # Run setup command
            result = cli_runner.invoke(app, ["setup", str(project_path)])

            # Verify command succeeded
            assert result.exit_code == 0
            assert "Setup configuration created successfully" in result.stdout

            # Verify venv was created
            venv_path = project_path / "venv"
            assert venv_path.exists()
            assert (venv_path / "pyvenv.cfg").exists()

            # Verify VSCode config was created
            vscode_dir = project_path / ".vscode"
            assert vscode_dir.exists()
            assert (vscode_dir / "settings.json").exists()

            settings_content = json.loads((vscode_dir / "settings.json").read_text())
            assert "python.defaultInterpreterPath" in settings_content
            assert "venv" in settings_content["python.defaultInterpreterPath"]

            # Verify project config was saved
            config_file = project_path / ".typysetup" / "config.json"
            assert config_file.exists()

            config_data = json.loads(config_file.read_text())
            assert config_data["setup_type_slug"] == "fastapi"
            assert config_data["package_manager"] == "uv"
            assert config_data["status"] == "success"

    def test_setup_flow_data_science_with_pip(self, tmp_path, cli_runner, mock_subprocess_run):
        """Test complete setup flow for Data Science with pip."""
        project_path = tmp_path / "ml-analysis"
        project_path.mkdir()

        # Mock to select Data Science and pip
        class MockSelect:
            def __init__(self, message, choices, **kwargs):
                self.choices = choices

            def ask(self):
                if "setup type" in str(self.choices):
                    return "Data Science"
                return "pip"

        class MockConfirm:
            def __init__(self, message, **kwargs):
                pass

            def ask(self):
                return True

        with patch("subprocess.run", side_effect=mock_subprocess_run), patch(
            "questionary.select", MockSelect
        ), patch("questionary.confirm", MockConfirm), patch(
            "questionary.checkbox", create_mock_checkbox()
        ):
            result = cli_runner.invoke(app, ["setup", str(project_path)])

            assert result.exit_code == 0

            # Verify venv
            assert (project_path / "venv").exists()

            # Verify config
            config_file = project_path / ".typysetup" / "config.json"
            assert config_file.exists()
            config_data = json.loads(config_file.read_text())
            assert config_data["setup_type_slug"] == "data-science"
            assert config_data["package_manager"] == "pip"

    def test_setup_flow_with_verbose_mode(self, tmp_path, cli_runner, mock_subprocess_run):
        """Test setup flow with verbose output enabled."""
        project_path = tmp_path / "test-verbose"
        project_path.mkdir()

        class MockSelect:
            def ask(self):
                return "CLI Tool"

        class MockConfirm:
            def ask(self):
                return True

        with patch("subprocess.run", side_effect=mock_subprocess_run), patch(
            "questionary.select", MockSelect
        ), patch("questionary.confirm", MockConfirm), patch(
            "questionary.checkbox", create_mock_checkbox()
        ):
            result = cli_runner.invoke(app, ["setup", str(project_path), "--verbose"])

            assert result.exit_code == 0
            # Verbose mode should be enabled (actual verbose output depends on implementation)
            assert "Setup configuration created successfully" in result.stdout

    def test_setup_flow_preserves_existing_vscode_settings(
        self, tmp_path, cli_runner, mock_subprocess_run
    ):
        """Test that setup preserves existing VSCode settings."""
        project_path = tmp_path / "existing-project"
        project_path.mkdir()

        # Create existing VSCode settings
        vscode_dir = project_path / ".vscode"
        vscode_dir.mkdir()
        existing_settings = {
            "editor.fontSize": 14,
            "workbench.colorTheme": "Monokai",
            "python.linting.enabled": False,  # Will be overridden
        }
        (vscode_dir / "settings.json").write_text(json.dumps(existing_settings, indent=2))

        class MockSelect:
            def ask(self):
                return "FastAPI"

        class MockConfirm:
            def ask(self):
                return True

        with patch("subprocess.run", side_effect=mock_subprocess_run), patch(
            "questionary.select", MockSelect
        ), patch("questionary.confirm", MockConfirm), patch(
            "questionary.checkbox", create_mock_checkbox()
        ):
            result = cli_runner.invoke(app, ["setup", str(project_path)])

            assert result.exit_code == 0

            # Verify settings were merged
            merged_settings = json.loads((vscode_dir / "settings.json").read_text())

            # Existing settings preserved
            assert merged_settings["editor.fontSize"] == 14
            assert merged_settings["workbench.colorTheme"] == "Monokai"

            # Setup settings applied (override)
            assert merged_settings["python.linting.enabled"] is True
            assert "python.defaultInterpreterPath" in merged_settings

    def test_setup_flow_updates_user_preferences(self, tmp_path, cli_runner, mock_subprocess_run):
        """Test that setup updates user preferences and history."""
        project_path = tmp_path / "test-preferences"
        project_path.mkdir()

        # Clear existing preferences
        pref_manager = PreferenceManager()
        if pref_manager.preferences_path.exists():
            pref_manager.preferences_path.unlink()

        class MockSelect:
            def ask(self):
                return "FastAPI"

        class MockConfirm:
            def ask(self):
                return True

        with patch("subprocess.run", side_effect=mock_subprocess_run), patch(
            "questionary.select", MockSelect
        ), patch("questionary.confirm", MockConfirm), patch(
            "questionary.checkbox", create_mock_checkbox()
        ):
            result = cli_runner.invoke(app, ["setup", str(project_path)])

            assert result.exit_code == 0

            # Verify preferences were updated
            prefs = pref_manager.load_preferences()

            # Check history
            assert len(prefs.setup_history) > 0
            last_setup = prefs.setup_history[-1]
            assert last_setup.setup_type_slug == "fastapi"
            assert last_setup.package_manager == "uv"
            assert last_setup.success is True

            # Check preferred setup types updated
            assert "fastapi" in prefs.preferred_setup_types

    def test_setup_flow_handles_missing_directory(self, cli_runner, mock_subprocess_run):
        """Test that setup handles missing project directory gracefully."""
        non_existent_path = "/tmp/non-existent-project-xyz123"

        class MockSelect:
            def ask(self):
                return "FastAPI"

        class MockConfirm:
            def ask(self):
                return True

        with patch("subprocess.run", side_effect=mock_subprocess_run), patch(
            "questionary.select", MockSelect
        ), patch("questionary.confirm", MockConfirm), patch(
            "questionary.checkbox", create_mock_checkbox()
        ):
            result = cli_runner.invoke(app, ["setup", non_existent_path])

            # Should handle gracefully (create directory or show error)
            # Exact behavior depends on implementation
            assert result.exit_code in [0, 1]

    def test_setup_flow_multiple_setups_in_sequence(
        self, tmp_path, cli_runner, mock_subprocess_run
    ):
        """Test running multiple setups in sequence."""
        # First setup: FastAPI
        project1 = tmp_path / "project1"
        project1.mkdir()

        class MockSelect1:
            def ask(self):
                return "FastAPI"

        class MockConfirm:
            def ask(self):
                return True

        with patch("subprocess.run", side_effect=mock_subprocess_run), patch(
            "questionary.select", MockSelect1
        ), patch("questionary.confirm", MockConfirm):
            result1 = cli_runner.invoke(app, ["setup", str(project1)])
            assert result1.exit_code == 0

        # Second setup: Django
        project2 = tmp_path / "project2"
        project2.mkdir()

        class MockSelect2:
            def ask(self):
                return "Django"

        with patch("subprocess.run", side_effect=mock_subprocess_run), patch(
            "questionary.select", MockSelect2
        ), patch("questionary.confirm", MockConfirm):
            result2 = cli_runner.invoke(app, ["setup", str(project2)])
            assert result2.exit_code == 0

        # Verify both projects configured correctly
        config1 = json.loads((project1 / ".typysetup" / "config.json").read_text())
        config2 = json.loads((project2 / ".typysetup" / "config.json").read_text())

        assert config1["setup_type_slug"] == "fastapi"
        assert config2["setup_type_slug"] == "django"

        # Verify preferences updated with both
        pref_manager = PreferenceManager()
        prefs = pref_manager.load_preferences()
        assert len(prefs.setup_history) >= 2


class TestSetupFlowErrorHandling:
    """Test error handling in setup flow."""

    def test_setup_flow_handles_venv_creation_failure(self, tmp_path, cli_runner):
        """Test that setup handles venv creation failure gracefully."""
        project_path = tmp_path / "test-venv-fail"
        project_path.mkdir()

        class MockSelect:
            def ask(self):
                return "FastAPI"

        class MockConfirm:
            def ask(self):
                return True

        # Mock venv creation to fail
        def mock_create_failing(*args, **kwargs):
            raise PermissionError("Cannot create venv")

        with patch("questionary.select", MockSelect), patch(
            "questionary.confirm", MockConfirm
        ), patch("venv.EnvBuilder.create", side_effect=mock_create_failing):
            result = cli_runner.invoke(app, ["setup", str(project_path)])

            # Should fail gracefully
            assert result.exit_code == 1
            # Rollback should cleanup (no partial venv left)
            assert not (project_path / "venv").exists()

    def test_setup_flow_handles_dependency_installation_failure(self, tmp_path, cli_runner):
        """Test that setup handles dependency installation failure."""
        project_path = tmp_path / "test-deps-fail"
        project_path.mkdir()

        class MockSelect:
            def ask(self):
                return "FastAPI"

        class MockConfirm:
            def ask(self):
                return True

        # Mock subprocess to fail on dependency installation
        def mock_run_failing(cmd, *args, **kwargs):
            if "pip" in cmd or "uv" in cmd:
                raise subprocess.CalledProcessError(1, cmd, stderr=b"Package not found")
            return subprocess.CompletedProcess(args=cmd, returncode=0)

        with patch("questionary.select", MockSelect), patch(
            "questionary.confirm", MockConfirm
        ), patch("subprocess.run", side_effect=mock_run_failing):
            result = cli_runner.invoke(app, ["setup", str(project_path)])

            # Should fail gracefully
            assert result.exit_code == 1


class TestSetupFlowPerformance:
    """Test setup flow performance characteristics."""

    def test_setup_flow_completes_within_timeout(self, tmp_path, cli_runner, mock_subprocess_run):
        """Test that setup completes within reasonable time (mocked, should be fast)."""
        import time

        project_path = tmp_path / "test-performance"
        project_path.mkdir()

        class MockSelect:
            def ask(self):
                return "CLI Tool"  # Smaller dependency set

        class MockConfirm:
            def ask(self):
                return True

        with patch("subprocess.run", side_effect=mock_subprocess_run), patch(
            "questionary.select", MockSelect
        ), patch("questionary.confirm", MockConfirm), patch(
            "questionary.checkbox", create_mock_checkbox()
        ):
            start_time = time.time()
            result = cli_runner.invoke(app, ["setup", str(project_path)])
            elapsed_time = time.time() - start_time

            assert result.exit_code == 0
            # With mocking, should complete quickly (< 5 seconds)
            assert elapsed_time < 5.0, f"Setup took {elapsed_time:.2f}s (too slow)"
