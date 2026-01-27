"""Tests for ConfigLoader."""

from pathlib import Path

import pytest

from typysetup.core.config_loader import ConfigLoader, ConfigLoadError
from typysetup.models import SetupType


@pytest.mark.unit
class TestConfigLoader:
    """Test ConfigLoader class."""

    def test_load_setup_type_valid(self, temp_config_dir: Path, sample_setup_type_data: dict):
        """Test loading a valid setup type configuration."""
        import yaml

        yaml_file = temp_config_dir / "fastapi.yaml"
        with open(yaml_file, "w") as f:
            yaml.dump(sample_setup_type_data, f)

        loader = ConfigLoader(temp_config_dir)
        setup_type = loader.load_setup_type("fastapi")

        assert setup_type.name == "FastAPI"
        assert setup_type.slug == "fastapi"
        assert isinstance(setup_type, SetupType)

    def test_load_setup_type_missing_file(self, temp_config_dir: Path):
        """Test loading a non-existent setup type."""
        loader = ConfigLoader(temp_config_dir)

        with pytest.raises(ConfigLoadError) as exc_info:
            loader.load_setup_type("nonexistent")

        assert "not found" in str(exc_info.value).lower()

    def test_load_setup_type_invalid_yaml(self, temp_config_dir: Path):
        """Test loading an invalid YAML file."""
        yaml_file = temp_config_dir / "invalid.yaml"
        yaml_file.write_text("invalid: yaml: content: [")

        loader = ConfigLoader(temp_config_dir)

        with pytest.raises(ConfigLoadError) as exc_info:
            loader.load_setup_type("invalid")

        assert "yaml" in str(exc_info.value).lower()

    def test_load_setup_type_invalid_config(self, temp_config_dir: Path):
        """Test loading a YAML with invalid configuration."""
        import yaml

        yaml_file = temp_config_dir / "bad_config.yaml"
        invalid_data = {
            "name": "Test",
            "slug": "test",
            # Missing required fields
        }
        with open(yaml_file, "w") as f:
            yaml.dump(invalid_data, f)

        loader = ConfigLoader(temp_config_dir)

        with pytest.raises(ConfigLoadError):
            loader.load_setup_type("bad_config")

    def test_load_all_setup_types(self, temp_config_dir: Path, sample_setup_type_data: dict):
        """Test loading all setup types from directory."""
        import yaml

        # Create multiple setup type files
        yaml_file1 = temp_config_dir / "fastapi.yaml"
        with open(yaml_file1, "w") as f:
            yaml.dump(sample_setup_type_data, f)

        data2 = sample_setup_type_data.copy()
        data2["name"] = "Django"
        data2["slug"] = "django"
        yaml_file2 = temp_config_dir / "django.yaml"
        with open(yaml_file2, "w") as f:
            yaml.dump(data2, f)

        loader = ConfigLoader(temp_config_dir)
        setup_types = loader.load_all_setup_types()

        assert len(setup_types) >= 2
        slugs = [st.slug for st in setup_types]
        assert "fastapi" in slugs
        assert "django" in slugs

    def test_load_all_setup_types_empty_dir(self, temp_config_dir: Path):
        """Test loading from empty directory."""
        loader = ConfigLoader(temp_config_dir)

        with pytest.raises(ConfigLoadError) as exc_info:
            loader.load_all_setup_types()

        # Should raise an error for empty directory
        error_msg = str(exc_info.value).lower()
        assert "no yaml files" in error_msg or "no valid setup types" in error_msg

    def test_cache_setup_type(self, temp_config_dir: Path, sample_setup_type_data: dict):
        """Test that setup types are cached."""
        import yaml

        yaml_file = temp_config_dir / "fastapi.yaml"
        with open(yaml_file, "w") as f:
            yaml.dump(sample_setup_type_data, f)

        loader = ConfigLoader(temp_config_dir)
        setup_type1 = loader.load_setup_type("fastapi")
        setup_type2 = loader.load_setup_type("fastapi")

        assert setup_type1 is setup_type2  # Same object from cache

    def test_clear_cache(self, temp_config_dir: Path, sample_setup_type_data: dict):
        """Test clearing the configuration cache."""
        import yaml

        yaml_file = temp_config_dir / "fastapi.yaml"
        with open(yaml_file, "w") as f:
            yaml.dump(sample_setup_type_data, f)

        loader = ConfigLoader(temp_config_dir)
        setup_type1 = loader.load_setup_type("fastapi")
        loader.clear_cache()
        setup_type2 = loader.load_setup_type("fastapi")

        assert setup_type1 is not setup_type2  # Different objects after cache clear

    def test_list_setup_type_slugs(self, temp_config_dir: Path, sample_setup_type_data: dict):
        """Test listing available setup type slugs."""
        import yaml

        yaml_file1 = temp_config_dir / "fastapi.yaml"
        with open(yaml_file1, "w") as f:
            yaml.dump(sample_setup_type_data, f)

        data2 = sample_setup_type_data.copy()
        data2["slug"] = "django"
        yaml_file2 = temp_config_dir / "django.yaml"
        with open(yaml_file2, "w") as f:
            yaml.dump(data2, f)

        loader = ConfigLoader(temp_config_dir)
        slugs = loader.list_setup_type_slugs()

        assert "fastapi" in slugs
        assert "django" in slugs

    def test_get_setup_type_by_slug_found(
        self, temp_config_dir: Path, sample_setup_type_data: dict
    ):
        """Test getting setup type by slug when it exists."""
        import yaml

        yaml_file = temp_config_dir / "fastapi.yaml"
        with open(yaml_file, "w") as f:
            yaml.dump(sample_setup_type_data, f)

        loader = ConfigLoader(temp_config_dir)
        setup_type = loader.get_setup_type_by_slug("fastapi")

        assert setup_type is not None
        assert setup_type.slug == "fastapi"

    def test_get_setup_type_by_slug_not_found(self, temp_config_dir: Path):
        """Test getting setup type by slug when it doesn't exist."""
        loader = ConfigLoader(temp_config_dir)
        setup_type = loader.get_setup_type_by_slug("nonexistent")

        assert setup_type is None
