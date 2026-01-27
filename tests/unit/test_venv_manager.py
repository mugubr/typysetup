"""Unit tests for VirtualEnvironmentManager."""

import subprocess
import sys
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from typysetup.core.venv_manager import VirtualEnvironmentManager
from typysetup.models import ProjectConfiguration


@pytest.fixture
def venv_manager():
    """Create a VirtualEnvironmentManager instance."""
    return VirtualEnvironmentManager()


@pytest.fixture
def temp_project_dir():
    """Create a temporary project directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def sample_project_config(temp_project_dir):
    """Create a sample ProjectConfiguration."""
    return ProjectConfiguration(
        project_path=str(temp_project_dir),
        setup_type_slug="fastapi",
        python_version="3.10",
        python_executable="",
        package_manager="uv",
        venv_path="",
    )


class TestPythonDiscovery:
    """Tests for Python executable discovery."""

    def test_discover_python_executable_with_specific_version(self, venv_manager):
        """Test discovering Python with specific version."""
        with patch("shutil.which") as mock_which:
            mock_which.side_effect = lambda x: "/usr/bin/python3.11" if x == "python3.11" else None

            with patch.object(venv_manager, "_is_executable_valid", return_value=True):
                result = venv_manager.discover_python_executable("3.11")
                assert result == Path("/usr/bin/python3.11")
                mock_which.assert_called()

    def test_discover_python_executable_fallback_to_generic(self, venv_manager):
        """Test fallback to generic python when specific version not found."""
        with patch("shutil.which") as mock_which:
            # Specific version not found, but generic python is
            def which_side_effect(cmd):
                if cmd == "python3.11":
                    return None
                elif cmd == "python3":
                    return None
                elif cmd == "python":
                    return "/usr/bin/python"
                return None

            mock_which.side_effect = which_side_effect

            with patch.object(venv_manager, "_is_executable_valid", return_value=True):
                result = venv_manager.discover_python_executable("3.11")
                assert result == Path("/usr/bin/python")

    def test_discover_python_executable_fallback_to_sys_executable(self, venv_manager):
        """Test fallback to sys.executable when no python found."""
        with patch("shutil.which", return_value=None):
            result = venv_manager.discover_python_executable("3.11")
            assert result == Path(sys.executable)

    def test_discover_python_version_parsing(self, venv_manager):
        """Test version string parsing in discovery."""
        with patch("shutil.which") as mock_which:
            mock_which.side_effect = lambda x: "/usr/bin/python3.10" if x == "python3.10" else None

            with patch.object(venv_manager, "_is_executable_valid", return_value=True):
                result = venv_manager.discover_python_executable("3.10+")
                assert result == Path("/usr/bin/python3.10")

    def test_discover_python_skips_invalid_executables(self, venv_manager):
        """Test that invalid executables are skipped in favor of valid ones."""
        with patch("shutil.which") as mock_which:
            # Return pyenv shim first, then fallback
            def which_side_effect(cmd):
                if cmd == "python3.10":
                    return "/broken/path/python3.10"  # Invalid
                elif cmd == "python3":
                    return "/usr/bin/python3"  # Valid
                return None

            mock_which.side_effect = which_side_effect

            with patch.object(venv_manager, "_is_executable_valid") as mock_valid:
                # First call returns False (broken), second returns True (valid)
                mock_valid.side_effect = [False, True]

                result = venv_manager.discover_python_executable("3.10")
                # Should skip the broken path and return the valid one
                assert result == Path("/usr/bin/python3")
                assert mock_valid.call_count == 2


class TestExecutableValidation:
    """Tests for Python executable validation."""

    def test_is_executable_valid_success(self, venv_manager):
        """Test valid executable returns True."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="Python 3.10.5\n")

            result = venv_manager._is_executable_valid(Path("/usr/bin/python3"))
            assert result is True

    def test_is_executable_valid_nonzero_exit(self, venv_manager):
        """Test executable with non-zero exit code returns False."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=1, stderr="Error\n")

            result = venv_manager._is_executable_valid(Path("/usr/bin/python3"))
            assert result is False

    def test_is_executable_valid_timeout(self, venv_manager):
        """Test executable with timeout returns False."""
        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = subprocess.TimeoutExpired("cmd", 5)

            result = venv_manager._is_executable_valid(Path("/usr/bin/python3"))
            assert result is False

    def test_is_executable_valid_not_found(self, venv_manager):
        """Test non-existent executable returns False."""
        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = FileNotFoundError()

            result = venv_manager._is_executable_valid(Path("/nonexistent/python"))
            assert result is False


class TestVersionValidation:
    """Tests for Python version validation."""

    def test_validate_python_version_sufficient(self, venv_manager):
        """Test validation when Python version is sufficient."""
        with patch.object(venv_manager, "_get_python_version", return_value="3.11.5"):
            result = venv_manager.validate_python_version(Path("/usr/bin/python"), "3.10")
            assert result is True

    def test_validate_python_version_insufficient(self, venv_manager):
        """Test validation when Python version is insufficient."""
        with patch.object(venv_manager, "_get_python_version", return_value="3.9.0"):
            result = venv_manager.validate_python_version(Path("/usr/bin/python"), "3.10")
            assert result is False

    def test_validate_python_version_exact_match(self, venv_manager):
        """Test validation when versions match exactly."""
        with patch.object(venv_manager, "_get_python_version", return_value="3.10.0"):
            result = venv_manager.validate_python_version(Path("/usr/bin/python"), "3.10")
            assert result is True

    def test_validate_python_version_cannot_determine(self, venv_manager):
        """Test validation when version cannot be determined."""
        with patch.object(venv_manager, "_get_python_version", return_value=None):
            result = venv_manager.validate_python_version(Path("/usr/bin/python"), "3.10")
            assert result is False

    def test_parse_version_various_formats(self, venv_manager):
        """Test version string parsing."""
        assert venv_manager._parse_version("3.11") == (3, 11)
        assert venv_manager._parse_version("3.10.5") == (3, 10)
        assert venv_manager._parse_version("3") == (3, 0)
        assert venv_manager._parse_version("invalid") == (0, 0)


class TestVenvStructureValidation:
    """Tests for virtual environment structure validation."""

    def test_validate_venv_structure_success(self, venv_manager, temp_project_dir):
        """Test successful validation of venv structure."""
        venv_path = temp_project_dir / "venv"
        venv_path.mkdir()

        # Create required files
        (venv_path / "pyvenv.cfg").touch()

        # Create python executable (cross-platform)
        if sys.platform == "win32":
            scripts_dir = venv_path / "Scripts"
            scripts_dir.mkdir()
            (scripts_dir / "python.exe").touch()
        else:
            bin_dir = venv_path / "bin"
            bin_dir.mkdir()
            (bin_dir / "python").touch()

        result = venv_manager.validate_venv_structure(venv_path)
        assert result is True

    def test_validate_venv_structure_missing_config(self, venv_manager, temp_project_dir):
        """Test validation fails when pyvenv.cfg is missing."""
        venv_path = temp_project_dir / "venv"
        venv_path.mkdir()

        result = venv_manager.validate_venv_structure(venv_path)
        assert result is False

    def test_validate_venv_structure_missing_executable(self, venv_manager, temp_project_dir):
        """Test validation fails when Python executable is missing."""
        venv_path = temp_project_dir / "venv"
        venv_path.mkdir()
        (venv_path / "pyvenv.cfg").touch()

        result = venv_manager.validate_venv_structure(venv_path)
        assert result is False

    def test_validate_venv_structure_nonexistent_path(self, venv_manager):
        """Test validation fails for non-existent venv path."""
        result = venv_manager.validate_venv_structure(Path("/nonexistent/venv"))
        assert result is False


class TestVenvExecutableValidation:
    """Tests for venv executable validation."""

    def test_validate_venv_executable_success(self, venv_manager, temp_project_dir):
        """Test successful executable validation."""
        # Create the required directory structure
        venv_path = temp_project_dir / "venv" / "bin"
        venv_path.mkdir(parents=True)
        (venv_path / "python").touch()

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="Python 3.10.5\n")

            result = venv_manager.validate_venv_executable(temp_project_dir / "venv")
            assert result is True

    def test_validate_venv_executable_failure(self, venv_manager, temp_project_dir):
        """Test executable validation when Python fails."""
        # Create the required directory structure
        venv_path = temp_project_dir / "venv" / "bin"
        venv_path.mkdir(parents=True)
        (venv_path / "python").touch()

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=1, stderr="Error")

            result = venv_manager.validate_venv_executable(temp_project_dir / "venv")
            assert result is False

    def test_validate_venv_executable_timeout(self, venv_manager, temp_project_dir):
        """Test executable validation when subprocess times out."""
        import subprocess

        # Create the required directory structure
        venv_path = temp_project_dir / "venv" / "bin"
        venv_path.mkdir(parents=True)
        (venv_path / "python").touch()

        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = subprocess.TimeoutExpired("cmd", 5)

            result = venv_manager.validate_venv_executable(temp_project_dir / "venv")
            assert result is False


class TestPipValidation:
    """Tests for pip availability validation."""

    def test_validate_pip_installed_success(self, venv_manager, temp_project_dir):
        """Test successful pip validation."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0, stdout="pip 23.0 from /venv/lib/site-packages\n"
            )

            result = venv_manager.validate_pip_installed(temp_project_dir / "venv")
            assert result is True

    def test_validate_pip_installed_failure(self, venv_manager, temp_project_dir):
        """Test pip validation when pip is not available."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=1, stderr="pip not found")

            result = venv_manager.validate_pip_installed(temp_project_dir / "venv")
            assert result is False

    def test_validate_pip_installed_not_in_output(self, venv_manager, temp_project_dir):
        """Test pip validation when pip is not in output."""
        # Create the required directory structure
        venv_path = temp_project_dir / "venv" / "bin"
        venv_path.mkdir(parents=True)
        (venv_path / "python").touch()

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="No package manager found\n")

            result = venv_manager.validate_pip_installed(temp_project_dir / "venv")
            assert result is False


class TestUpdateProjectConfig:
    """Tests for ProjectConfiguration updates."""

    def test_update_project_config_with_valid_venv(self, venv_manager, sample_project_config):
        """Test updating ProjectConfiguration with valid venv path."""
        venv_path = Path(sample_project_config.project_path) / "venv"

        venv_manager.update_project_config(sample_project_config, venv_path)

        assert sample_project_config.venv_path == str(venv_path)
        assert "venv" in sample_project_config.python_executable
        # Verify it's the correct cross-platform path
        if sys.platform == "win32":
            assert "Scripts" in sample_project_config.python_executable
            assert "python.exe" in sample_project_config.python_executable
        else:
            assert "bin" in sample_project_config.python_executable
            assert sample_project_config.python_executable.endswith("python")

    def test_update_project_config_overwrites_existing(self, venv_manager, sample_project_config):
        """Test that update overwrites existing paths."""
        sample_project_config.venv_path = "/old/path"
        sample_project_config.python_executable = "/old/python"

        venv_path = Path(sample_project_config.project_path) / "venv"
        venv_manager.update_project_config(sample_project_config, venv_path)

        assert sample_project_config.venv_path == str(venv_path)
        assert sample_project_config.venv_path != "/old/path"


class TestCreateVirtualEnvironment:
    """Tests for complete virtual environment creation."""

    @patch("typysetup.core.venv_manager.EnvBuilder")
    def test_create_virtual_environment_success(
        self, mock_builder_class, venv_manager, temp_project_dir, sample_project_config
    ):
        """Test successful venv creation with all steps."""
        sample_project_config.project_path = str(temp_project_dir)

        # Create the venv directory structure
        venv_path = temp_project_dir / "venv"
        venv_path.mkdir()
        (venv_path / "pyvenv.cfg").touch()
        bin_dir = venv_path / "bin"
        bin_dir.mkdir()
        (bin_dir / "python").touch()

        # Mock the builder
        mock_builder = MagicMock()
        mock_builder_class.return_value = mock_builder

        # Mock discovery and validation methods
        with patch.object(venv_manager, "discover_python_executable") as mock_discover:
            with patch.object(venv_manager, "validate_python_version") as mock_val_version:
                with patch.object(venv_manager, "validate_venv_executable") as mock_val_exe:
                    with patch.object(venv_manager, "validate_pip_installed") as mock_val_pip:
                        mock_discover.return_value = Path("/usr/bin/python3.10")
                        mock_val_version.return_value = True
                        mock_val_exe.return_value = True
                        mock_val_pip.return_value = True

                        result = venv_manager.create_virtual_environment(
                            temp_project_dir,
                            "3.10",
                            sample_project_config,
                        )

        assert result is True
        # Verify ProjectConfiguration was updated
        assert sample_project_config.venv_path != ""
        assert sample_project_config.python_executable != ""

    @patch("typysetup.core.venv_manager.EnvBuilder")
    def test_create_virtual_environment_python_not_found(
        self, mock_builder_class, venv_manager, temp_project_dir, sample_project_config
    ):
        """Test venv creation fails when Python not found."""
        sample_project_config.project_path = str(temp_project_dir)

        with patch.object(venv_manager, "discover_python_executable", return_value=None):
            result = venv_manager.create_virtual_environment(
                temp_project_dir,
                "3.11",
                sample_project_config,
            )

        assert result is False

    @patch("typysetup.core.venv_manager.EnvBuilder")
    def test_create_virtual_environment_version_mismatch(
        self, mock_builder_class, venv_manager, temp_project_dir, sample_project_config
    ):
        """Test venv creation fails on version mismatch."""
        sample_project_config.project_path = str(temp_project_dir)

        with patch.object(venv_manager, "discover_python_executable") as mock_discover:
            with patch.object(venv_manager, "validate_python_version") as mock_val_version:
                mock_discover.return_value = Path("/usr/bin/python3.9")
                mock_val_version.return_value = False

                result = venv_manager.create_virtual_environment(
                    temp_project_dir,
                    "3.10",
                    sample_project_config,
                )

        assert result is False

    @patch("typysetup.core.venv_manager.EnvBuilder")
    def test_create_virtual_environment_structure_invalid(
        self, mock_builder_class, venv_manager, temp_project_dir, sample_project_config
    ):
        """Test venv creation fails on invalid structure."""
        sample_project_config.project_path = str(temp_project_dir)

        # Create minimal venv directory (but validation will fail)
        venv_path = temp_project_dir / "venv"
        venv_path.mkdir()

        mock_builder = MagicMock()
        mock_builder_class.return_value = mock_builder

        with patch.object(venv_manager, "discover_python_executable") as mock_discover:
            with patch.object(venv_manager, "validate_python_version") as mock_val_version:
                with patch.object(venv_manager, "validate_venv_structure") as mock_val_struct:
                    mock_discover.return_value = Path("/usr/bin/python3.10")
                    mock_val_version.return_value = True
                    mock_val_struct.return_value = False

                    result = venv_manager.create_virtual_environment(
                        temp_project_dir,
                        "3.10",
                        sample_project_config,
                    )

        assert result is False

    @patch("venv.EnvBuilder")
    def test_create_virtual_environment_keyboard_interrupt(
        self, mock_builder_class, venv_manager, temp_project_dir, sample_project_config
    ):
        """Test venv creation handles KeyboardInterrupt gracefully."""
        sample_project_config.project_path = str(temp_project_dir)

        with patch.object(venv_manager, "discover_python_executable") as mock_discover:
            mock_discover.side_effect = KeyboardInterrupt()

            result = venv_manager.create_virtual_environment(
                temp_project_dir,
                "3.10",
                sample_project_config,
            )

        assert result is False
