"""Unit tests for selection models: DependencySelection and ProjectMetadata."""

import pytest

from typysetup.models import DependencySelection, ProjectMetadata, SetupTypeBuilder


class TestDependencySelection:
    """Tests for DependencySelection model."""

    @pytest.fixture
    def sample_setup_type(self):
        """Create a sample setup type for testing."""
        return (
            SetupTypeBuilder()
            .with_name("FastAPI")
            .with_slug("fastapi")
            .with_description("Web API with FastAPI")
            .with_python_version("3.10+")
            .with_supported_managers(["uv", "pip"])
            .add_dependency("core", "fastapi>=0.104.0")
            .add_dependency("core", "uvicorn[standard]>=0.24.0")
            .add_dependency("dev", "pytest>=7.0")
            .add_dependency("optional", "httpx>=0.24.0")
            .build()
        )

    def test_dependency_selection_creation(self, sample_setup_type):
        """Test creating a DependencySelection."""
        selection = DependencySelection(
            setup_type_slug="fastapi",
            selected_groups={"core": True, "dev": True, "optional": False},
            all_packages=["fastapi>=0.104.0", "uvicorn[standard]>=0.24.0", "pytest>=7.0"],
        )
        assert selection.setup_type_slug == "fastapi"
        assert selection.get_total_package_count() == 3

    def test_core_must_be_selected(self):
        """Test that core group must be selected."""
        from pydantic_core import ValidationError

        with pytest.raises((ValueError, ValidationError)):
            DependencySelection(
                setup_type_slug="fastapi",
                selected_groups={"core": False, "dev": True},
                all_packages=[],
            )

    def test_core_cannot_be_absent(self):
        """Test that core group cannot be missing from selection."""
        with pytest.raises(ValueError, match="Core dependencies must be selected"):
            DependencySelection(
                setup_type_slug="fastapi",
                selected_groups={"dev": True, "optional": False},
                all_packages=[],
            )

    def test_get_selected_groups(self):
        """Test getting list of selected group names."""
        selection = DependencySelection(
            setup_type_slug="fastapi",
            selected_groups={"core": True, "dev": True, "optional": False},
            all_packages=["pkg1", "pkg2"],
        )
        selected = selection.get_selected_groups()
        assert "core" in selected
        assert "dev" in selected
        assert "optional" not in selected

    def test_get_total_package_count(self):
        """Test getting total package count."""
        selection = DependencySelection(
            setup_type_slug="fastapi",
            selected_groups={"core": True, "dev": True},
            all_packages=["pkg1", "pkg2", "pkg3"],
        )
        assert selection.get_total_package_count() == 3

    def test_get_group_count(self):
        """Test getting count of selected groups."""
        selection = DependencySelection(
            setup_type_slug="fastapi",
            selected_groups={"core": True, "dev": True, "optional": False},
            all_packages=["pkg1"],
        )
        assert selection.get_group_count() == 2

    def test_validate_against_setup_type(self, sample_setup_type):
        """Test validation against setup type."""
        selection = DependencySelection(
            setup_type_slug="fastapi",
            selected_groups={"core": True, "dev": True, "optional": False},
            all_packages=["pkg1"],
        )
        errors = selection.validate_against_setup_type(sample_setup_type)
        assert len(errors) == 0

    def test_validate_against_setup_type_invalid_group(self, sample_setup_type):
        """Test validation fails for invalid group."""
        selection = DependencySelection(
            setup_type_slug="fastapi",
            selected_groups={"core": True, "invalid": True},
            all_packages=["pkg1"],
        )
        errors = selection.validate_against_setup_type(sample_setup_type)
        assert len(errors) > 0
        assert "invalid" in errors[0]

    def test_to_install_list(self):
        """Test getting packages in install format."""
        packages = ["fastapi>=0.104.0", "pytest>=7.0"]
        selection = DependencySelection(
            setup_type_slug="fastapi",
            selected_groups={"core": True, "dev": True},
            all_packages=packages,
        )
        install_list = selection.to_install_list()
        assert install_list == packages

    def test_get_readable_summary(self):
        """Test getting human-readable summary."""
        selection = DependencySelection(
            setup_type_slug="fastapi",
            selected_groups={"core": True, "dev": True, "optional": False},
            all_packages=["pkg1", "pkg2", "pkg3"],
        )
        summary = selection.get_readable_summary()
        assert "core" in summary.lower()
        assert "dev" in summary.lower()
        assert "3 packages" in summary


