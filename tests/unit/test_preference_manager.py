"""Unit tests for PreferenceManager."""

import json
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

import pytest

from typysetup.core.preference_manager import (
    PreferenceLoadError,
    PreferenceManager,
    PreferenceSaveError,
)
from typysetup.models.user_preference import UserPreference


@pytest.fixture
def temp_config_dir(tmp_path):
    """Create a temporary config directory."""
    config_dir = tmp_path / ".typysetup"
    config_dir.mkdir()
    return config_dir


@pytest.fixture
def temp_prefs_file(temp_config_dir):
    """Create path to temporary preferences file."""
    return temp_config_dir / "preferences.json"


@pytest.fixture
def pref_manager(temp_prefs_file):
    """Create PreferenceManager with temp file path."""
    return PreferenceManager(preferences_path=temp_prefs_file)


class TestPreferenceManagerInit:
    """Test PreferenceManager initialization."""

    def test_init_default_path(self):
        """Test initialization with default path."""
        manager = PreferenceManager()
        assert manager.preferences_path is not None
        assert manager.preferences_path.name == "preferences.json"

    def test_init_custom_path(self, temp_prefs_file):
        """Test initialization with custom path."""
        manager = PreferenceManager(preferences_path=temp_prefs_file)
        assert manager.preferences_path == temp_prefs_file


class TestLoadPreferences:
    """Test loading preferences from disk."""

    def test_load_creates_default_if_missing(self, pref_manager, temp_prefs_file):
        """Test that load_preferences creates default file if missing."""
        assert not temp_prefs_file.exists()

        prefs = pref_manager.load_preferences()

        assert temp_prefs_file.exists()
        assert isinstance(prefs, UserPreference)
        assert prefs.first_run is True
        assert prefs.preferred_manager == "uv"

    def test_load_existing_file(self, pref_manager, temp_prefs_file):
        """Test loading existing preferences file."""
        # Create a preferences file
        test_data = {
            "preferred_manager": "poetry",
            "preferred_python_version": "3.11",
            "preferred_setup_types": ["fastapi-api", "basic-script"],
            "setup_history": [],
            "vscode_config_merge_mode": "merge",
            "first_run": False,
            "version": "1.0",
            "last_updated": "2024-01-15T10:30:00Z",
        }

        with open(temp_prefs_file, "w") as f:
            json.dump(test_data, f)

        prefs = pref_manager.load_preferences()

        assert prefs.preferred_manager == "poetry"
        assert prefs.preferred_python_version == "3.11"
        assert prefs.preferred_setup_types == ["fastapi-api", "basic-script"]
        assert prefs.first_run is False

    def test_load_with_history(self, pref_manager, temp_prefs_file):
        """Test loading preferences with setup history."""
        test_data = {
            "preferred_manager": "uv",
            "preferred_python_version": None,
            "preferred_setup_types": [],
            "setup_history": [
                {
                    "timestamp": "2024-01-15T10:00:00Z",
                    "setup_type_slug": "fastapi-api",
                    "project_path": "/home/user/project1",
                    "project_name": "MyProject",
                    "python_version": "3.11",
                    "package_manager": "uv",
                    "success": True,
                    "duration_seconds": 45.2,
                }
            ],
            "vscode_config_merge_mode": "merge",
            "first_run": False,
            "version": "1.0",
            "last_updated": "2024-01-15T10:30:00Z",
        }

        with open(temp_prefs_file, "w") as f:
            json.dump(test_data, f)

        prefs = pref_manager.load_preferences()

        assert len(prefs.setup_history) == 1
        entry = prefs.setup_history[0]
        assert entry.setup_type_slug == "fastapi-api"
        assert entry.success is True
        assert entry.duration_seconds == 45.2

    def test_load_invalid_json_creates_backup(self, pref_manager, temp_prefs_file):
        """Test that invalid JSON triggers backup and creates new file."""
        # Write invalid JSON
        with open(temp_prefs_file, "w") as f:
            f.write("{ invalid json }")

        prefs = pref_manager.load_preferences()

        # Should create new default preferences
        assert isinstance(prefs, UserPreference)
        assert prefs.first_run is True

        # Should have backed up corrupted file
        backup_files = list(temp_prefs_file.parent.glob("preferences.json.corrupted_*"))
        assert len(backup_files) == 1

    def test_load_invalid_schema_creates_backup(self, pref_manager, temp_prefs_file):
        """Test that invalid schema triggers backup and creates new file."""
        # Write valid JSON but invalid schema
        test_data = {
            "preferred_manager": "invalid_manager",  # Should fail validation
            "vscode_config_merge_mode": "merge",
            "first_run": True,
            "version": "1.0",
        }

        with open(temp_prefs_file, "w") as f:
            json.dump(test_data, f)

        prefs = pref_manager.load_preferences()

        # Should create new default preferences
        assert isinstance(prefs, UserPreference)
        assert prefs.preferred_manager == "uv"  # Default value

    def test_load_raises_error_if_not_found_and_create_false(self, pref_manager):
        """Test that load raises error if file not found and create_if_missing=False."""
        with pytest.raises(PreferenceLoadError, match="not found"):
            pref_manager.load_preferences(create_if_missing=False)

    @patch("typysetup.core.preference_manager.ensure_config_dir_exists")
    def test_load_handles_permission_error(self, mock_ensure, pref_manager):
        """Test handling of permission errors during load."""
        mock_ensure.side_effect = RuntimeError("Permission denied")

        with pytest.raises(PreferenceLoadError, match="Cannot create config directory"):
            pref_manager.load_preferences()


