"""Unit tests for dependency models: DependencyGroup, VersionConstraint, SetupTypeBuilder."""

import pytest

from typysetup.models import (
    ConstraintType,
    DependencyGroup,
    SetupTypeBuilder,
    VersionConstraint,
)


class TestDependencyGroup:
    """Tests for DependencyGroup model."""

    def test_dependency_group_creation(self):
        """Test creating a DependencyGroup."""
        group = DependencyGroup(
            group_name="core",
            packages=["fastapi>=0.104.0", "uvicorn[standard]>=0.24.0"],
        )
        assert group.group_name == "core"
        assert len(group.packages) == 2

    def test_dependency_group_validation_invalid_name(self):
        """Test that invalid group names are rejected."""
        with pytest.raises(ValueError):
            DependencyGroup(
                group_name="Invalid Name",  # Has space
                packages=["fastapi>=0.104.0"],
            )

    def test_dependency_group_validation_invalid_package(self):
        """Test that invalid package format is rejected."""
        with pytest.raises(ValueError):
            DependencyGroup(
                group_name="core",
                packages=["!!!invalid!!!"],
            )

    def test_get_package_names(self):
        """Test extracting package names without versions."""
        group = DependencyGroup(
            group_name="core",
            packages=["fastapi>=0.104.0", "uvicorn[standard]>=0.24.0", "pydantic"],
        )
        names = group.get_package_names()
        assert "fastapi" in names
        assert "uvicorn" in names
        assert "pydantic" in names

    def test_get_package_count(self):
        """Test counting packages."""
        group = DependencyGroup(
            group_name="core",
            packages=["fastapi>=0.104.0", "uvicorn[standard]>=0.24.0"],
        )
        assert group.get_package_count() == 2

    def test_filter_by_version_spec(self):
        """Test filtering packages by version spec."""
        group = DependencyGroup(
            group_name="core",
            packages=["fastapi>=0.104.0", "uvicorn>=0.24.0", "pydantic"],
        )
        versioned = group.filter_by_version_spec(">=")
        assert len(versioned) == 2

    def test_get_readable_description_provided(self):
        """Test getting description when provided."""
        group = DependencyGroup(
            group_name="core",
            packages=["fastapi>=0.104.0"],
            description="Core dependencies",
        )
        assert group.get_readable_description() == "Core dependencies"

    def test_get_readable_description_generated(self):
        """Test getting auto-generated description."""
        group = DependencyGroup(
            group_name="core",
            packages=["fastapi>=0.104.0"],
        )
        desc = group.get_readable_description()
        assert "Core" in desc

    def test_to_installable_format(self):
        """Test getting packages in pip-installable format."""
        group = DependencyGroup(
            group_name="core",
            packages=["fastapi>=0.104.0", "uvicorn[standard]>=0.24.0"],
        )
        installable = group.to_installable_format()
        assert "fastapi" in installable
        assert "uvicorn" in installable


class TestVersionConstraint:
    """Tests for VersionConstraint model."""

    def test_parse_minimum_version_plus(self):
        """Test parsing 3.10+ format."""
        constraint = VersionConstraint.from_string("3.10+")
        assert constraint.constraint_type == ConstraintType.MINIMUM
        assert constraint.min_version == "3.10"
        assert constraint.is_satisfied_by("3.10")
        assert constraint.is_satisfied_by("3.11")
        assert not constraint.is_satisfied_by("3.9")

    def test_parse_version_range(self):
        """Test parsing 3.8-3.11 format."""
        constraint = VersionConstraint.from_string("3.8-3.11")
        assert constraint.constraint_type == ConstraintType.RANGE
        assert constraint.min_version == "3.8"
        assert constraint.max_version == "3.11"
        assert constraint.is_satisfied_by("3.10")
        assert not constraint.is_satisfied_by("3.7")
        assert not constraint.is_satisfied_by("3.12")

    def test_parse_greater_equal(self):
        """Test parsing >=3.9 format."""
        constraint = VersionConstraint.from_string(">=3.9")
        assert constraint.constraint_type == ConstraintType.MINIMUM
        assert constraint.is_satisfied_by("3.9")
        assert constraint.is_satisfied_by("3.10")

    def test_parse_less_equal(self):
        """Test parsing <=3.11 format."""
        constraint = VersionConstraint.from_string("<=3.11")
        assert constraint.constraint_type == ConstraintType.MAXIMUM
        assert constraint.is_satisfied_by("3.10")
        assert not constraint.is_satisfied_by("3.12")

    def test_parse_exact_with_equals(self):
        """Test parsing ==3.10 format."""
        constraint = VersionConstraint.from_string("==3.10")
        assert constraint.constraint_type == ConstraintType.EXACT
        assert constraint.is_satisfied_by("3.10")
        assert not constraint.is_satisfied_by("3.11")

    def test_parse_exact_plain(self):
        """Test parsing plain 3.10 format."""
        constraint = VersionConstraint.from_string("3.10")
        assert constraint.constraint_type == ConstraintType.EXACT
        assert constraint.is_satisfied_by("3.10")

    def test_invalid_format_raises(self):
        """Test that invalid format raises ValueError."""
        with pytest.raises(ValueError):
            VersionConstraint.from_string("python3.10")

    def test_get_readable_format_minimum(self):
        """Test readable format for minimum constraint."""
        constraint = VersionConstraint.from_string("3.10+")
        readable = constraint.get_readable_format()
        assert "3.10" in readable
        assert "or later" in readable

    def test_get_readable_format_range(self):
        """Test readable format for range constraint."""
        constraint = VersionConstraint.from_string("3.8-3.11")
        readable = constraint.get_readable_format()
        assert "3.8" in readable
        assert "3.11" in readable

    def test_version_string_parsing(self):
        """Test parsing version strings."""
        parts = VersionConstraint.parse_version_string("3.10.5")
        assert parts == (3, 10, 5)

    def test_version_string_parsing_invalid(self):
        """Test parsing invalid version string."""
        with pytest.raises(ValueError):
            VersionConstraint.parse_version_string("invalid")


