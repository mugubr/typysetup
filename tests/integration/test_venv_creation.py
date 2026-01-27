"""Integration tests for virtual environment creation."""

import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

from typysetup.core.venv_manager import VirtualEnvironmentManager
from typysetup.models import ProjectConfiguration
from typysetup.utils.paths import get_venv_python_executable


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


@pytest.mark.integration
@pytest.mark.slow
@pytest.mark.skipif(
    sys.platform != "win32"
    and not Path("/usr/bin/python3-venv").exists()
    and not Path("/usr/bin/python3").exists(),
    reason="python3-venv package not installed",
)
class TestVenvCreationIntegration:
    """Integration tests for virtual environment creation with real venv."""

    def test_real_venv_creation(self, venv_manager, temp_project_dir, sample_project_config):
        """Test creating an actual virtual environment (no mocking)."""
        sample_project_config.project_path = str(temp_project_dir)

        result = venv_manager.create_virtual_environment(
            temp_project_dir,
            f"{sys.version_info.major}.{sys.version_info.minor}",
            sample_project_config,
        )

        assert result is True

        # Verify venv directory exists
        venv_path = Path(sample_project_config.venv_path)
        assert venv_path.exists()
        assert venv_path.is_dir()

        # Verify pyvenv.cfg exists
        pyvenv_cfg = venv_path / "pyvenv.cfg"
        assert pyvenv_cfg.exists()

    def test_venv_python_executable_exists(
        self, venv_manager, temp_project_dir, sample_project_config
    ):
        """Test that Python executable exists in created venv."""
        sample_project_config.project_path = str(temp_project_dir)

        venv_manager.create_virtual_environment(
            temp_project_dir,
            f"{sys.version_info.major}.{sys.version_info.minor}",
            sample_project_config,
        )

        venv_path = Path(sample_project_config.venv_path)
        python_exe = get_venv_python_executable(venv_path)

        assert python_exe.exists()
        assert python_exe.is_file()

    def test_venv_python_executable_works(
        self, venv_manager, temp_project_dir, sample_project_config
    ):
        """Test that Python executable in venv is functional."""
        sample_project_config.project_path = str(temp_project_dir)

        venv_manager.create_virtual_environment(
            temp_project_dir,
            f"{sys.version_info.major}.{sys.version_info.minor}",
            sample_project_config,
        )

        venv_path = Path(sample_project_config.venv_path)
        python_exe = get_venv_python_executable(venv_path)

        # Try running Python in the venv
        result = subprocess.run(
            [str(python_exe), "--version"],
            capture_output=True,
            text=True,
            timeout=10,
        )

        assert result.returncode == 0
        assert "Python" in result.stdout or "Python" in result.stderr

    def test_venv_pip_available(self, venv_manager, temp_project_dir, sample_project_config):
        """Test that pip is available in created venv."""
        sample_project_config.project_path = str(temp_project_dir)

        venv_manager.create_virtual_environment(
            temp_project_dir,
            f"{sys.version_info.major}.{sys.version_info.minor}",
            sample_project_config,
        )

        venv_path = Path(sample_project_config.venv_path)
        python_exe = get_venv_python_executable(venv_path)

        # Try running pip in the venv
        result = subprocess.run(
            [str(python_exe), "-m", "pip", "--version"],
            capture_output=True,
            text=True,
            timeout=10,
        )

        assert result.returncode == 0
        assert "pip" in result.stdout.lower()

    def test_venv_config_updated(self, venv_manager, temp_project_dir, sample_project_config):
        """Test that ProjectConfiguration is updated after venv creation."""
        original_venv_path = sample_project_config.venv_path
        original_python_exe = sample_project_config.python_executable

        assert original_venv_path == ""
        assert original_python_exe == ""

        sample_project_config.project_path = str(temp_project_dir)

        venv_manager.create_virtual_environment(
            temp_project_dir,
            f"{sys.version_info.major}.{sys.version_info.minor}",
            sample_project_config,
        )

        # Verify paths were updated
        assert sample_project_config.venv_path != ""
        assert sample_project_config.python_executable != ""
        assert "venv" in sample_project_config.venv_path

        if sys.platform == "win32":
            assert "Scripts" in sample_project_config.python_executable
            assert "python.exe" in sample_project_config.python_executable
        else:
            assert "bin" in sample_project_config.python_executable
            assert sample_project_config.python_executable.endswith("python")

    def test_venv_different_versions(self, venv_manager, temp_project_dir, sample_project_config):
        """Test venv creation with different Python versions."""
        # This test uses the current Python version since we can't guarantee others are installed
        sample_project_config.project_path = str(temp_project_dir)
        major, minor = sys.version_info.major, sys.version_info.minor

        result = venv_manager.create_virtual_environment(
            temp_project_dir,
            f"{major}.{minor}",
            sample_project_config,
        )

        assert result is True

        # Verify the created venv has correct Python
        venv_path = Path(sample_project_config.venv_path)
        python_exe = get_venv_python_executable(venv_path)

        result = subprocess.run(
            [str(python_exe), "--version"],
            capture_output=True,
            text=True,
            timeout=10,
        )

        assert result.returncode == 0

    def test_multiple_venv_in_same_project(
        self, venv_manager, temp_project_dir, sample_project_config
    ):
        """Test creating multiple venv instances (one per directory)."""
        major, minor = sys.version_info.major, sys.version_info.minor

        # First venv
        venv_path1 = temp_project_dir / "project1"
        venv_path1.mkdir()
        config1 = ProjectConfiguration(
            project_path=str(venv_path1),
            setup_type_slug="fastapi",
            python_version=f"{major}.{minor}",
            python_executable="",
            package_manager="uv",
            venv_path="",
        )

        result1 = venv_manager.create_virtual_environment(
            venv_path1,
            f"{major}.{minor}",
            config1,
        )

        assert result1 is True

        # Second venv in different directory
        venv_path2 = temp_project_dir / "project2"
        venv_path2.mkdir()
        config2 = ProjectConfiguration(
            project_path=str(venv_path2),
            setup_type_slug="fastapi",
            python_version=f"{major}.{minor}",
            python_executable="",
            package_manager="uv",
            venv_path="",
        )

        result2 = venv_manager.create_virtual_environment(
            venv_path2,
            f"{major}.{minor}",
            config2,
        )

        assert result2 is True

        # Verify both venvs are independent
        assert config1.venv_path != config2.venv_path
        assert (Path(config1.venv_path)).exists()
        assert (Path(config2.venv_path)).exists()

    def test_venv_in_nested_directory(self, venv_manager, temp_project_dir, sample_project_config):
        """Test creating venv in nested directory structure."""
        nested_path = temp_project_dir / "parent" / "child" / "project"
        nested_path.mkdir(parents=True)

        sample_project_config.project_path = str(nested_path)

        result = venv_manager.create_virtual_environment(
            nested_path,
            f"{sys.version_info.major}.{sys.version_info.minor}",
            sample_project_config,
        )

        assert result is True
        assert (nested_path / "venv").exists()

    def test_rollback_on_creation_failure(
        self, venv_manager, temp_project_dir, sample_project_config
    ):
        """Test that rollback cleanup happens on venv creation failure."""
        # This test is harder to do without mocking since we need to force a failure
        # after venv is created. We'll test with a missing Python version instead.
        sample_project_config.project_path = str(temp_project_dir)

        # Try to create venv with non-existent Python version
        result = venv_manager.create_virtual_environment(
            temp_project_dir,
            "99.99",  # Non-existent version
            sample_project_config,
        )

        # Should fail
        assert result is False

        # Verify no partial venv was left behind
        venv_path = temp_project_dir / "venv"
        # Either venv doesn't exist, or if it does, it should be cleaned up by rollback
        # (though in this case it should fail before creation)
        if venv_path.exists():
            # If somehow created, it should be removed by rollback
            assert not venv_path.exists()


