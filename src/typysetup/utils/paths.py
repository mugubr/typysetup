"""Cross-platform path utilities."""

import logging
import sys
from pathlib import Path

logger = logging.getLogger(__name__)


def get_user_config_dir() -> Path:
    r"""
    Get user configuration directory for TyPySetup.

    Returns ~/.typysetup/ on Unix-like systems or %APPDATA%\typysetup on Windows.

    Returns:
        Path to user config directory
    """
    if sys.platform == "win32":
        # Windows: use APPDATA environment variable
        appdata = Path.home() / "AppData" / "Roaming"
        config_dir = appdata / "typysetup"
    else:
        # Unix-like (Linux, macOS): use ~/.typysetup
        config_dir = Path.home() / ".typysetup"

    return config_dir


def ensure_config_dir_exists() -> Path:
    """
    Ensure user configuration directory exists, creating if necessary.

    Returns:
        Path to user config directory

    Raises:
        RuntimeError: If directory cannot be created
    """
    config_dir = get_user_config_dir()

    try:
        config_dir.mkdir(parents=True, exist_ok=True)
        logger.debug(f"Config directory ensured: {config_dir}")
    except Exception as e:
        raise RuntimeError(f"Failed to create config directory {config_dir}: {e}") from e

    return config_dir


def get_venv_path(project_path: Path) -> Path:
    """
    Get path to virtual environment in project.

    Args:
        project_path: Project directory path

    Returns:
        Path to venv directory (project_path/venv)
    """
    return Path(project_path) / "venv"


def get_venv_python_executable(venv_path: Path) -> Path:
    r"""
    Get path to Python executable in virtual environment.

    Handles cross-platform differences (bin/python on Unix, Scripts\python.exe on Windows).

    Args:
        venv_path: Path to virtual environment

    Returns:
        Path to Python executable
    """
    venv_path = Path(venv_path)

    if sys.platform == "win32":
        return venv_path / "Scripts" / "python.exe"
    else:
        return venv_path / "bin" / "python"


def get_venv_pip_executable(venv_path: Path) -> Path:
    """
    Get path to pip executable in virtual environment.

    Args:
        venv_path: Path to virtual environment

    Returns:
        Path to pip executable
    """
    venv_path = Path(venv_path)

    if sys.platform == "win32":
        return venv_path / "Scripts" / "pip.exe"
    else:
        return venv_path / "bin" / "pip"


def get_venv_activate_script(venv_path: Path) -> Path:
    """
    Get path to venv activation script.

    Args:
        venv_path: Path to virtual environment

    Returns:
        Path to activation script (activate on Unix, activate.bat on Windows)
    """
    venv_path = Path(venv_path)

    if sys.platform == "win32":
        return venv_path / "Scripts" / "activate.bat"
    else:
        return venv_path / "bin" / "activate"


def get_preferences_file_path() -> Path:
    """
    Get path to user preferences JSON file.

    Returns:
        Path to preferences.json in user config directory
    """
    config_dir = get_user_config_dir()
    return config_dir / "preferences.json"


def ensure_project_directory(project_path: str) -> Path:
    """
    Ensure project directory exists.

    Args:
        project_path: Project directory path (can be relative)

    Returns:
        Absolute Path to project directory

    Raises:
        RuntimeError: If directory cannot be created or doesn't have write permissions
    """
    project_path = Path(project_path).expanduser().resolve()

    try:
        project_path.mkdir(parents=True, exist_ok=True)
        logger.debug(f"Project directory ensured: {project_path}")
    except PermissionError as e:
        raise RuntimeError(f"Permission denied: cannot write to {project_path}") from e
    except Exception as e:
        raise RuntimeError(f"Failed to create project directory {project_path}: {e}") from e

    # Check write permissions
    if not project_path.is_dir():
        raise RuntimeError(f"Project path exists but is not a directory: {project_path}")

    try:
        test_file = project_path / ".typysetup_write_test"
        test_file.touch()
        test_file.unlink()
    except PermissionError as e:
        raise RuntimeError(f"No write permissions in {project_path}") from e
    except Exception as e:
        logger.warning(f"Could not test write permissions: {e}")

    return project_path


def get_vscode_settings_path(project_path: Path) -> Path:
    """
    Get path to VSCode settings.json file.

    Args:
        project_path: Project directory path

    Returns:
        Path to .vscode/settings.json
    """
    return Path(project_path) / ".vscode" / "settings.json"


def get_vscode_extensions_path(project_path: Path) -> Path:
    """
    Get path to VSCode extensions.json file.

    Args:
        project_path: Project directory path

    Returns:
        Path to .vscode/extensions.json
    """
    return Path(project_path) / ".vscode" / "extensions.json"


def get_vscode_launch_config_path(project_path: Path) -> Path:
    """
    Get path to VSCode launch.json file.

    Args:
        project_path: Project directory path

    Returns:
        Path to .vscode/launch.json
    """
    return Path(project_path) / ".vscode" / "launch.json"


def ensure_vscode_directory(project_path: Path) -> Path:
    """
    Ensure .vscode directory exists in project.

    Args:
        project_path: Project directory path

    Returns:
        Path to .vscode directory
    """
    vscode_dir = Path(project_path) / ".vscode"

    try:
        vscode_dir.mkdir(parents=True, exist_ok=True)
        logger.debug(f"VSCode directory ensured: {vscode_dir}")
    except Exception as e:
        raise RuntimeError(f"Failed to create .vscode directory: {e}") from e

    return vscode_dir


def is_writable(path: Path) -> bool:
    """
    Check if a path is writable.

    Args:
        path: Path to check

    Returns:
        True if writable, False otherwise
    """
    try:
        if path.exists():
            return bool(path.stat().st_mode & 0o200)
        else:
            # Check parent directory
            return is_writable(path.parent)
    except Exception:
        return False
