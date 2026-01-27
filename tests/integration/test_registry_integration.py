"""Integration tests for setup type registry and configuration system."""

from typysetup.core import ConfigLoader, SetupTypeRegistry, SetupTypeValidator
from typysetup.models import SetupTypeBuilder


class TestPhase3Integration:
    """Integration tests for Phase 3 components."""

    def test_config_loader_with_registry(self):
        """Test ConfigLoader integration with SetupTypeRegistry."""
        loader = ConfigLoader()
        registry = loader.get_registry()

        assert registry is not None
        assert len(registry) == 6
        assert "fastapi" in registry

    def test_registry_validates_all_yaml_configs(self):
        """Test that registry loads and validates all YAML configs."""
        registry = SetupTypeRegistry()
        errors = registry.validate_all()

        # All built-in YAML configs should be valid
        assert len(errors) == 0

    def test_all_six_templates_present_and_valid(self):
        """Test that all 6 setup type templates are present and valid."""
        registry = SetupTypeRegistry()
        slugs = registry.get_slugs()

        expected = [
            "fastapi",
            "django",
            "data-science",
            "cli-tool",
            "async-realtime",
            "ml-ai",
        ]

        for slug in expected:
            assert slug in slugs
            setup_type = registry.get(slug)
            assert setup_type is not None
            result = SetupTypeValidator.validate_setup_type(setup_type)
            assert result["is_valid"]

    def test_each_template_has_minimum_deps(self):
        """Test that each template has at least core dependencies."""
        registry = SetupTypeRegistry()

        for setup_type in registry:
            assert "core" in setup_type.dependencies
            assert len(setup_type.dependencies["core"]) > 0

    def test_each_template_has_vscode_config(self):
        """Test that each template has VSCode configuration."""
        registry = SetupTypeRegistry()

        for setup_type in registry:
            assert setup_type.has_vscode_config()

    def test_registry_filtering_by_manager_consistency(self):
        """Test that manager filtering is consistent across registry."""
        registry = SetupTypeRegistry()

        for manager in ["uv", "pip", "poetry"]:
            types = registry.find_by_manager(manager)
            assert len(types) > 0

            # Verify each returned type supports the manager
            for setup_type in types:
                assert setup_type.supports_manager(manager)

    def test_registry_filtering_by_tags_consistency(self):
        """Test that tag filtering is consistent."""
        registry = SetupTypeRegistry()
        stats = registry.get_stats()

        all_tags = stats.get("tags", [])
        assert len(all_tags) > 0

        for tag in all_tags[:3]:  # Test first 3 tags
            types = registry.find_by_tag(tag)
            assert len(types) > 0

            for setup_type in types:
                assert setup_type.matches_tags([tag])

    def test_registry_python_version_filtering(self):
        """Test Python version compatibility filtering."""
        registry = SetupTypeRegistry()

        # Test with 3.10 (should find most types)
        types_310 = registry.find_by_python_version("3.10.5")
        assert len(types_310) >= 4

        # Test with 3.8 (should find subset - Django)
        types_38 = registry.find_by_python_version("3.8.0")
        assert len(types_38) >= 1

    def test_builder_creates_registerable_type(self):
        """Test that SetupTypeBuilder can create types suitable for registry."""
        setup = (
            SetupTypeBuilder()
            .with_name("Test Type")
            .with_slug("test-type")
            .with_description("Test setup type for validation")
            .with_python_version("3.10+")
            .with_supported_managers(["uv", "pip"])
            .add_dependency("core", "test-package>=1.0")
            .add_vscode_extension("ms-python.python")
            .add_tag("test")
            .build()
        )

        registry = SetupTypeRegistry()
        registry.register(setup)

        assert "test-type" in registry
        retrieved = registry.get("test-type")
        assert retrieved.name == "Test Type"

    def test_validation_pipeline(self):
        """Test complete validation pipeline."""
        loader = ConfigLoader()

        # Load all configs
        types = loader.load_all_setup_types()
        assert len(types) == 6

        # Validate each one
        all_valid = True
        for setup_type in types:
            result = SetupTypeValidator.validate_setup_type(setup_type)
            if not result["is_valid"]:
                all_valid = False

        assert all_valid

    def test_registry_statistics_comprehensive(self):
        """Test getting comprehensive statistics from registry."""
        registry = SetupTypeRegistry()
        stats = registry.get_stats()

        assert stats["total_types"] == 6
        assert stats["total_packages"] > 0
        assert stats["average_dependencies_per_type"] > 0
        assert "manager_support" in stats

        # Each manager should support multiple types
        for manager in ["uv", "pip", "poetry"]:
            assert stats["manager_support"][manager] > 0

    def test_setup_type_analysis_methods(self):
        """Test SetupType analysis methods work correctly."""
        registry = SetupTypeRegistry()
        fastapi = registry.get("fastapi")

        # Test various analysis methods
        assert fastapi.get_total_dependency_count() > 0
        assert len(fastapi.get_dependency_groups()) > 0
        assert fastapi.get_extension_count() > 0
        assert fastapi.requires_python_version("3.10.5")
        assert not fastapi.requires_python_version("3.9.0")

    def test_config_loader_caching(self):
        """Test that ConfigLoader properly caches setup types."""
        loader = ConfigLoader()

        # Load the same type twice
        fastapi1 = loader.load_setup_type("fastapi")
        fastapi2 = loader.load_setup_type("fastapi")

        # Should be the same object (cached)
        assert fastapi1 is fastapi2

    def test_registry_lazy_loading(self):
        """Test that registry uses lazy loading."""
        registry = SetupTypeRegistry()

        # Before accessing, should not be loaded
        assert registry._loaded is False

        # After accessing, should be loaded
        _ = registry.get_all()
        assert registry._loaded is True

    def test_orchestrator_can_use_registry(self):
        """Test that SetupOrchestrator can use registry features."""
        from typysetup.core import ConfigLoader

        loader = ConfigLoader()
        registry = loader.get_registry()

        # Get web-related setup types
        web_types = registry.find_by_tags(["web"])
        assert len(web_types) >= 2

        # Get types supporting Python 3.10+
        modern_types = registry.find_by_python_version("3.10.5")
        assert len(modern_types) > 0

        # Get types supporting uv
        uv_types = registry.find_by_manager("uv")
        assert len(uv_types) > 0

    def test_full_workflow_from_selection_to_validation(self):
        """Test full workflow: select type -> analyze -> validate -> use."""
        registry = SetupTypeRegistry()

        # Select a type
        selected = registry.get("fastapi")
        assert selected is not None

        # Analyze it
        total_deps = selected.get_total_dependency_count()
        groups = selected.get_dependency_groups()
        assert total_deps > 0
        assert "core" in groups

        # Validate it
        result = SetupTypeValidator.validate_setup_type(selected)
        assert result["is_valid"]

        # Use it
        core_deps = selected.get_core_dependencies()
        assert len(core_deps) > 0
