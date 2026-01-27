"""Unit tests for VSCode configuration models."""

import pytest

from typysetup.models import (
    VSCodeConfiguration,
    VSCodeExtension,
    VSCodeLaunchConfiguration,
    VSCodeSettings,
)
from typysetup.models.vscode_config_merge import DeepMergeStrategy


class TestVSCodeSettings:
    """Tests for VSCodeSettings model."""

    def test_vscode_settings_creation(self):
        """Test creating VSCode settings."""
        settings_dict = {
            "python.linting.enabled": True,
            "python.formatting.provider": "black",
            "editor.formatOnSave": True,
        }
        settings = VSCodeSettings(**settings_dict)
        assert settings.model_dump() == settings_dict

    def test_vscode_settings_nested_dict(self):
        """Test settings with nested objects."""
        settings_dict = {
            "editor.rulers": [80, 120],
            "[python]": {"editor.defaultFormatter": "ms-python.python"},
        }
        settings = VSCodeSettings(**settings_dict)
        dumped = settings.model_dump()
        assert dumped["editor.rulers"] == [80, 120]
        assert dumped["[python]"]["editor.defaultFormatter"] == "ms-python.python"

    def test_vscode_settings_empty(self):
        """Test empty VSCode settings."""
        settings = VSCodeSettings()
        assert len(settings.__dict__) == 0


class TestVSCodeExtension:
    """Tests for VSCodeExtension model."""

    def test_vscode_extension_valid(self):
        """Test creating valid VSCode extension."""
        ext = VSCodeExtension(extension_id="ms-python.python")
        assert ext.extension_id == "ms-python.python"
        assert ext.enabled is True

    def test_vscode_extension_disabled(self):
        """Test creating disabled VSCode extension."""
        ext = VSCodeExtension(extension_id="ms-python.python", enabled=False)
        assert ext.extension_id == "ms-python.python"
        assert ext.enabled is False

    def test_vscode_extension_invalid_format(self):
        """Test that invalid extension IDs are rejected."""
        with pytest.raises(ValueError):
            VSCodeExtension(extension_id="invalid-format")

    def test_vscode_extension_invalid_characters(self):
        """Test that invalid characters in extension ID are rejected."""
        with pytest.raises(ValueError):
            VSCodeExtension(extension_id="publisher@name")


class TestVSCodeLaunchConfiguration:
    """Tests for VSCodeLaunchConfiguration model."""

    def test_launch_config_creation(self):
        """Test creating launch configuration."""
        config = VSCodeLaunchConfiguration(
            name="Python: FastAPI",
            type="python",
            request="launch",
            module="uvicorn",
            args=["main:app", "--reload"],
        )
        assert config.name == "Python: FastAPI"
        assert config.type == "python"
        assert config.request == "launch"

    def test_launch_config_default_request(self):
        """Test launch configuration with default request."""
        config = VSCodeLaunchConfiguration(
            name="Python: Debug",
            type="python",
        )
        assert config.request == "launch"


class TestVSCodeConfiguration:
    """Tests for VSCodeConfiguration model."""

    def test_vscode_configuration_creation(self):
        """Test creating complete VSCode configuration."""
        config = VSCodeConfiguration(
            settings={"python.linting.enabled": True},
            extensions=["ms-python.python"],
            launch_configurations=[{"name": "Python", "type": "python", "request": "launch"}],
        )
        assert config.settings == {"python.linting.enabled": True}
        assert config.extensions == ["ms-python.python"]
        assert len(config.launch_configurations) == 1

    def test_vscode_configuration_empty(self):
        """Test creating empty VSCode configuration."""
        config = VSCodeConfiguration()
        assert config.settings == {}
        assert config.extensions == []
        assert config.launch_configurations == []

    def test_get_settings_dict(self):
        """Test getting settings as dictionary."""
        config = VSCodeConfiguration(settings={"python.linting.enabled": True})
        result = config.get_settings_dict()
        assert result == {"python.linting.enabled": True}

    def test_get_extensions_dict(self):
        """Test getting extensions in VSCode format."""
        config = VSCodeConfiguration(extensions=["ms-python.python", "charliermarsh.ruff"])
        result = config.get_extensions_dict()
        assert result == {"recommendations": ["ms-python.python", "charliermarsh.ruff"]}

    def test_get_launch_dict(self):
        """Test getting launch config in VSCode format."""
        config = VSCodeConfiguration(
            launch_configurations=[{"name": "Python", "type": "python", "request": "launch"}]
        )
        result = config.get_launch_dict()
        assert result["version"] == "0.2.0"
        assert len(result["configurations"]) == 1

    def test_merge_with_settings(self):
        """Test merging configurations with settings."""
        config1 = VSCodeConfiguration(settings={"editor.formatOnSave": False})
        config2 = VSCodeConfiguration(settings={"python.linting.enabled": True})
        merged = config1.merge_with(config2)
        assert merged.settings["editor.formatOnSave"] is False
        assert merged.settings["python.linting.enabled"] is True

    def test_merge_with_extensions(self):
        """Test merging configurations with extensions."""
        config1 = VSCodeConfiguration(extensions=["ms-python.python"])
        config2 = VSCodeConfiguration(extensions=["ms-python.python", "charliermarsh.ruff"])
        merged = config1.merge_with(config2)
        assert len(merged.extensions) == 2
        assert "ms-python.python" in merged.extensions
        assert "charliermarsh.ruff" in merged.extensions


