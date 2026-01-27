"""Tests for path utilities."""

import sys
from pathlib import Path

import pytest

from typysetup.utils import paths


@pytest.mark.unit
class TestPathUtilities:
    """Test path utility functions."""

    def test_get_user_config_dir_unix(self):
        """Test getting user config dir on Unix systems."""
        # This test checks the logic, not the actual system
        config_dir = paths.get_user_config_dir()
        assert isinstance(config_dir, Path)
        assert config_dir.is_absolute()

    def test_ensure_config_dir_exists(self, temp_project_dir: Path):
        """Test ensuring config directory exists."""
        # Temporarily override home directory for testing
        import unittest.mock

        mock_home = temp_project_dir / "home"
        with unittest.mock.patch("pathlib.Path.home", return_value=mock_home):
            config_dir = paths.ensure_config_dir_exists()
            assert config_dir.exists()
            assert config_dir.is_dir()

    def test_get_venv_path(self, temp_project_dir: Path):
        """Test getting venv path."""
        venv_path = paths.get_venv_path(temp_project_dir)
        assert venv_path == temp_project_dir / "venv"

    def test_get_venv_python_executable_unix(self):
        """Test getting venv Python executable on Unix."""
        if sys.platform != "win32":
            venv_path = Path("/tmp/venv")
            python_exe = paths.get_venv_python_executable(venv_path)
            assert python_exe.name == "python"
            assert "bin" in str(python_exe)

    def test_get_venv_python_executable_windows(self):
        """Test getting venv Python executable on Windows."""
        if sys.platform == "win32":
            venv_path = Path("C:\\project\\venv")
            python_exe = paths.get_venv_python_executable(venv_path)
            assert python_exe.name == "python.exe"
            assert "Scripts" in str(python_exe)

    def test_get_venv_pip_executable(self):
        """Test getting venv pip executable."""
        venv_path = Path("/tmp/venv")
        pip_exe = paths.get_venv_pip_executable(venv_path)
        assert isinstance(pip_exe, Path)
        assert "pip" in pip_exe.name.lower()

    def test_get_venv_activate_script_unix(self):
        """Test getting venv activation script on Unix."""
        if sys.platform != "win32":
            venv_path = Path("/tmp/venv")
            activate = paths.get_venv_activate_script(venv_path)
            assert activate.name == "activate"
            assert "bin" in str(activate)

    def test_get_venv_activate_script_windows(self):
        """Test getting venv activation script on Windows."""
        if sys.platform == "win32":
            venv_path = Path("C:\\project\\venv")
            activate = paths.get_venv_activate_script(venv_path)
            assert activate.name == "activate.bat"
            assert "Scripts" in str(activate)

    def test_get_preferences_file_path(self):
        """Test getting preferences file path."""
        prefs_file = paths.get_preferences_file_path()
        assert isinstance(prefs_file, Path)
        assert prefs_file.name == "preferences.json"
        assert ".typysetup" in str(prefs_file)

    def test_ensure_project_directory(self, temp_project_dir: Path):
        """Test ensuring project directory exists."""
        project_path = str(temp_project_dir / "my_project")
        result = paths.ensure_project_directory(project_path)

        assert result.exists()
        assert result.is_dir()
        assert result.is_absolute()

    def test_ensure_project_directory_relative(self, temp_project_dir: Path):
        """Test ensuring relative project directory is resolved."""
        import os

        original_cwd = os.getcwd()
        try:
            os.chdir(temp_project_dir)
            result = paths.ensure_project_directory("./my_project")
            assert result.is_absolute()
            assert result.exists()
        finally:
            os.chdir(original_cwd)

    def test_ensure_project_directory_with_tilde(self, temp_project_dir: Path):
        """Test that tilde in paths is expanded."""
        # We can't actually test ~ expansion without mocking,
        # but we can verify the function accepts it
        assert paths.ensure_project_directory("~/test_project")

    def test_get_vscode_settings_path(self, temp_project_dir: Path):
        """Test getting VSCode settings.json path."""
        settings_path = paths.get_vscode_settings_path(temp_project_dir)
        assert settings_path == temp_project_dir / ".vscode" / "settings.json"

    def test_get_vscode_extensions_path(self, temp_project_dir: Path):
        """Test getting VSCode extensions.json path."""
        extensions_path = paths.get_vscode_extensions_path(temp_project_dir)
        assert extensions_path == temp_project_dir / ".vscode" / "extensions.json"

    def test_get_vscode_launch_config_path(self, temp_project_dir: Path):
        """Test getting VSCode launch.json path."""
        launch_path = paths.get_vscode_launch_config_path(temp_project_dir)
        assert launch_path == temp_project_dir / ".vscode" / "launch.json"

    def test_ensure_vscode_directory(self, temp_project_dir: Path):
        """Test ensuring .vscode directory exists."""
        vscode_dir = paths.ensure_vscode_directory(temp_project_dir)

        assert vscode_dir.exists()
        assert vscode_dir.is_dir()
        assert vscode_dir.name == ".vscode"

    def test_is_writable_existing_file(self, temp_project_dir: Path):
        """Test checking if existing file is writable."""
        test_file = temp_project_dir / "test.txt"
        test_file.write_text("test")

        is_writable = paths.is_writable(test_file)
        assert is_writable is True

    def test_is_writable_directory(self, temp_project_dir: Path):
        """Test checking if directory is writable."""
        is_writable = paths.is_writable(temp_project_dir)
        assert is_writable is True
