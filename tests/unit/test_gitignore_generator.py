"""Unit tests for GitignoreGenerator."""

from pathlib import Path

import pytest

from typysetup.core.gitignore_generator import GitignoreGenerator


@pytest.fixture
def temp_project_dir(tmp_path):
    """Create a temporary project directory."""
    return tmp_path


class TestGitignoreGeneratorInit:
    """Tests for GitignoreGenerator initialization."""

    def test_gitignore_template_exists(self):
        """Test that GitignoreGenerator has a template."""
        assert hasattr(GitignoreGenerator, "GITIGNORE_TEMPLATE")
        assert len(GitignoreGenerator.GITIGNORE_TEMPLATE) > 0
        assert "venv/" in GitignoreGenerator.GITIGNORE_TEMPLATE
        assert "__pycache__/" in GitignoreGenerator.GITIGNORE_TEMPLATE
        assert "*.backup.*" in GitignoreGenerator.GITIGNORE_TEMPLATE


class TestGitignoreGeneration:
    """Tests for .gitignore generation."""

    def test_generate_gitignore_creates_file(self, temp_project_dir):
        """Test that generate_gitignore creates a .gitignore file."""
        gitignore_path = GitignoreGenerator.generate_gitignore(temp_project_dir)

        assert gitignore_path.exists()
        assert gitignore_path.name == ".gitignore"
        assert gitignore_path.parent == temp_project_dir

    def test_generate_gitignore_contains_expected_patterns(self, temp_project_dir):
        """Test that generated .gitignore contains expected patterns."""
        gitignore_path = GitignoreGenerator.generate_gitignore(temp_project_dir)

        content = gitignore_path.read_text()
        expected_patterns = [
            "venv/",
            ".venv/",
            "__pycache__/",
            "dist/",
            "build/",
            "*.egg-info/",
            ".pytest_cache/",
            ".vscode/",
            ".idea/",
            ".DS_Store",
            ".typysetup/",
            "*.backup.*",
        ]

        for pattern in expected_patterns:
            assert pattern in content, f"Pattern '{pattern}' not found in .gitignore"

    def test_generate_gitignore_does_not_overwrite(self, temp_project_dir):
        """Test that generate_gitignore doesn't overwrite existing .gitignore."""
        # Create existing .gitignore with custom content
        gitignore_path = temp_project_dir / ".gitignore"
        custom_content = "# Custom gitignore\ncustom_pattern/"
        gitignore_path.write_text(custom_content)

        # Generate .gitignore again
        returned_path = GitignoreGenerator.generate_gitignore(temp_project_dir)

        # Content should remain unchanged
        assert returned_path.read_text() == custom_content

    def test_generate_gitignore_returns_path(self, temp_project_dir):
        """Test that generate_gitignore returns the correct path."""
        expected_path = temp_project_dir / ".gitignore"
        returned_path = GitignoreGenerator.generate_gitignore(temp_project_dir)

        assert returned_path == expected_path

    def test_generate_gitignore_with_invalid_path_raises_error(self):
        """Test that generate_gitignore raises error with invalid path."""
        invalid_path = Path("/nonexistent/path/that/does/not/exist")

        with pytest.raises(OSError):
            GitignoreGenerator.generate_gitignore(invalid_path)
