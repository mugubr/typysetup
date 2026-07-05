"""Unit tests for PromptManager - interactive setup wizard prompts."""

from unittest.mock import MagicMock

import pytest
import questionary

from typysetup.models import DependencySelection, ProjectMetadata, SetupType
from typysetup.utils.prompts import PromptManager

PROMPTS_QUESTIONARY = "typysetup.utils.prompts.questionary"


@pytest.fixture
def prompt_manager() -> PromptManager:
    """Provide a PromptManager instance."""
    return PromptManager()


def mock_prompt(
    monkeypatch: pytest.MonkeyPatch, prompt_name: str, ask_result=None, ask_side_effect=None
) -> MagicMock:
    """Patch a questionary prompt factory so .ask() returns canned answers."""
    mock_factory = MagicMock()
    if ask_side_effect is not None:
        mock_factory.return_value.ask.side_effect = ask_side_effect
    else:
        mock_factory.return_value.ask.return_value = ask_result
    monkeypatch.setattr(f"{PROMPTS_QUESTIONARY}.{prompt_name}", mock_factory)
    return mock_factory


class TestPromptDependencyGroups:
    """Tests for prompt_dependency_groups."""

    def test_returns_selection_with_chosen_groups(
        self,
        prompt_manager: PromptManager,
        sample_setup_type: SetupType,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Test that selecting core and dev returns a full DependencySelection."""
        # Arrange
        mock_prompt(monkeypatch, "checkbox", ask_result=["core", "dev"])

        # Act
        selection = prompt_manager.prompt_dependency_groups(sample_setup_type)

        # Assert
        assert isinstance(selection, DependencySelection)
        assert selection.setup_type_slug == "fastapi"
        assert selection.selected_groups == {"core": True, "dev": True}
        assert "fastapi>=0.104.0" in selection.all_packages
        assert "pytest>=7.0" in selection.all_packages

    def test_core_group_is_forced_when_not_selected(
        self,
        prompt_manager: PromptManager,
        sample_setup_type: SetupType,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Test that the core group is always included even if omitted."""
        # Arrange
        mock_prompt(monkeypatch, "checkbox", ask_result=["dev"])

        # Act
        selection = prompt_manager.prompt_dependency_groups(sample_setup_type)

        # Assert
        assert selection is not None
        assert selection.selected_groups["core"] is True
        assert "fastapi>=0.104.0" in selection.all_packages

    def test_core_choice_is_disabled_in_checkbox(
        self,
        prompt_manager: PromptManager,
        sample_setup_type: SetupType,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Test that the checkbox marks the core group as non-deselectable."""
        # Arrange
        mock_checkbox = mock_prompt(monkeypatch, "checkbox", ask_result=["core"])

        # Act
        prompt_manager.prompt_dependency_groups(sample_setup_type)

        # Assert
        choices = mock_checkbox.call_args.kwargs["choices"]
        core_choice = next(c for c in choices if c["value"] == "core")
        dev_choice = next(c for c in choices if c["value"] == "dev")
        assert core_choice["disabled"] is True
        assert dev_choice["disabled"] is False
        assert "[required]" in core_choice["name"]

    def test_returns_none_when_cancelled(
        self,
        prompt_manager: PromptManager,
        sample_setup_type: SetupType,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Test that cancelling the checkbox returns None."""
        # Arrange
        mock_prompt(monkeypatch, "checkbox", ask_result=None)

        # Act
        selection = prompt_manager.prompt_dependency_groups(sample_setup_type)

        # Assert
        assert selection is None


class TestPromptVscodeExtensions:
    """Tests for prompt_vscode_extensions."""

    def test_returns_selected_extensions(
        self,
        prompt_manager: PromptManager,
        sample_setup_type: SetupType,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Test that selected extension IDs are returned."""
        # Arrange
        mock_prompt(monkeypatch, "checkbox", ask_result=["ms-python.python"])

        # Act
        selected = prompt_manager.prompt_vscode_extensions(sample_setup_type)

        # Assert
        assert selected == ["ms-python.python"]

    def test_returns_empty_list_without_prompting_when_no_extensions(
        self,
        prompt_manager: PromptManager,
        sample_setup_type_data: dict,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Test that setup types without extensions skip the checkbox entirely."""
        # Arrange
        setup_type = SetupType(**{**sample_setup_type_data, "vscode_extensions": []})
        mock_checkbox = mock_prompt(monkeypatch, "checkbox", ask_result=["should-not-happen"])

        # Act
        selected = prompt_manager.prompt_vscode_extensions(setup_type)

        # Assert
        assert selected == []
        mock_checkbox.assert_not_called()

    def test_returns_none_when_cancelled(
        self,
        prompt_manager: PromptManager,
        sample_setup_type: SetupType,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Test that cancelling the extension checkbox returns None."""
        # Arrange
        mock_prompt(monkeypatch, "checkbox", ask_result=None)

        # Act
        selected = prompt_manager.prompt_vscode_extensions(sample_setup_type)

        # Assert
        assert selected is None


class TestPromptProjectName:
    """Tests for prompt_project_name."""

    def test_returns_valid_name(
        self, prompt_manager: PromptManager, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test that a valid project name is returned on first try."""
        # Arrange
        mock_prompt(monkeypatch, "text", ask_result="cool_project")

        # Act
        name = prompt_manager.prompt_project_name()

        # Assert
        assert name == "cool_project"

    def test_returns_none_when_cancelled(
        self, prompt_manager: PromptManager, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test that cancelling the name prompt returns None."""
        # Arrange
        mock_prompt(monkeypatch, "text", ask_result=None)

        # Act
        name = prompt_manager.prompt_project_name()

        # Assert
        assert name is None

    def test_retries_after_validation_error_then_succeeds(
        self, prompt_manager: PromptManager, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test that a validation failure triggers a retry before success."""
        # Arrange
        mock_prompt(monkeypatch, "text", ask_side_effect=["bad name", "good_name"])
        monkeypatch.setattr(
            "typysetup.utils.prompts.ProjectMetadata.is_valid_package_name",
            MagicMock(side_effect=[False, True]),
        )

        # Act
        name = prompt_manager.prompt_project_name()

        # Assert
        assert name == "good_name"

    def test_returns_none_after_max_retries(
        self, prompt_manager: PromptManager, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test that exceeding max retries cancels the setup with None."""
        # Arrange
        mock_prompt(monkeypatch, "text", ask_result="always_bad")
        monkeypatch.setattr(
            "typysetup.utils.prompts.ProjectMetadata.is_valid_package_name",
            MagicMock(return_value=False),
        )

        # Act
        name = prompt_manager.prompt_project_name()

        # Assert
        assert name is None


class TestPromptOptionalFields:
    """Tests for description and author name prompts."""

    def test_description_returned_when_provided(
        self, prompt_manager: PromptManager, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test that a non-empty description is returned as-is."""
        # Arrange
        mock_prompt(monkeypatch, "text", ask_result="A great tool")

        # Act / Assert
        assert prompt_manager.prompt_project_description() == "A great tool"

    def test_description_skipped_returns_none(
        self, prompt_manager: PromptManager, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test that pressing Enter (empty string) skips the description."""
        # Arrange
        mock_prompt(monkeypatch, "text", ask_result="   ")

        # Act / Assert
        assert prompt_manager.prompt_project_description() is None

    def test_description_cancelled_returns_none(
        self, prompt_manager: PromptManager, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test that cancelling the description prompt returns None."""
        # Arrange
        mock_prompt(monkeypatch, "text", ask_result=None)

        # Act / Assert
        assert prompt_manager.prompt_project_description() is None

    def test_author_name_returned_when_provided(
        self, prompt_manager: PromptManager, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test that a non-empty author name is returned."""
        # Arrange
        mock_prompt(monkeypatch, "text", ask_result="Jane Doe")

        # Act / Assert
        assert prompt_manager.prompt_author_name() == "Jane Doe"

    def test_author_name_skipped_returns_none(
        self, prompt_manager: PromptManager, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test that an empty author name is treated as skipped."""
        # Arrange
        mock_prompt(monkeypatch, "text", ask_result="")

        # Act / Assert
        assert prompt_manager.prompt_author_name() is None


class TestPromptAuthorEmail:
    """Tests for prompt_author_email."""

    def test_returns_valid_email(
        self, prompt_manager: PromptManager, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test that a valid email is returned on first try."""
        # Arrange
        mock_prompt(monkeypatch, "text", ask_result="jane@example.com")

        # Act / Assert
        assert prompt_manager.prompt_author_email() == "jane@example.com"

    def test_empty_email_is_skipped(
        self, prompt_manager: PromptManager, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test that an empty email returns None (skip)."""
        # Arrange
        mock_prompt(monkeypatch, "text", ask_result="  ")

        # Act / Assert
        assert prompt_manager.prompt_author_email() is None

    def test_cancelled_email_returns_none(
        self, prompt_manager: PromptManager, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test that cancelling the email prompt returns None."""
        # Arrange
        mock_prompt(monkeypatch, "text", ask_result=None)

        # Act / Assert
        assert prompt_manager.prompt_author_email() is None

    def test_invalid_email_retries_then_succeeds(
        self, prompt_manager: PromptManager, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test that an invalid email triggers a retry before accepting a valid one."""
        # Arrange
        mock_prompt(monkeypatch, "text", ask_side_effect=["not-an-email", "jane@example.com"])

        # Act / Assert
        assert prompt_manager.prompt_author_email() == "jane@example.com"

    def test_invalid_email_exhausts_retries_and_skips(
        self, prompt_manager: PromptManager, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test that repeated invalid emails end with None after max retries."""
        # Arrange
        mock_text = mock_prompt(monkeypatch, "text", ask_result="still-not-an-email")

        # Act
        email = prompt_manager.prompt_author_email()

        # Assert
        assert email is None
        assert mock_text.return_value.ask.call_count == prompt_manager.max_retries


class TestPromptCollectAllMetadata:
    """Tests for prompt_collect_all_metadata."""

    def test_collects_full_metadata(
        self, prompt_manager: PromptManager, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test that all metadata fields are collected in sequence."""
        # Arrange
        mock_prompt(
            monkeypatch,
            "text",
            ask_side_effect=["cool_project", "A great tool", "Jane Doe", "jane@example.com"],
        )

        # Act
        metadata = prompt_manager.prompt_collect_all_metadata()

        # Assert
        assert isinstance(metadata, ProjectMetadata)
        assert metadata.project_name == "cool_project"
        assert metadata.project_description == "A great tool"
        assert metadata.author_name == "Jane Doe"
        assert metadata.author_email == "jane@example.com"

    def test_returns_none_when_name_cancelled(
        self, prompt_manager: PromptManager, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test that cancelling the required name aborts collection."""
        # Arrange
        mock_prompt(monkeypatch, "text", ask_result=None)

        # Act / Assert
        assert prompt_manager.prompt_collect_all_metadata() is None

    def test_email_prompt_skipped_when_no_author(
        self, prompt_manager: PromptManager, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test that the email prompt is not shown when author is skipped."""
        # Arrange
        mock_text = mock_prompt(monkeypatch, "text", ask_side_effect=["cool_project", "", ""])

        # Act
        metadata = prompt_manager.prompt_collect_all_metadata()

        # Assert
        assert metadata is not None
        assert metadata.author_name is None
        assert metadata.author_email is None
        # Only name, description, and author prompts ran - no email prompt
        assert mock_text.return_value.ask.call_count == 3


class TestValidators:
    """Tests for static validation helpers."""

    def test_validate_package_name_accepts_valid_name(self) -> None:
        """Test that a valid package name passes validation."""
        assert PromptManager._validate_package_name("valid_name") is True

    def test_validate_package_name_rejects_short_name(self) -> None:
        """Test that names under 3 characters raise a ValidationError."""
        with pytest.raises(questionary.ValidationError, match="at least 3 characters"):
            PromptManager._validate_package_name("ab")

    def test_validate_package_name_rejects_hyphenated_name(self) -> None:
        """Test that hyphenated names raise a ValidationError."""
        with pytest.raises(questionary.ValidationError, match="no hyphens"):
            PromptManager._validate_package_name("bad-name")

    def test_validate_description_accepts_normal_text(self) -> None:
        """Test that a short description passes validation."""
        assert PromptManager._validate_description("Short and sweet") is True

    def test_validate_description_rejects_overlong_text(self) -> None:
        """Test that descriptions over 500 characters raise a ValidationError."""
        with pytest.raises(questionary.ValidationError, match="500 characters or less"):
            PromptManager._validate_description("x" * 501)

    def test_validate_email_optional_accepts_empty(self) -> None:
        """Test that an empty email is allowed (skip)."""
        assert PromptManager._validate_email_optional("") is True

    def test_validate_email_optional_accepts_valid_email(self) -> None:
        """Test that a well-formed email passes validation."""
        assert PromptManager._validate_email_optional("user@example.com") is True

    def test_validate_email_optional_rejects_malformed_email(self) -> None:
        """Test that a malformed email raises a ValidationError."""
        with pytest.raises(questionary.ValidationError, match="Invalid email format"):
            PromptManager._validate_email_optional("nope@nowhere")
