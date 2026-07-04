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


@pytest.fixture(autouse=True)
def _mock_questionary_text(monkeypatch):
    """Mock questionary.text for project metadata prompts.

    The flow tests mock select/confirm/checkbox but not text; without this the
    non-interactive runner returns None for the project-name prompt and the
    metadata phase aborts before venv creation.
    """

    class MockText:
        def __init__(self, message, **kwargs):
            self.message = message

        def ask(self):
            if "Project name" in self.message:
                return "my_project"
            return ""  # skip optional description/author/email

    monkeypatch.setattr("questionary.text", MockText)


@pytest.fixture(autouse=True)
def _stub_venv_creation(monkeypatch):
    """Stub venv creation (EnvBuilder + pip bootstrap), which is unit-tested separately.

    These flow tests mock subprocess, which is incompatible with real EnvBuilder
    pip bootstrapping; create a minimal venv layout so filesystem assertions hold.
    """
    from typysetup.utils.paths import get_venv_path, get_venv_python_executable

    def fake_create(self, project_path, python_version, project_config):
        venv_path = get_venv_path(project_path)
        py = get_venv_python_executable(venv_path)
        py.parent.mkdir(parents=True, exist_ok=True)
        py.write_text("")
        (venv_path / "pyvenv.cfg").write_text("home = /usr\nversion = 3.11.0\n")
        project_config.venv_path = str(venv_path)
        project_config.python_executable = str(py)
        return True

    monkeypatch.setattr(
        "typysetup.core.venv_manager.VirtualEnvironmentManager.create_virtual_environment",
        fake_create,
    )


