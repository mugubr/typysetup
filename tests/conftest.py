"""Pytest configuration and shared fixtures."""

import json
import tempfile
from pathlib import Path
from typing import Generator

import pytest
from typer.testing import CliRunner

from typysetup.models import ProjectConfiguration, SetupType, UserPreference


@pytest.fixture
def cli_runner() -> CliRunner:
    """Provide a Typer CliRunner for testing CLI commands."""
    return CliRunner()


@pytest.fixture
def temp_project_dir() -> Generator[Path, None, None]:
    """Provide a temporary project directory for testing."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        yield Path(tmp_dir)


@pytest.fixture
def temp_config_dir() -> Generator[Path, None, None]:
    """Provide a temporary directory for test configurations."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        yield Path(tmp_dir)


@pytest.fixture
def sample_setup_type_data() -> dict:
    """Provide sample setup type configuration data."""
    return {
        "name": "FastAPI",
        "slug": "fastapi",
        "description": "Web API with FastAPI framework",
        "python_version": "3.10+",
        "supported_managers": ["uv", "pip", "poetry"],
        "vscode_settings": {
            "python.linting.enabled": True,
            "python.formatting.provider": "black",
        },
        "vscode_extensions": ["ms-python.python"],
        "dependencies": {
            "core": ["fastapi>=0.104.0", "uvicorn[standard]>=0.24.0"],
            "dev": ["pytest>=7.0", "black>=23.0"],
        },
        "tags": ["web", "api", "async"],
    }


@pytest.fixture
def sample_setup_type(sample_setup_type_data: dict) -> SetupType:
    """Provide a sample SetupType instance."""
    return SetupType(**sample_setup_type_data)


@pytest.fixture
def sample_project_config(temp_project_dir: Path) -> ProjectConfiguration:
    """Provide a sample ProjectConfiguration instance."""
    return ProjectConfiguration(
        project_path=str(temp_project_dir),
        setup_type_slug="fastapi",
        python_version="3.11.0",
        python_executable=str(temp_project_dir / "venv" / "bin" / "python"),
        package_manager="uv",
        venv_path=str(temp_project_dir / "venv"),
        status="success",
    )


@pytest.fixture
def sample_user_preference() -> UserPreference:
    """Provide a sample UserPreference instance."""
    pref = UserPreference(
        preferred_manager="uv",
        preferred_python_version="3.11",
        first_run=False,
    )
    pref.add_preferred_setup_type("fastapi")
    return pref


@pytest.fixture
def mock_preferences_file(temp_project_dir: Path) -> Path:
    """Provide a mock preferences file."""
    prefs_file = temp_project_dir / "preferences.json"
    prefs = UserPreference()
    prefs_file.write_text(prefs.json())
    return prefs_file


@pytest.fixture
def mock_setup_type_yaml(temp_config_dir: Path, sample_setup_type_data: dict) -> Path:
    """Provide a mock setup type YAML file."""
    import yaml

    yaml_file = temp_config_dir / "fastapi.yaml"
    with open(yaml_file, "w") as f:
        yaml.dump(sample_setup_type_data, f)
    return yaml_file


@pytest.fixture
def mock_vscode_settings(temp_project_dir: Path) -> Path:
    """Provide a mock VSCode settings.json file."""
    vscode_dir = temp_project_dir / ".vscode"
    vscode_dir.mkdir(exist_ok=True)

    settings_file = vscode_dir / "settings.json"
    settings = {
        "python.defaultInterpreterPath": "${workspaceFolder}/venv/bin/python",
        "python.linting.enabled": True,
    }
    settings_file.write_text(json.dumps(settings, indent=2))
    return settings_file


@pytest.fixture(autouse=True)
def reset_imports():
    """Reset module imports between tests to avoid caching issues."""
    yield
    # Cleanup after test


# Markers for test classification
def pytest_configure(config):
    """Register custom pytest markers."""
    config.addinivalue_line("markers", "unit: Unit tests for individual components")
    config.addinivalue_line("markers", "integration: Integration tests for feature flows")
    config.addinivalue_line("markers", "slow: Slow tests that may take significant time")