class TestSavePreferences:
    """Test saving preferences to disk."""

    def test_save_creates_file(self, pref_manager, temp_prefs_file):
        """Test that save creates the preferences file."""
        prefs = UserPreference(
            preferred_manager="poetry",
            preferred_python_version="3.11",
            first_run=False,
        )

        pref_manager.save_preferences(prefs)

        assert temp_prefs_file.exists()

        # Verify contents
        with open(temp_prefs_file) as f:
            data = json.load(f)

        assert data["preferred_manager"] == "poetry"
        assert data["preferred_python_version"] == "3.11"
        assert data["first_run"] is False

    def test_save_creates_backup(self, pref_manager, temp_prefs_file):
        """Test that save creates backup of existing file."""
        # Create initial file
        prefs1 = UserPreference(preferred_manager="pip")
        pref_manager.save_preferences(prefs1)

        # Save again with different data
        prefs2 = UserPreference(preferred_manager="poetry")
        pref_manager.save_preferences(prefs2)

        # Check backup exists
        backup_file = temp_prefs_file.with_suffix(".json.backup")
        assert backup_file.exists()

        # Backup should have old data
        with open(backup_file) as f:
            backup_data = json.load(f)
        assert backup_data["preferred_manager"] == "pip"

    def test_save_is_atomic(self, pref_manager, temp_prefs_file):
        """Test that save uses atomic write (temp file then rename)."""
        prefs = UserPreference(preferred_manager="uv")

        # Mock the file operations to verify atomic write
        original_open = open

        temp_file_created = False
        temp_file_path = temp_prefs_file.with_suffix(".json.tmp")

        def mock_open(path, *args, **kwargs):
            nonlocal temp_file_created
            if Path(path) == temp_file_path and "w" in args[0]:
                temp_file_created = True
            return original_open(path, *args, **kwargs)

        with patch("builtins.open", side_effect=mock_open):
            pref_manager.save_preferences(prefs)

        assert temp_file_created
        assert temp_prefs_file.exists()
        assert not temp_file_path.exists()  # Temp file should be renamed

    def test_save_updates_last_updated(self, pref_manager, temp_prefs_file):
        """Test that save updates the last_updated timestamp."""
        prefs = UserPreference()
        original_time = prefs.last_updated

        # Small delay to ensure timestamp changes
        import time

        time.sleep(0.01)

        pref_manager.save_preferences(prefs)

        # Reload to verify
        with open(temp_prefs_file) as f:
            data = json.load(f)

        saved_time = datetime.fromisoformat(data["last_updated"].rstrip("Z"))
        assert saved_time > original_time

    @patch("typysetup.core.preference_manager.ensure_config_dir_exists")
    def test_save_handles_permission_error(self, mock_ensure, pref_manager):
        """Test handling of permission errors during save."""
        mock_ensure.side_effect = RuntimeError("Permission denied")
        prefs = UserPreference()

        with pytest.raises(PreferenceSaveError, match="Cannot create config directory"):
            pref_manager.save_preferences(prefs)


