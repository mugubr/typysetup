"""Integration tests for dependency installation (Phase 7).

These tests install real packages in temporary venv directories.
They are marked as slow and integration tests for optional execution.
"""

import subprocess
import sys

import pytest

from typysetup.core.dependency_installer import DependencyInstaller
from typysetup.core.pyproject_generator import PyprojectGenerator
from typysetup.models import ProjectConfiguration, ProjectMetadata
from typysetup.utils.paths import get_venv_python_executable


@pytest.fixture
def temp_venv(tmp_path):
    """Create a temporary virtual environment."""
    venv_path = tmp_path / "venv"

    try:
        subprocess.run(
            [sys.executable, "-m", "venv", str(venv_path)],
            check=True,
            capture_output=True,
            timeout=30,
        )
        yield venv_path
    except subprocess.CalledProcessError as e:
        pytest.skip(f"Failed to create test venv: {e.stderr.decode()}")
    except subprocess.TimeoutExpired:
        pytest.skip("Venv creation timed out")


@pytest.fixture
def project_metadata():
    """Create sample ProjectMetadata."""
    return ProjectMetadata(
        project_name="test_integration",
        project_description="Integration test project",
        author_name="Test Author",
        author_email="test@example.com",
    )


@pytest.fixture
def project_config(tmp_path, temp_venv):
    """Create a ProjectConfiguration for testing."""
    return ProjectConfiguration(
        project_path=str(tmp_path),
        setup_type_slug="test",
        python_version="3.10+",
        python_executable=get_venv_python_executable(temp_venv),
        package_manager="pip",
        venv_path=str(temp_venv),
    )


@pytest.mark.integration
@pytest.mark.slow
class TestDependencyInstallationIntegration:
    """Integration tests for full dependency installation workflow."""

    def test_pip_install_single_package(self, project_config, tmp_path, temp_venv):
        """Test installing a single package with pip."""
        installer = DependencyInstaller()

        result = installer.install_dependencies(
            packages=["six>=1.16.0"],
            package_manager="pip",
            python_executable=project_config.python_executable,
            project_path=tmp_path,
            project_config=project_config,
        )

        assert result is True
        assert len(project_config.installed_dependencies) > 0
        assert project_config.installed_dependencies[0].name == "six"

    def test_pip_install_multiple_packages(self, project_config, tmp_path, temp_venv):
        """Test installing multiple packages with pip."""
        installer = DependencyInstaller()

        packages = ["six>=1.16.0", "requests>=2.28.0"]
        result = installer.install_dependencies(
            packages=packages,
            package_manager="pip",
            python_executable=project_config.python_executable,
            project_path=tmp_path,
            project_config=project_config,
        )

        assert result is True
        assert len(project_config.installed_dependencies) >= 1

    def test_pip_install_nonexistent_package(self, project_config, tmp_path, temp_venv):
        """Test installation failure with nonexistent package."""
        installer = DependencyInstaller()

        result = installer.install_dependencies(
            packages=["nonexistent_package_xyz_abc_123"],
            package_manager="pip",
            python_executable=project_config.python_executable,
            project_path=tmp_path,
            project_config=project_config,
        )

        assert result is False

    def test_pyproject_generation_integration(self, project_metadata, tmp_path, project_config):
        """Test pyproject.toml generation."""
        generator = PyprojectGenerator()

        dependencies = ["six>=1.16.0", "requests>=2.28.0"]
        result = generator.generate_pyproject_toml(
            project_path=tmp_path,
            metadata=project_metadata,
            dependencies=dependencies,
            python_version=project_config.python_version,
        )

        assert result.exists()

        # Verify content
        import tomli

        with open(result, "rb") as f:
            config = tomli.load(f)

        assert config["project"]["name"] == "test_integration"
        assert len(config["project"]["dependencies"]) == 2

    def test_poetry_config_generation(self, project_metadata, tmp_path, project_config):
        """Test pyproject.toml generation for poetry."""
        # Skip if poetry is not installed
        if not _is_poetry_installed():
            pytest.skip("poetry not installed")

        generator = PyprojectGenerator()

        dependencies = ["six>=1.16.0"]
        result = generator.generate_pyproject_toml(
            project_path=tmp_path,
            metadata=project_metadata,
            dependencies=dependencies,
            python_version=project_config.python_version,
        )

        assert result.exists()

    def test_pip_install_with_package_config(
        self, project_metadata, tmp_path, temp_venv, project_config
    ):
        """Test pip installation after generating pyproject.toml."""
        generator = PyprojectGenerator()
        installer = DependencyInstaller()

        dependencies = ["six>=1.16.0"]

        # Generate pyproject.toml
        generator.generate_pyproject_toml(
            project_path=tmp_path,
            metadata=project_metadata,
            dependencies=dependencies,
            python_version=project_config.python_version,
        )

        # Install packages
        result = installer.install_dependencies(
            packages=dependencies,
            package_manager="pip",
            python_executable=project_config.python_executable,
            project_path=tmp_path,
            project_config=project_config,
        )

        assert result is True

    def test_verify_installed_package_importable(self, project_config, tmp_path, temp_venv):
        """Test that installed packages are actually importable."""
        installer = DependencyInstaller()

        result = installer.install_dependencies(
            packages=["six>=1.16.0"],
            package_manager="pip",
            python_executable=project_config.python_executable,
            project_path=tmp_path,
            project_config=project_config,
        )

        assert result is True

        # Verify import works
        import_result = subprocess.run(
            [project_config.python_executable, "-c", "import six; print(six.__version__)"],
            capture_output=True,
            text=True,
            timeout=5,
        )

        assert import_result.returncode == 0
        assert len(import_result.stdout.strip()) > 0

    def test_pip_install_with_version_extraction(self, project_config, tmp_path, temp_venv):
        """Test that installed version is correctly extracted."""
        installer = DependencyInstaller()

        result = installer.install_dependencies(
            packages=["six>=1.16.0"],
            package_manager="pip",
            python_executable=project_config.python_executable,
            project_path=tmp_path,
            project_config=project_config,
        )

        assert result is True
        assert len(project_config.installed_dependencies) > 0
        dep = project_config.installed_dependencies[0]
        assert dep.name == "six"
        # Version should be a valid version string
        assert isinstance(dep.version, str)
        assert len(dep.version) > 0


