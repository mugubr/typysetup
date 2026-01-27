"""Integration tests for preference management."""

import json

import pytest

from typysetup.core import PreferenceManager


@pytest.fixture
def temp_prefs_dir(tmp_path):
    """Create a temporary preferences directory."""
    prefs_dir = tmp_path / ".typysetup"
    prefs_dir.mkdir()
    return prefs_dir


@pytest.fixture
def pref_manager(temp_prefs_dir):
    """Create PreferenceManager with temp directory."""
    prefs_file = temp_prefs_dir / "preferences.json"
    return PreferenceManager(preferences_path=prefs_file)


class TestPreferencesIntegration:
    """Integration tests for full preference workflow."""

    def test_first_run_workflow(self, pref_manager):
        """Test the complete first-run workflow."""
        # Load preferences (should create defaults)
        prefs = pref_manager.load_preferences()
        assert prefs.first_run is True
        assert len(prefs.setup_history) == 0

        # Simulate a successful setup
        pref_manager.update_after_setup(
            setup_type_slug="fastapi-api",
            project_path="/home/user/my-project",
            project_name="MyProject",
            python_version="3.11",
            package_manager="uv",
            success=True,
            duration_seconds=45.2,
        )

        # Reload and verify changes persisted
        prefs = pref_manager.load_preferences()
        assert prefs.first_run is False
        assert prefs.preferred_manager == "uv"
        assert prefs.preferred_python_version == "3.11"
        assert "fastapi-api" in prefs.preferred_setup_types
        assert len(prefs.setup_history) == 1

    def test_multiple_setups_workflow(self, pref_manager):
        """Test workflow with multiple setup operations."""
        pref_manager.load_preferences()

        # First setup - FastAPI with uv
        pref_manager.update_after_setup(
            setup_type_slug="fastapi-api",
            project_path="/projects/api1",
            project_name="API1",
            python_version="3.11",
            package_manager="uv",
            success=True,
            duration_seconds=40.0,
        )

        # Second setup - Basic script with pip
        pref_manager.update_after_setup(
            setup_type_slug="basic-script",
            project_path="/projects/script1",
            project_name="Script1",
            python_version="3.10",
            package_manager="pip",
            success=True,
            duration_seconds=15.0,
        )

        # Third setup - FastAPI again with poetry
        pref_manager.update_after_setup(
            setup_type_slug="fastapi-api",
            project_path="/projects/api2",
            project_name="API2",
            python_version="3.12",
            package_manager="poetry",
            success=True,
            duration_seconds=55.0,
        )

        # Verify final state
        prefs = pref_manager.get_preferences()

        # Most recent preferences win
        assert prefs.preferred_manager == "poetry"
        assert prefs.preferred_python_version == "3.12"

        # FastAPI should be first (most recent)
        assert prefs.preferred_setup_types[0] == "fastapi-api"
        assert prefs.preferred_setup_types[1] == "basic-script"

        # All three setups in history
        assert len(prefs.setup_history) == 3
        assert prefs.setup_history[-1].project_name == "API2"

    def test_preferences_survive_reload(self, pref_manager):
        """Test that preferences persist across manager instances."""
        # Set some preferences
        pref_manager.load_preferences()
        pref_manager.update_preference("preferred_manager", "poetry")
        pref_manager.update_preference("preferred_python_version", "3.12")

        # Create new manager instance pointing to same file
        new_manager = PreferenceManager(preferences_path=pref_manager.preferences_path)
        prefs = new_manager.load_preferences()

        assert prefs.preferred_manager == "poetry"
        assert prefs.preferred_python_version == "3.12"

    def test_reset_workflow(self, pref_manager):
        """Test resetting preferences to defaults."""
        # Setup some custom preferences
        pref_manager.load_preferences()
        pref_manager.update_after_setup(
            setup_type_slug="fastapi-api",
            project_path="/project",
            project_name="Project",
            python_version="3.11",
            package_manager="poetry",
            success=True,
        )

        prefs = pref_manager.get_preferences()
        assert prefs.preferred_manager == "poetry"
        assert len(prefs.setup_history) == 1

        # Reset
        pref_manager.reset_to_defaults()

        # Verify defaults restored
        prefs = pref_manager.get_preferences()
        assert prefs.preferred_manager == "uv"
        assert prefs.first_run is True
        assert len(prefs.setup_history) == 0

        # Verify backup was created
        backup_files = list(pref_manager.preferences_path.parent.glob("*.backup_*"))
        assert len(backup_files) > 0

    def test_concurrent_setups(self, pref_manager):
        """Test handling of rapid successive setups."""
        pref_manager.load_preferences()

        # Simulate rapid successive setups
        for i in range(5):
            pref_manager.add_setup_history(
                setup_type_slug=f"type-{i % 3}",
                project_path=f"/project{i}",
                project_name=f"Project {i}",
                python_version="3.11",
                package_manager="uv",
                success=i % 2 == 0,  # Alternate success/failure
                duration_seconds=float(i * 10),
            )

        prefs = pref_manager.get_preferences()
        assert len(prefs.setup_history) == 5

        # Verify mix of success and failure
        successes = [e for e in prefs.setup_history if e.success]
        failures = [e for e in prefs.setup_history if not e.success]
        assert len(successes) == 3
        assert len(failures) == 2

    def test_file_corruption_recovery(self, pref_manager):
        """Test recovery from corrupted preferences file."""
        # Create initial valid preferences
        pref_manager.load_preferences()
        pref_manager.update_preference("preferred_manager", "poetry")

        # Corrupt the file
        with open(pref_manager.preferences_path, "w") as f:
            f.write("{ corrupted json }")

        # Should recover gracefully
        prefs = pref_manager.load_preferences()
        assert prefs.first_run is True  # Defaults restored
        assert prefs.preferred_manager == "uv"  # Default value

        # Backup should exist
        backup_files = list(pref_manager.preferences_path.parent.glob("*.corrupted_*"))
        assert len(backup_files) == 1

    def test_history_limit_enforcement(self, pref_manager):
        """Test that history is properly limited to 20 entries."""
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
                duration_seconds=10.0,
            )

        prefs = pref_manager.get_preferences()

        # Should only have 20 entries (most recent)
        assert len(prefs.setup_history) == 20
        assert prefs.setup_history[-1].project_name == "Project 24"
        assert prefs.setup_history[0].project_name == "Project 5"

    def test_json_file_format(self, pref_manager):
        """Test that saved JSON is valid and readable."""
        pref_manager.load_preferences()
        pref_manager.update_preference("preferred_manager", "poetry")

        # Read raw JSON
        with open(pref_manager.preferences_path) as f:
            data = json.load(f)

        # Verify structure
        assert "preferred_manager" in data
        assert "setup_history" in data
        assert "version" in data
        assert "last_updated" in data

        # Verify values
        assert data["preferred_manager"] == "poetry"
        assert isinstance(data["setup_history"], list)

    def test_failed_setup_recorded(self, pref_manager):
        """Test that failed setups are properly recorded."""
        pref_manager.load_preferences()

        pref_manager.add_setup_history(
            setup_type_slug="fastapi-api",
            project_path="/project",
            project_name="FailedProject",
            python_version="3.11",
            package_manager="uv",
            success=False,
            duration_seconds=5.0,
        )

        prefs = pref_manager.get_preferences()
        assert len(prefs.setup_history) == 1

        entry = prefs.setup_history[0]
        assert entry.success is False
        assert entry.project_name == "FailedProject"
        assert entry.duration_seconds == 5.0