class TestProjectMetadata:
    """Tests for ProjectMetadata model."""

    def test_project_metadata_creation(self):
        """Test creating ProjectMetadata."""
        metadata = ProjectMetadata(
            project_name="my_project",
            project_description="A test project",
            author_name="Jane Doe",
            author_email="jane@example.com",
        )
        assert metadata.project_name == "my_project"

    def test_project_name_validation_valid(self):
        """Test valid project names."""
        valid_names = ["my_project", "test_123", "_private", "a"]
        for name in valid_names:
            if len(name) >= 3:
                metadata = ProjectMetadata(project_name=name)
                assert metadata.project_name == name

    def test_project_name_validation_invalid_hyphen(self):
        """Test that hyphens are converted to underscores."""
        metadata = ProjectMetadata(project_name="my-project")
        assert metadata.project_name == "my_project"

    def test_project_name_validation_lowercase(self):
        """Test that project names are converted to lowercase."""
        metadata = ProjectMetadata(project_name="MyProject")
        assert metadata.project_name == "myproject"

    def test_project_name_too_short(self):
        """Test that names < 3 chars are rejected."""
        with pytest.raises(ValueError, match="3 characters"):
            ProjectMetadata(project_name="ab")

    def test_project_name_python_keyword(self):
        """Test that Python keywords are rejected."""
        with pytest.raises(ValueError, match="keyword"):
            ProjectMetadata(project_name="class")

    def test_project_name_invalid_start(self):
        """Test that names starting with digits are rejected."""
        with pytest.raises(ValueError):
            ProjectMetadata(project_name="123project")

    def test_project_description_optional(self):
        """Test that description is optional."""
        metadata = ProjectMetadata(project_name="my_project")
        assert metadata.project_description is None

    def test_project_description_too_long(self):
        """Test that description > 500 chars is rejected."""
        long_desc = "x" * 501
        with pytest.raises(ValueError, match="500 characters"):
            ProjectMetadata(project_name="my_project", project_description=long_desc)

    def test_project_description_stripped(self):
        """Test that description whitespace is stripped."""
        metadata = ProjectMetadata(project_name="my_project", project_description="  test  ")
        assert metadata.project_description == "test"

    def test_author_name_optional(self):
        """Test that author name is optional."""
        metadata = ProjectMetadata(project_name="my_project")
        assert metadata.author_name is None

    def test_author_email_validation_valid(self):
        """Test valid email addresses."""
        valid_emails = [
            "user@example.com",
            "john.doe@example.co.uk",
            "test+tag@example.org",
        ]
        for email in valid_emails:
            metadata = ProjectMetadata(project_name="my_project", author_email=email)
            assert metadata.author_email == email

    def test_author_email_validation_invalid(self):
        """Test invalid email addresses."""
        invalid_emails = [
            "not-an-email",
            "@example.com",
            "user@",
            "user@.com",
        ]
        for email in invalid_emails:
            with pytest.raises(ValueError, match="not a valid email"):
                ProjectMetadata(project_name="my_project", author_email=email)

    def test_is_valid_package_name_true(self):
        """Test static method with valid name."""
        assert ProjectMetadata.is_valid_package_name("valid_name")

    def test_is_valid_package_name_false(self):
        """Test static method with invalid name."""
        assert not ProjectMetadata.is_valid_package_name("invalid-name")
        assert not ProjectMetadata.is_valid_package_name("class")

    def test_sanitize_for_file_usage(self):
        """Test preparation for file generation."""
        metadata = ProjectMetadata(
            project_name="my_project",
            project_description="A project",
            author_name="Jane Doe",
            author_email="jane@example.com",
        )
        sanitized = metadata.sanitize_for_file_usage()
        assert sanitized["project_name"] == "my_project"
        assert sanitized["project_description"] == "A project"

    def test_get_author_string_full(self):
        """Test author string with name and email."""
        metadata = ProjectMetadata(
            project_name="my_project",
            author_name="Jane Doe",
            author_email="jane@example.com",
        )
        author_str = metadata.get_author_string()
        assert "Jane Doe" in author_str
        assert "jane@example.com" in author_str

    def test_get_author_string_name_only(self):
        """Test author string with name only."""
        metadata = ProjectMetadata(project_name="my_project", author_name="Jane Doe")
        author_str = metadata.get_author_string()
        assert author_str == "Jane Doe"

    def test_get_author_string_empty(self):
        """Test author string when no author provided."""
        metadata = ProjectMetadata(project_name="my_project")
        author_str = metadata.get_author_string()
        assert author_str == ""

    def test_repr(self):
        """Test string representation."""
        metadata = ProjectMetadata(
            project_name="my_project",
            author_name="Jane Doe",
            author_email="jane@example.com",
        )
        repr_str = repr(metadata)
        assert "my_project" in repr_str
        assert "Jane Doe" in repr_str