class TestSetupTypeBuilder:
    """Tests for SetupTypeBuilder."""

    def test_builder_basic_construction(self):
        """Test basic builder usage."""
        setup = (
            SetupTypeBuilder()
            .with_name("FastAPI")
            .with_slug("fastapi")
            .with_description("Web API with FastAPI")
            .with_python_version("3.10+")
            .with_supported_managers(["uv", "pip"])
            .add_dependency("core", "fastapi>=0.104.0")
            .build()
        )
        assert setup.name == "FastAPI"
        assert setup.slug == "fastapi"

    def test_builder_add_multiple_dependencies(self):
        """Test adding dependencies in multiple groups."""
        setup = (
            SetupTypeBuilder()
            .with_name("FastAPI")
            .with_slug("fastapi")
            .with_description("Modern Web API Framework")
            .with_python_version("3.10+")
            .with_supported_managers(["uv"])
            .add_dependency("core", "fastapi>=0.104.0")
            .add_dependency("core", "uvicorn>=0.24.0")
            .add_dependency("dev", "pytest>=7.0")
            .build()
        )
        assert len(setup.dependencies["core"]) == 2
        assert len(setup.dependencies["dev"]) == 1

    def test_builder_add_vscode_extensions(self):
        """Test adding VSCode extensions."""
        setup = (
            SetupTypeBuilder()
            .with_name("FastAPI")
            .with_slug("fastapi")
            .with_description("Modern Web API Framework")
            .with_python_version("3.10+")
            .with_supported_managers(["uv"])
            .add_dependency("core", "fastapi>=0.104.0")
            .add_vscode_extension("ms-python.python")
            .add_vscode_extension("ms-python.vscode-pylance")
            .build()
        )
        assert len(setup.vscode_extensions) == 2

    def test_builder_add_tags(self):
        """Test adding tags."""
        setup = (
            SetupTypeBuilder()
            .with_name("FastAPI")
            .with_slug("fastapi")
            .with_description("Modern Web API Framework")
            .with_python_version("3.10+")
            .with_supported_managers(["uv"])
            .add_dependency("core", "fastapi>=0.104.0")
            .add_tags(["web", "api", "async"])
            .build()
        )
        assert "web" in setup.tags
        assert "api" in setup.tags

    def test_builder_missing_name(self):
        """Test that missing name raises error."""
        with pytest.raises(ValueError, match="Name is required"):
            (
                SetupTypeBuilder()
                .with_slug("fastapi")
                .with_description("Modern Web API Framework")
                .with_python_version("3.10+")
                .with_supported_managers(["uv"])
                .add_dependency("core", "fastapi>=0.104.0")
                .build()
            )

    def test_builder_missing_core_dependencies(self):
        """Test that missing core dependencies raises error."""
        with pytest.raises(ValueError, match="Core dependencies"):
            (
                SetupTypeBuilder()
                .with_name("FastAPI")
                .with_slug("fastapi")
                .with_description("Modern Web API Framework")
                .with_python_version("3.10+")
                .with_supported_managers(["uv"])
                .build()
            )

    def test_builder_missing_managers(self):
        """Test that missing managers raises error."""
        with pytest.raises(ValueError, match="Supported managers"):
            (
                SetupTypeBuilder()
                .with_name("FastAPI")
                .with_slug("fastapi")
                .with_description("Modern Web API Framework")
                .with_python_version("3.10+")
                .add_dependency("core", "fastapi>=0.104.0")
                .build()
            )

    def test_builder_reset(self):
        """Test resetting builder."""
        builder = (
            SetupTypeBuilder()
            .with_name("FastAPI")
            .with_slug("fastapi")
            .with_description("Modern Web API Framework")
        )
        builder.reset()

        with pytest.raises(ValueError):
            builder.build()

    def test_builder_fluent_api_chaining(self):
        """Test that fluent API allows chaining."""
        setup = (
            SetupTypeBuilder()
            .with_name("Test")
            .with_slug("test")
            .with_description("Test setup")
            .with_python_version("3.10+")
            .with_supported_managers(["uv"])
            .add_dependency("core", "test-package")
            .add_vscode_setting("python.formatting.provider", "black")
            .add_tag("test")
            .with_docs_url("https://example.com")
            .build()
        )
        assert setup.name == "Test"
        assert setup.docs_url == "https://example.com"