class TestDeepMergeStrategy:
    """Tests for deep merge strategy."""

    def test_deep_merge_simple(self):
        """Test merging simple dictionaries."""
        existing = {"a": 1, "b": 2}
        new = {"b": 3, "c": 4}
        result = DeepMergeStrategy.deep_merge_dicts(existing, new)
        assert result == {"a": 1, "b": 3, "c": 4}

    def test_deep_merge_nested(self):
        """Test merging nested dictionaries."""
        existing = {"python": {"linting": {"enabled": False}}}
        new = {"python": {"linting": {"maxLineLength": 100}}}
        result = DeepMergeStrategy.deep_merge_dicts(existing, new)
        assert result["python"]["linting"]["enabled"] is False
        assert result["python"]["linting"]["maxLineLength"] == 100

    def test_deep_merge_language_settings(self):
        """Test merging language-specific settings."""
        existing = {"[python]": {"editor.tabSize": 4}}
        new = {"[python]": {"editor.defaultFormatter": "ms-python.python"}}
        result = DeepMergeStrategy.deep_merge_dicts(existing, new)
        assert result["[python]"]["editor.tabSize"] == 4
        assert result["[python]"]["editor.defaultFormatter"] == "ms-python.python"

    def test_deep_merge_precedence(self):
        """Test that new values take precedence."""
        existing = {"python.linting.enabled": False}
        new = {"python.linting.enabled": True}
        result = DeepMergeStrategy.deep_merge_dicts(existing, new)
        assert result["python.linting.enabled"] is True

    def test_deduplicate_extensions(self):
        """Test extension deduplication."""
        existing = ["ms-python.python", "charliermarsh.ruff"]
        new = ["ms-python.python", "ms-python.vscode-pylance"]
        result = DeepMergeStrategy.deduplicate_extensions(existing, new)
        assert len(result) == 3
        assert result[0] == "ms-python.python"
        assert result[1] == "charliermarsh.ruff"
        assert result[2] == "ms-python.vscode-pylance"

    def test_deduplicate_extensions_empty(self):
        """Test deduplication with empty lists."""
        result = DeepMergeStrategy.deduplicate_extensions([], ["ext1", "ext2"])
        assert result == ["ext1", "ext2"]

    def test_merge_launch_configurations(self):
        """Test merging launch configurations."""
        existing = [{"name": "Python", "type": "python"}]
        new = [{"name": "Python", "type": "python", "module": "uvicorn"}]
        result = DeepMergeStrategy.merge_launch_configurations(existing, new)
        assert len(result) == 1
        assert result[0]["module"] == "uvicorn"

    def test_detect_overrides(self):
        """Test detecting configuration overrides."""
        existing = {"python.linting.enabled": False, "editor.formatOnSave": True}
        new = {"python.linting.enabled": True}
        overrides = DeepMergeStrategy.detect_overrides(existing, new)
        assert "python.linting.enabled" in overrides
        assert overrides["python.linting.enabled"] == (False, True)
        assert "editor.formatOnSave" not in overrides