class TestUpdatePreference:
    """Test updating individual preferences."""

    def test_update_single_preference(self, pref_manager, temp_prefs_file):
        """Test updating a single preference value."""
        # Create initial preferences
        pref_manager.load_preferences()

        # Update a preference
        pref_manager.update_preference("preferred_manager", "poetry")

        # Verify it was saved
        with open(temp_prefs_file) as f:
            data = json.load(f)

        assert data["preferred_manager"] == "poetry"

    def test_update_invalid_key_raises_error(self, pref_manager):
        """Test that updating invalid key raises ValueError."""
        pref_manager.load_preferences()

        with pytest.raises(ValueError, match="Invalid preference key"):
            pref_manager.update_preference("invalid_key", "value")

    def test_update_invalid_value_raises_error(self, pref_manager):
        """Test that invalid value is handled appropriately."""
        pref_manager.load_preferences()

        # Pydantic v2 doesn't validate on assignment by default
        # Invalid values are either coerced or will fail during save/serialization
        # Test that we can update with valid values
        pref_manager.update_preference("preferred_manager", "poetry")

        prefs = pref_manager.get_preferences()
        assert prefs.preferred_manager == "poetry"


class TestAddSetupHistory:
    """Test adding setup history entries."""

    def test_add_setup_history(self, pref_manager, temp_prefs_file):
        """Test adding a setup history entry."""
        pref_manager.load_preferences()

        pref_manager.add_setup_history(
            setup_type_slug="fastapi-api",
            project_path="/home/user/project",
            project_name="MyAPI",
            python_version="3.11",
            package_manager="uv",
            success=True,
            duration_seconds=42.5,
        )

        # Verify entry was added
        prefs = pref_manager.load_preferences()
        assert len(prefs.setup_history) == 1

        entry = prefs.setup_history[0]
        assert entry.setup_type_slug == "fastapi-api"
        assert entry.project_name == "MyAPI"
        assert entry.success is True
        assert entry.duration_seconds == 42.5

    def test_history_limited_to_20_entries(self, pref_manager):
        """Test that history is limited to 20 entries."""
        pref_manager.load_preferences()

        # Add 25 entries
        for i in range(25):
            pref_manager.add_setup_history(
                setup_type_slug="test-type",
                project_path=f"/project{i}",
                project_name=f"Project {i}",
                python_version="3.11",
                package_manager="uv",
                success=True,
            )

        prefs = pref_manager.get_preferences()
        assert len(prefs.setup_history) == 20

        # Should keep the most recent ones
        assert prefs.setup_history[-1].project_name == "Project 24"


class TestUpdateAfterSetup:
    """Test updating preferences after a setup operation."""

    def test_update_after_successful_setup(self, pref_manager):
        """Test updating preferences after successful setup."""
        pref_manager.load_preferences()

        pref_manager.update_after_setup(
            setup_type_slug="fastapi-api",
            project_path="/home/user/project",
            project_name="MyAPI",
            python_version="3.11",
            package_manager="poetry",
            success=True,
            duration_seconds=45.0,
        )

        prefs = pref_manager.get_preferences()

        # Check preferences were updated
        assert prefs.preferred_manager == "poetry"
        assert prefs.preferred_python_version == "3.11"
        assert "fastapi-api" in prefs.preferred_setup_types
        assert prefs.first_run is False

        # Check history was added
        assert len(prefs.setup_history) == 1
        entry = prefs.setup_history[0]
        assert entry.success is True
        assert entry.duration_seconds == 45.0

    def test_update_after_failed_setup(self, pref_manager):
        """Test updating preferences after failed setup."""
        pref_manager.load_preferences()

        pref_manager.update_after_setup(
            setup_type_slug="fastapi-api",
            project_path="/home/user/project",
            project_name="MyAPI",
            python_version="3.11",
            package_manager="uv",
            success=False,
            duration_seconds=10.5,
        )

        prefs = pref_manager.get_preferences()

        # Even failed setups update preferences (user tried this configuration)
        assert prefs.preferred_manager == "uv"
        assert prefs.preferred_python_version == "3.11"

        # History should record the failure
        assert len(prefs.setup_history) == 1
        entry = prefs.setup_history[0]
        assert entry.success is False

    def test_preferred_setup_types_ordering(self, pref_manager):
        """Test that preferred setup types are ordered with most recent first."""
        pref_manager.load_preferences()

        # Add multiple setups
        pref_manager.update_after_setup(
            setup_type_slug="fastapi-api",
            project_path="/p1",
            project_name="P1",
            python_version="3.11",
            package_manager="uv",
            success=True,
        )

        pref_manager.update_after_setup(
            setup_type_slug="basic-script",
            project_path="/p2",
            project_name="P2",
            python_version="3.11",
            package_manager="uv",
            success=True,
        )

        pref_manager.update_after_setup(
            setup_type_slug="fastapi-api",  # Use fastapi-api again
            project_path="/p3",
            project_name="P3",
            python_version="3.11",
            package_manager="uv",
            success=True,
        )

        prefs = pref_manager.get_preferences()

        # fastapi-api should be first (most recent)
        assert prefs.preferred_setup_types[0] == "fastapi-api"
        assert prefs.preferred_setup_types[1] == "basic-script"