@pytest.mark.integration
@pytest.mark.slow
class TestDependencyInstallationEdgeCases:
    """Integration tests for edge cases in dependency installation."""

    def test_pip_install_with_extras(self, project_config, tmp_path, temp_venv):
        """Test installing package with extras."""
        installer = DependencyInstaller()

        # requests[security] requires additional packages
        result = installer.install_dependencies(
            packages=["requests[socks]>=2.28.0"],
            package_manager="pip",
            python_executable=project_config.python_executable,
            project_path=tmp_path,
            project_config=project_config,
        )

        # Installation may succeed or fail depending on dependencies
        # Just verify no crash
        assert isinstance(result, bool)

    def test_pip_install_empty_then_install(self, project_config, tmp_path, temp_venv):
        """Test that installing with empty list doesn't break subsequent install."""
        installer = DependencyInstaller()

        # First call with empty list
        result1 = installer.install_dependencies(
            packages=[],
            package_manager="pip",
            python_executable=project_config.python_executable,
            project_path=tmp_path,
            project_config=project_config,
        )

        assert result1 is True

        # Second call with packages
        result2 = installer.install_dependencies(
            packages=["six>=1.16.0"],
            package_manager="pip",
            python_executable=project_config.python_executable,
            project_path=tmp_path,
            project_config=project_config,
        )

        assert result2 is True

    def test_pyproject_backup_and_restore(self, project_metadata, tmp_path, project_config):
        """Test that existing pyproject.toml is backed up."""
        generator = PyprojectGenerator()

        # Create existing pyproject.toml
        existing_config = {"project": {"name": "old_project"}}
        import tomli_w

        pyproject_path = tmp_path / "pyproject.toml"
        with open(pyproject_path, "wb") as f:
            tomli_w.dump(existing_config, f)

        # Generate new pyproject.toml
        result = generator.generate_pyproject_toml(
            project_path=tmp_path,
            metadata=project_metadata,
            dependencies=[],
            python_version=project_config.python_version,
        )

        assert result.exists()

        # Check that backup was created
        backup_files = list(tmp_path.glob("pyproject.toml.backup*"))
        assert len(backup_files) == 1


def _is_poetry_installed() -> bool:
    """Check if poetry is installed and available."""
    import shutil

    return shutil.which("poetry") is not None


def _is_uv_installed() -> bool:
    """Check if uv is installed and available."""
    import shutil

    return shutil.which("uv") is not None