def make_select_mock(setup_type_name, package_manager="uv"):
    """Create a questionary.select mock keyed on the prompt message.

    Returns the given setup type name for the setup-type prompt, the given
    package manager for the manager prompt, and the first choice otherwise.
    """

    class MockSelect:
        def __init__(self, message, choices, **kwargs):
            self.message = message
            self.choices = choices

        def ask(self):
            if "setup type" in self.message.lower():
                return setup_type_name
            if "package manager" in self.message.lower():
                return package_manager
            return self.choices[0] if self.choices else None

    return MockSelect


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
        """Mock successful subprocess execution (text output, matching text=True)."""
        cmd_list = cmd if isinstance(cmd, (list, tuple)) else [cmd]
        cmd_str = " ".join(str(c) for c in cmd_list)
        # pip availability check expects "pip X.Y ..." on stdout
        if "--version" in cmd_str and "pip" in cmd_str:
            return subprocess.CompletedProcess(
                args=cmd, returncode=0, stdout="pip 23.3.1 from /venv (python 3.11)\n", stderr=""
            )
        # Python version detection expects "Python X.Y.Z" on stdout
        if "--version" in cmd_str:
            return subprocess.CompletedProcess(
                args=cmd, returncode=0, stdout="Python 3.11.0\n", stderr=""
            )
        return subprocess.CompletedProcess(
            args=cmd, returncode=0, stdout="Successfully installed", stderr=""
        )

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
        with (
            patch("subprocess.run", side_effect=mock_subprocess_run),
            patch("questionary.select", mock_questionary_responses["select"]),
            patch("questionary.confirm", mock_questionary_responses["confirm"]),
            patch("questionary.checkbox", mock_questionary_responses["checkbox"]),
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

    def test_setup_flow_data_science_with_pip(
        self, tmp_path, cli_runner, mock_subprocess_run, mock_questionary_responses, monkeypatch
    ):
        """Test complete setup flow for Data Science with pip."""
        # Arrange
        home_dir = tmp_path / "home"
        home_dir.mkdir()
        monkeypatch.setenv("HOME", str(home_dir))

        project_path = tmp_path / "ml-analysis"
        project_path.mkdir()

        # Act: select Data Science with pip and confirm every prompt
        with (
            patch("subprocess.run", side_effect=mock_subprocess_run),
            patch("questionary.select", make_select_mock("Data Science", "pip")),
            patch("questionary.confirm", mock_questionary_responses["confirm"]),
            patch("questionary.checkbox", mock_questionary_responses["checkbox"]),
        ):
            result = cli_runner.invoke(app, ["setup", str(project_path)])

        # Assert
        assert result.exit_code == 0

        # Verify venv
        assert (project_path / "venv").exists()

        # Verify config
        config_file = project_path / ".typysetup" / "config.json"
        assert config_file.exists()
        config_data = json.loads(config_file.read_text())
        assert config_data["setup_type_slug"] == "data-science"
        assert config_data["package_manager"] == "pip"
        assert config_data["status"] == "success"

    def test_setup_flow_with_verbose_mode(
        self, tmp_path, cli_runner, mock_subprocess_run, mock_questionary_responses, monkeypatch
    ):
        """Test setup flow with verbose output enabled."""
        # Arrange
        home_dir = tmp_path / "home"
        home_dir.mkdir()
        monkeypatch.setenv("HOME", str(home_dir))

        project_path = tmp_path / "test-verbose"
        project_path.mkdir()

        # Act
        with (
            patch("subprocess.run", side_effect=mock_subprocess_run),
            patch("questionary.select", make_select_mock("CLI Tool")),
            patch("questionary.confirm", mock_questionary_responses["confirm"]),
            patch("questionary.checkbox", mock_questionary_responses["checkbox"]),
        ):
            result = cli_runner.invoke(app, ["setup", str(project_path), "--verbose"])

        # Assert: verbose mode should still complete the full flow successfully
        assert result.exit_code == 0
        assert "Setup configuration created successfully" in result.stdout
        assert (project_path / ".typysetup" / "config.json").exists()

    def test_setup_flow_preserves_existing_vscode_settings(
        self, tmp_path, cli_runner, mock_subprocess_run, mock_questionary_responses, monkeypatch
    ):
        """Test that setup preserves existing VSCode settings."""
        # Arrange
        home_dir = tmp_path / "home"
        home_dir.mkdir()
        monkeypatch.setenv("HOME", str(home_dir))

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

        # Act
        with (
            patch("subprocess.run", side_effect=mock_subprocess_run),
            patch("questionary.select", make_select_mock("FastAPI")),
            patch("questionary.confirm", mock_questionary_responses["confirm"]),
            patch("questionary.checkbox", mock_questionary_responses["checkbox"]),
        ):
            result = cli_runner.invoke(app, ["setup", str(project_path)])

        # Assert
        assert result.exit_code == 0

        # Verify settings were merged
        merged_settings = json.loads((vscode_dir / "settings.json").read_text())

        # Existing settings preserved
        assert merged_settings["editor.fontSize"] == 14
        assert merged_settings["workbench.colorTheme"] == "Monokai"

        # Setup settings applied (override)
        assert merged_settings["python.linting.enabled"] is True
        assert "python.defaultInterpreterPath" in merged_settings

    def test_setup_flow_updates_user_preferences(
        self, tmp_path, cli_runner, mock_subprocess_run, mock_questionary_responses, monkeypatch
    ):
        """Test that setup updates user preferences and history."""
        # Arrange: isolate preferences under a temporary HOME
        home_dir = tmp_path / "home"
        home_dir.mkdir()
        monkeypatch.setenv("HOME", str(home_dir))

        project_path = tmp_path / "test-preferences"
        project_path.mkdir()

        # Act
        with (
            patch("subprocess.run", side_effect=mock_subprocess_run),
            patch("questionary.select", make_select_mock("FastAPI", "uv")),
            patch("questionary.confirm", mock_questionary_responses["confirm"]),
            patch("questionary.checkbox", mock_questionary_responses["checkbox"]),
        ):
            result = cli_runner.invoke(app, ["setup", str(project_path)])

        # Assert
        assert result.exit_code == 0

        # Verify preferences were updated (in the isolated HOME)
        prefs = PreferenceManager().load_preferences()

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

        with (
            patch("subprocess.run", side_effect=mock_subprocess_run),
            patch("questionary.select", MockSelect),
            patch("questionary.confirm", MockConfirm),
            patch("questionary.checkbox", create_mock_checkbox()),
        ):
            result = cli_runner.invoke(app, ["setup", non_existent_path])

            # Should handle gracefully (create directory or show error)
            # Exact behavior depends on implementation
            assert result.exit_code in [0, 1]

    def test_setup_flow_multiple_setups_in_sequence(
        self, tmp_path, cli_runner, mock_subprocess_run, mock_questionary_responses, monkeypatch
    ):
        """Test running multiple setups in sequence."""
        # Arrange: isolate preferences under a temporary HOME
        home_dir = tmp_path / "home"
        home_dir.mkdir()
        monkeypatch.setenv("HOME", str(home_dir))

        # First setup: FastAPI
        project1 = tmp_path / "project1"
        project1.mkdir()

        with (
            patch("subprocess.run", side_effect=mock_subprocess_run),
            patch("questionary.select", make_select_mock("FastAPI", "uv")),
            patch("questionary.confirm", mock_questionary_responses["confirm"]),
            patch("questionary.checkbox", mock_questionary_responses["checkbox"]),
        ):
            result1 = cli_runner.invoke(app, ["setup", str(project1)])
            assert result1.exit_code == 0

        # Second setup: Django
        project2 = tmp_path / "project2"
        project2.mkdir()

        with (
            patch("subprocess.run", side_effect=mock_subprocess_run),
            patch("questionary.select", make_select_mock("Django", "pip")),
            patch("questionary.confirm", mock_questionary_responses["confirm"]),
            patch("questionary.checkbox", mock_questionary_responses["checkbox"]),
        ):
            result2 = cli_runner.invoke(app, ["setup", str(project2)])
            assert result2.exit_code == 0

        # Verify both projects configured correctly
        config1 = json.loads((project1 / ".typysetup" / "config.json").read_text())
        config2 = json.loads((project2 / ".typysetup" / "config.json").read_text())

        assert config1["setup_type_slug"] == "fastapi"
        assert config2["setup_type_slug"] == "django"

        # Verify preferences updated with both
        prefs = PreferenceManager().load_preferences()
        assert len(prefs.setup_history) >= 2
        history_slugs = [entry.setup_type_slug for entry in prefs.setup_history]
        assert "fastapi" in history_slugs
        assert "django" in history_slugs


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

        with (
            patch("questionary.select", MockSelect),
            patch("questionary.confirm", MockConfirm),
            patch("venv.EnvBuilder.create", side_effect=mock_create_failing),
        ):
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

        with (
            patch("questionary.select", MockSelect),
            patch("questionary.confirm", MockConfirm),
            patch("subprocess.run", side_effect=mock_run_failing),
        ):
            result = cli_runner.invoke(app, ["setup", str(project_path)])

            # Should fail gracefully
            assert result.exit_code == 1


class TestSetupFlowPerformance:
    """Test setup flow performance characteristics."""

    def test_setup_flow_completes_within_timeout(
        self, tmp_path, cli_runner, mock_subprocess_run, mock_questionary_responses, monkeypatch
    ):
        """Test that setup completes within reasonable time (mocked, should be fast)."""
        import time

        # Arrange
        home_dir = tmp_path / "home"
        home_dir.mkdir()
        monkeypatch.setenv("HOME", str(home_dir))

        project_path = tmp_path / "test-performance"
        project_path.mkdir()

        # Act: CLI Tool has a smaller dependency set
        with (
            patch("subprocess.run", side_effect=mock_subprocess_run),
            patch("questionary.select", make_select_mock("CLI Tool")),
            patch("questionary.confirm", mock_questionary_responses["confirm"]),
            patch("questionary.checkbox", mock_questionary_responses["checkbox"]),
        ):
            start_time = time.time()
            result = cli_runner.invoke(app, ["setup", str(project_path)])
            elapsed_time = time.time() - start_time

        # Assert
        assert result.exit_code == 0
        assert (project_path / ".typysetup" / "config.json").exists()
        # With mocking, should complete quickly (< 5 seconds)
        assert elapsed_time < 5.0, f"Setup took {elapsed_time:.2f}s (too slow)"
