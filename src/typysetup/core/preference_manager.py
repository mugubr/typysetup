"""User preference management with atomic file operations."""

import json
import logging
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from pydantic import ValidationError

from typysetup.models.user_preference import SetupHistoryEntry, UserPreference
from typysetup.utils.paths import ensure_config_dir_exists, get_preferences_file_path

logger = logging.getLogger(__name__)


class PreferenceLoadError(Exception):
    """Raised when preferences cannot be loaded."""

    pass


class PreferenceSaveError(Exception):
    """Raised when preferences cannot be saved."""

    pass


class PreferenceManager:
    """Manages user preferences with atomic writes and backup.

    Handles loading, saving, and updating user preferences stored in JSON format.
    Provides atomic write operations to prevent file corruption and automatic
    backup/recovery mechanisms.
    """

    def __init__(self, preferences_path: Optional[Path] = None):
        """Initialize preference manager.

        Args:
            preferences_path: Optional custom path to preferences file.
                If None, uses default from paths.py
        """
        self.preferences_path = preferences_path or get_preferences_file_path()
        self._preferences: Optional[UserPreference] = None

    def load_preferences(self, create_if_missing: bool = True) -> UserPreference:
        """Load user preferences from disk.

        Args:
            create_if_missing: If True, create default preferences if file doesn't exist

        Returns:
            UserPreference instance

        Raises:
            PreferenceLoadError: If preferences cannot be loaded and create_if_missing is False
        """
        # Ensure config directory exists
        try:
            ensure_config_dir_exists()
        except RuntimeError as e:
            raise PreferenceLoadError(f"Cannot create config directory: {e}") from e

        # If file doesn't exist, create defaults
        if not self.preferences_path.exists():
            if create_if_missing:
                logger.info("Preferences file not found, creating defaults")
                self._preferences = UserPreference()
                self.save_preferences(self._preferences)
                return self._preferences
            else:
                raise PreferenceLoadError(f"Preferences file not found: {self.preferences_path}")

        # Try to load existing file
        try:
            with open(self.preferences_path, encoding="utf-8") as f:
                data = json.load(f)

            # Parse timestamps from ISO format
            if "last_updated" in data and isinstance(data["last_updated"], str):
                data["last_updated"] = datetime.fromisoformat(data["last_updated"].rstrip("Z"))

            if "setup_history" in data:
                for entry in data["setup_history"]:
                    if "timestamp" in entry and isinstance(entry["timestamp"], str):
                        entry["timestamp"] = datetime.fromisoformat(entry["timestamp"].rstrip("Z"))

            # Validate with Pydantic model
            self._preferences = UserPreference(**data)
            logger.debug(f"Loaded preferences from {self.preferences_path}")
            return self._preferences

        except json.JSONDecodeError as e:
            # Invalid JSON - backup and create new
            logger.warning(f"Invalid JSON in preferences file: {e}")
            self._backup_corrupted_file()
            self._preferences = UserPreference()
            self.save_preferences(self._preferences)
            return self._preferences

        except ValidationError as e:
            # Schema validation failed - backup and create new
            logger.warning(f"Preference schema validation failed: {e}")
            self._backup_corrupted_file()
            self._preferences = UserPreference()
            self.save_preferences(self._preferences)
            return self._preferences

        except PermissionError as e:
            raise PreferenceLoadError(f"Permission denied reading preferences: {e}") from e

        except Exception as e:
            raise PreferenceLoadError(f"Error loading preferences: {e}") from e

    def save_preferences(self, preferences: UserPreference) -> None:
        """Save preferences to disk with atomic write.

        Writes to a temporary file first, then renames to ensure atomicity.
        Keeps a backup of the previous version.

        Args:
            preferences: UserPreference instance to save

        Raises:
            PreferenceSaveError: If preferences cannot be saved
        """
        # Ensure config directory exists
        try:
            ensure_config_dir_exists()
        except RuntimeError as e:
            raise PreferenceSaveError(f"Cannot create config directory: {e}") from e

        # Update last_updated timestamp
        preferences.last_updated = datetime.utcnow()

        # Create backup of existing file if it exists
        if self.preferences_path.exists():
            backup_path = self.preferences_path.with_suffix(".json.backup")
            try:
                shutil.copy2(self.preferences_path, backup_path)
                logger.debug(f"Created backup at {backup_path}")
            except Exception as e:
                logger.warning(f"Could not create backup: {e}")

        # Write to temporary file first (atomic write)
        temp_path = self.preferences_path.with_suffix(".json.tmp")
        try:
            # Convert to JSON-serializable dict
            data = preferences.model_dump(mode="json")

            with open(temp_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
                f.flush()  # Ensure data is written

            # Atomic rename (overwrites existing file)
            temp_path.replace(self.preferences_path)
            logger.debug(f"Saved preferences to {self.preferences_path}")

            # Update cached instance
            self._preferences = preferences

        except PermissionError as e:
            raise PreferenceSaveError(f"Permission denied writing preferences: {e}") from e

        except Exception as e:
            # Clean up temp file if it exists
            if temp_path.exists():
                try:
                    temp_path.unlink()
                except Exception:
                    pass
            raise PreferenceSaveError(f"Error saving preferences: {e}") from e

    def update_preference(self, key: str, value: Any) -> None:
        """Update a single preference value.

        Args:
            key: Preference key to update
            value: New value for the preference

        Raises:
            PreferenceLoadError: If preferences cannot be loaded
            PreferenceSaveError: If updated preferences cannot be saved
            ValueError: If key is invalid or value fails validation
        """
        # Load current preferences
        prefs = self.load_preferences()

        # Validate key exists in model
        if not hasattr(prefs, key):
            raise ValueError(f"Invalid preference key: {key}")

        # Set new value (Pydantic will validate on assignment)
        try:
            setattr(prefs, key, value)
        except (ValidationError, ValueError) as e:
            raise ValueError(f"Invalid value for {key}: {e}") from e

        # Save updated preferences
        self.save_preferences(prefs)
        logger.debug(f"Updated preference {key} = {value}")

    def add_setup_history(
        self,
        setup_type_slug: str,
        project_path: str,
        project_name: Optional[str],
        python_version: Optional[str],
        package_manager: Optional[str],
        success: bool,
        duration_seconds: Optional[float] = None,
    ) -> None:
        """Add an entry to setup history.

        Args:
            setup_type_slug: Setup type that was used
            project_path: Project directory path
            project_name: Project name
            python_version: Python version used
            package_manager: Package manager used
            success: Whether setup succeeded
            duration_seconds: Setup duration in seconds
        """
        prefs = self.load_preferences()

        entry = SetupHistoryEntry(
            timestamp=datetime.utcnow(),
            setup_type_slug=setup_type_slug,
            project_path=project_path,
            project_name=project_name,
            python_version=python_version,
            package_manager=package_manager,
            success=success,
            duration_seconds=duration_seconds,
        )

        prefs.add_to_history(entry)
        self.save_preferences(prefs)
        logger.info(f"Added setup history entry: {setup_type_slug} at {project_path}")

    def update_after_setup(
        self,
        setup_type_slug: str,
        project_path: str,
        project_name: Optional[str],
        python_version: str,
        package_manager: str,
        success: bool,
        duration_seconds: Optional[float] = None,
    ) -> None:
        """Update preferences after a setup operation.

        Updates preferred manager, Python version, setup types, and adds history entry.

        Args:
            setup_type_slug: Setup type that was used
            project_path: Project directory path
            project_name: Project name
            python_version: Python version used
            package_manager: Package manager used
            success: Whether setup succeeded
            duration_seconds: Setup duration in seconds
        """
        prefs = self.load_preferences()

        # Update preferences
        prefs.update_preferred_manager(package_manager)
        prefs.update_preferred_python_version(python_version)
        prefs.add_preferred_setup_type(setup_type_slug)
        prefs.mark_not_first_run()

        # Add history entry
        entry = SetupHistoryEntry(
            timestamp=datetime.utcnow(),
            setup_type_slug=setup_type_slug,
            project_path=project_path,
            project_name=project_name,
            python_version=python_version,
            package_manager=package_manager,
            success=success,
            duration_seconds=duration_seconds,
        )
        prefs.add_to_history(entry)

        self.save_preferences(prefs)
        logger.info(f"Updated preferences after setup: {setup_type_slug}")

    def reset_to_defaults(self) -> None:
        """Reset preferences to default values.

        Creates a backup of current preferences before resetting.
        """
        # Create backup with timestamp
        if self.preferences_path.exists():
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = self.preferences_path.with_suffix(f".json.backup_{timestamp}")
            try:
                shutil.copy2(self.preferences_path, backup_path)
                logger.info(f"Created backup before reset: {backup_path}")
            except Exception as e:
                logger.warning(f"Could not create backup: {e}")

        # Create and save default preferences
        default_prefs = UserPreference()
        self.save_preferences(default_prefs)
        logger.info("Reset preferences to defaults")

    def _backup_corrupted_file(self) -> None:
        """Backup corrupted preferences file with timestamp."""
        if not self.preferences_path.exists():
            return

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = self.preferences_path.with_suffix(f".json.corrupted_{timestamp}")

        try:
            shutil.copy2(self.preferences_path, backup_path)
            logger.info(f"Backed up corrupted file to {backup_path}")
        except Exception as e:
            logger.warning(f"Could not backup corrupted file: {e}")

    def get_preferences(self) -> UserPreference:
        """Get current preferences, loading if necessary.

        Returns:
            Current UserPreference instance
        """
        if self._preferences is None:
            self._preferences = self.load_preferences()
        return self._preferences

    @property
    def preferences(self) -> UserPreference:
        """Get current preferences (property accessor).

        Returns:
            Current UserPreference instance
        """
        return self.get_preferences()