@pytest.mark.integration
@pytest.mark.slow
@pytest.mark.skipif(sys.platform == "win32", reason="Unix-specific paths")
class TestVenvUnixPaths:
    """Tests specific to Unix virtual environment paths."""

    def test_unix_venv_structure(self, venv_manager, temp_project_dir, sample_project_config):
        """Test Unix-specific venv structure."""
        sample_project_config.project_path = str(temp_project_dir)

        venv_manager.create_virtual_environment(
            temp_project_dir,
            f"{sys.version_info.major}.{sys.version_info.minor}",
            sample_project_config,
        )

        venv_path = Path(sample_project_config.venv_path)

        # Unix-specific checks
        assert (venv_path / "bin").exists()
        assert (venv_path / "bin" / "python").exists()
        assert (venv_path / "bin" / "pip").exists()


@pytest.mark.integration
@pytest.mark.slow
@pytest.mark.skipif(sys.platform != "win32", reason="Windows-specific paths")
class TestVenvWindowsPaths:
    """Tests specific to Windows virtual environment paths."""

    def test_windows_venv_structure(self, venv_manager, temp_project_dir, sample_project_config):
        """Test Windows-specific venv structure."""
        sample_project_config.project_path = str(temp_project_dir)

        venv_manager.create_virtual_environment(
            temp_project_dir,
            f"{sys.version_info.major}.{sys.version_info.minor}",
            sample_project_config,
        )

        venv_path = Path(sample_project_config.venv_path)

        # Windows-specific checks
        assert (venv_path / "Scripts").exists()
        assert (venv_path / "Scripts" / "python.exe").exists()
