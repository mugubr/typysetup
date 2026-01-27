"""Unit tests for setup type registry and utility classes."""

import pytest

from typysetup.core import (
    SetupTypeComparator,
    SetupTypeFilter,
    SetupTypeRegistry,
    SetupTypeValidator,
)
from typysetup.models import SetupTypeBuilder


@pytest.fixture
def sample_setup_types():
    """Create sample setup types for testing."""
    fastapi = (
        SetupTypeBuilder()
        .with_name("FastAPI")
        .with_slug("fastapi")
        .with_description("Web API with FastAPI")
        .with_python_version("3.10+")
        .with_supported_managers(["uv", "pip", "poetry"])
        .add_dependency("core", "fastapi>=0.104.0")
        .add_dependency("core", "uvicorn[standard]>=0.24.0")
        .add_dependency("dev", "pytest>=7.0")
        .add_vscode_extension("ms-python.python")
        .add_tags(["web", "api", "async"])
        .with_docs_url("https://fastapi.tiangolo.com")
        .build()
    )

    django = (
        SetupTypeBuilder()
        .with_name("Django")
        .with_slug("django")
        .with_description("Full-stack web framework")
        .with_python_version("3.8+")
        .with_supported_managers(["pip", "poetry"])
        .add_dependency("core", "django>=4.2")
        .add_dependency("dev", "pytest>=7.0")
        .add_vscode_extension("ms-python.python")
        .add_tags(["web", "orm"])
        .build()
    )

    data_science = (
        SetupTypeBuilder()
        .with_name("Data Science")
        .with_slug("data-science")
        .with_description("Jupyter-based data analysis")
        .with_python_version("3.9+")
        .with_supported_managers(["uv", "pip"])
        .add_dependency("core", "pandas>=2.0")
        .add_dependency("core", "jupyter>=1.0")
        .add_vscode_extension("ms-toolsai.jupyter")
        .add_tags(["data", "jupyter"])
        .build()
    )

    return [fastapi, django, data_science]


class TestSetupTypeRegistry:
    """Tests for SetupTypeRegistry."""

    def test_registry_initialization(self):
        """Test registry can be initialized."""
        registry = SetupTypeRegistry()
        assert registry is not None

    def test_registry_loads_setup_types(self):
        """Test that registry loads setup types from config loader."""
        registry = SetupTypeRegistry()
        all_types = registry.get_all()
        assert len(all_types) == 6  # 6 YAML files

    def test_registry_get_by_slug(self):
        """Test getting setup type by slug."""
        registry = SetupTypeRegistry()
        fastapi = registry.get("fastapi")
        assert fastapi is not None
        assert fastapi.name == "FastAPI"

    def test_registry_get_nonexistent(self):
        """Test getting nonexistent setup type."""
        registry = SetupTypeRegistry()
        result = registry.get("nonexistent")
        assert result is None

    def test_registry_find_by_tag(self):
        """Test finding setup types by tag."""
        registry = SetupTypeRegistry()
        web_types = registry.find_by_tag("web")
        assert len(web_types) > 0
        assert all("web" in st.tags for st in web_types)

    def test_registry_find_by_manager(self):
        """Test finding setup types by package manager."""
        registry = SetupTypeRegistry()
        uv_types = registry.find_by_manager("uv")
        assert len(uv_types) > 0
        assert all("uv" in st.supported_managers for st in uv_types)

    def test_registry_find_by_python_version(self):
        """Test finding setup types by Python version."""
        registry = SetupTypeRegistry()
        types = registry.find_by_python_version("3.10.5")
        # Should find types compatible with 3.10.5
        assert len(types) > 0

    def test_registry_search(self):
        """Test searching setup types."""
        registry = SetupTypeRegistry()
        results = registry.search("fastapi")
        assert len(results) > 0
        assert "fastapi" in [st.slug for st in results]

    def test_registry_get_stats(self):
        """Test getting registry statistics."""
        registry = SetupTypeRegistry()
        stats = registry.get_stats()
        assert "total_types" in stats
        assert stats["total_types"] == 6

    def test_registry_validate_all(self):
        """Test validating all setup types."""
        registry = SetupTypeRegistry()
        errors = registry.validate_all()
        # Should not have errors for built-in types
        assert len(errors) == 0

    def test_registry_contains(self):
        """Test checking if setup type exists."""
        registry = SetupTypeRegistry()
        assert "fastapi" in registry
        assert "nonexistent" not in registry

    def test_registry_getitem(self):
        """Test accessing setup type with bracket notation."""
        registry = SetupTypeRegistry()
        fastapi = registry["fastapi"]
        assert fastapi.name == "FastAPI"

    def test_registry_getitem_missing(self):
        """Test that missing setup type raises KeyError."""
        registry = SetupTypeRegistry()
        with pytest.raises(KeyError):
            _ = registry["nonexistent"]

    def test_registry_len(self):
        """Test getting registry length."""
        registry = SetupTypeRegistry()
        assert len(registry) == 6

    def test_registry_iteration(self):
        """Test iterating over setup types."""
        registry = SetupTypeRegistry()
        types = list(registry)
        assert len(types) == 6

    def test_registry_clear_cache(self):
        """Test clearing registry cache."""
        registry = SetupTypeRegistry()
        registry.clear_cache()
        # Should reload on next access
        assert len(registry) == 6