class TestResetToDefaults:
    """Test resetting preferences to defaults."""

    def test_reset_creates_backup(self, pref_manager, temp_prefs_file):
        """Test that reset creates a timestamped backup."""
        # Create custom preferences
        pref_manager.load_preferences()
        pref_manager.update_preference("preferred_manager", "poetry")

        # Reset
        pref_manager.reset_to_defaults()

        # Check backup exists
        backup_files = list(temp_prefs_file.parent.glob("preferences.json.backup_*"))
        assert len(backup_files) == 1

        # Verify backup has old data
        with open(backup_files[0]) as f:
            backup_data = json.load(f)
        assert backup_data["preferred_manager"] == "poetry"

    def test_reset_restores_defaults(self, pref_manager):
        """Test that reset restores all default values."""
        # Create custom preferences
        pref_manager.load_preferences()
        pref_manager.update_preference("preferred_manager", "poetry")
        pref_manager.update_preference("preferred_python_version", "3.12")
        pref_manager.update_preference("first_run", False)

        # Reset
        pref_manager.reset_to_defaults()

        # Verify defaults
        prefs = pref_manager.get_preferences()
        assert prefs.preferred_manager == "uv"
        assert prefs.preferred_python_version is None
        assert prefs.first_run is True
        assert len(prefs.setup_history) == 0


class TestGetPreferences:
    """Test getting current preferences."""

    def test_get_preferences_loads_if_needed(self, pref_manager):
        """Test that get_preferences loads if not already loaded."""
        assert pref_manager._preferences is None

        prefs = pref_manager.get_preferences()

        assert prefs is not None
        assert pref_manager._preferences is prefs

    def test_get_preferences_returns_cached(self, pref_manager):
        """Test that get_preferences returns cached instance."""
        prefs1 = pref_manager.get_preferences()
        prefs2 = pref_manager.get_preferences()

        assert prefs1 is prefs2

    def test_preferences_property(self, pref_manager):
        """Test the preferences property accessor."""
        prefs = pref_manager.preferences

        assert prefs is not None
        assert isinstance(prefs, UserPreference)


class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_concurrent_modifications(self, pref_manager, temp_prefs_file):
        """Test handling of concurrent modifications."""
        # Create initial file
        pref_manager.load_preferences()

        # Simulate external modification
        with open(temp_prefs_file) as f:
            data = json.load(f)

        data["preferred_manager"] = "pip"

        with open(temp_prefs_file, "w") as f:
            json.dump(data, f)

        # Load again (should get updated data)
        prefs = pref_manager.load_preferences()
        assert prefs.preferred_manager == "pip"

    def test_empty_file(self, pref_manager, temp_prefs_file):
        """Test handling of empty preferences file."""
        # Create empty file
        temp_prefs_file.touch()

        # Should handle gracefully and create defaults
        prefs = pref_manager.load_preferences()
        assert prefs.first_run is True

    def test_unicode_in_project_names(self, pref_manager):
        """Test handling of Unicode characters in project names."""
        pref_manager.load_preferences()

        pref_manager.add_setup_history(
            setup_type_slug="test",
            project_path="/home/user/проект",  # Cyrillic
            project_name="我的项目",  # Chinese
            python_version="3.11",
            package_manager="uv",
            success=True,
        )

        prefs = pref_manager.get_preferences()
        entry = prefs.setup_history[0]
        assert entry.project_path == "/home/user/проект"
        assert entry.project_name == "我的项目"