class TestSetupTypeComparator:
    """Tests for SetupTypeComparator."""

    def test_compare_dependencies(self, sample_setup_types):
        """Test comparing dependencies between setup types."""
        fastapi, django, _ = sample_setup_types
        result = SetupTypeComparator.compare_dependencies(fastapi, django)

        assert "common_dependencies" in result
        assert "unique_to_first" in result
        assert "unique_to_second" in result

    def test_compare_managers(self, sample_setup_types):
        """Test comparing managers between setup types."""
        fastapi, django, _ = sample_setup_types
        result = SetupTypeComparator.compare_managers(fastapi, django)

        assert "common_managers" in result
        assert "fully_compatible" in result
        # They don't support all the same managers
        assert not result["fully_compatible"]

    def test_compare_python_versions(self, sample_setup_types):
        """Test comparing Python versions."""
        fastapi, django, _ = sample_setup_types
        result = SetupTypeComparator.compare_python_versions(fastapi, django)
        assert isinstance(result, str)
        assert "3.10" in result


class TestSetupTypeFilter:
    """Tests for SetupTypeFilter."""

    def test_filter_by_tags_single(self, sample_setup_types):
        """Test filtering by a single tag."""
        result = SetupTypeFilter.filter_by_tags(sample_setup_types, ["web"])
        assert len(result) == 2  # FastAPI and Django

    def test_filter_by_tags_multiple_match_any(self, sample_setup_types):
        """Test filtering by multiple tags (match any)."""
        result = SetupTypeFilter.filter_by_tags(
            sample_setup_types, ["web", "data"], match_all=False
        )
        assert len(result) == 3  # All three

    def test_filter_by_manager(self, sample_setup_types):
        """Test filtering by package manager."""
        result = SetupTypeFilter.filter_by_manager(sample_setup_types, "uv")
        assert len(result) == 2  # FastAPI and Data Science

    def test_filter_by_python_version(self, sample_setup_types):
        """Test filtering by Python version."""
        result = SetupTypeFilter.filter_by_python_version(sample_setup_types, "3.10.5")
        assert len(result) == 3  # All match: FastAPI (3.10+), Django (3.8+), Data Science (3.9+)

    def test_filter_by_min_dependencies(self, sample_setup_types):
        """Test filtering by minimum dependency count."""
        result = SetupTypeFilter.filter_by_min_dependencies(sample_setup_types, 2)
        # All have at least 2 dependencies
        assert len(result) == 3

    def test_filter_by_vscode_support(self, sample_setup_types):
        """Test filtering by VSCode support."""
        result = SetupTypeFilter.filter_by_vscode_support(sample_setup_types)
        # All have VSCode extensions
        assert len(result) == 3

    def test_rank_by_relevance_exact(self, sample_setup_types):
        """Test ranking by relevance (exact match)."""
        result = SetupTypeFilter.rank_by_relevance(sample_setup_types, "fastapi")
        assert result[0].name == "FastAPI"

    def test_rank_by_relevance_partial(self, sample_setup_types):
        """Test ranking by relevance (partial match)."""
        result = SetupTypeFilter.rank_by_relevance(sample_setup_types, "api")
        # FastAPI should rank higher than Django
        assert result[0].name == "FastAPI"

    def test_apply_multiple_filters(self, sample_setup_types):
        """Test applying multiple filters."""
        filters = {
            "tags": ["web"],
            "manager": "pip",
        }
        result = SetupTypeFilter.apply_multiple_filters(sample_setup_types, filters)
        # Both FastAPI and Django have web tag and pip support
        assert len(result) == 2


class TestSetupTypeValidator:
    """Tests for SetupTypeValidator."""

    def test_validate_valid_setup_type(self, sample_setup_types):
        """Test validating a valid setup type."""
        fastapi = sample_setup_types[0]
        result = SetupTypeValidator.validate_setup_type(fastapi)
        assert result["is_valid"]

    def test_validate_returns_warnings(self, sample_setup_types):
        """Test that validation may return warnings."""
        # Create a minimal setup type
        minimal = (
            SetupTypeBuilder()
            .with_name("Minimal")
            .with_slug("minimal")
            .with_description("Minimal setup")
            .with_python_version("3.10+")
            .with_supported_managers(["pip"])
            .add_dependency("core", "minimal-package")
            .build()
        )
        result = SetupTypeValidator.validate_setup_type(minimal)
        assert len(result["warnings"]) > 0

    def test_validate_python_compatibility(self, sample_setup_types):
        """Test Python version compatibility validation."""
        fastapi = sample_setup_types[0]
        assert SetupTypeValidator.validate_python_compatibility(fastapi, "3.10.5")
        assert not SetupTypeValidator.validate_python_compatibility(fastapi, "3.9.0")

    def test_validate_manager_compatibility(self, sample_setup_types):
        """Test manager compatibility validation."""
        fastapi = sample_setup_types[0]
        assert SetupTypeValidator.validate_manager_compatibility(fastapi, "uv")
        assert SetupTypeValidator.validate_manager_compatibility(fastapi, "pip")
        assert not SetupTypeValidator.validate_manager_compatibility(fastapi, "conda")
