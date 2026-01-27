"""DependencySelection model for capturing user's dependency group selections."""

from typing import Dict, List

from pydantic import BaseModel, ConfigDict, Field, field_validator

from typysetup.models.setup_type import SetupType


class DependencySelection(BaseModel):
    """Captures user's selection of which dependency groups to install.

    The "core" group is always selected and cannot be deselected.
    """

    model_config = ConfigDict(extra="forbid")

    setup_type_slug: str = Field(..., description="The setup type this selection applies to")
    selected_groups: Dict[str, bool] = Field(
        ..., description="Maps group_name -> is_selected (e.g., {'core': true, 'dev': true})"
    )
    all_packages: List[str] = Field(
        ..., description="Flattened list of all packages from selected groups"
    )
    group_descriptions: Dict[str, str] = Field(
        default_factory=dict, description="Descriptions of each group for display"
    )

    @field_validator("selected_groups", mode="before")
    @classmethod
    def validate_core_selected(cls, v: Dict[str, bool]) -> Dict[str, bool]:
        """Ensure core group is always selected."""
        if "core" not in v:
            raise ValueError("Core dependencies must be selected")
        if not v.get("core"):
            raise ValueError("Core dependencies cannot be deselected")
        return v

    def get_selected_groups(self) -> List[str]:
        """Get list of selected group names.

        Returns:
            List of group names that were selected
        """
        return [name for name, selected in self.selected_groups.items() if selected]

    def get_packages_for_groups(self, group_names: List[str]) -> List[str]:
        """Get packages for specific groups from the all_packages list.

        This is a simplified method - for actual filtering, use the
        SetupType model's filter_dependencies_by_groups().

        Args:
            group_names: List of group names to get packages for

        Returns:
            List of packages (subset of all_packages)
        """
        # Note: This returns the all_packages since we don't store per-group
        # mapping. The full filtering happens in SetupType model.
        if self.get_selected_groups() == group_names:
            return self.all_packages
        return self.all_packages

    def validate_against_setup_type(self, setup_type: SetupType) -> List[str]:
        """Validate that all selected groups exist in the setup type.

        Args:
            setup_type: The SetupType to validate against

        Returns:
            List of validation errors (empty if valid)
        """
        errors = []
        available_groups = set(setup_type.get_dependency_groups())
        selected = self.get_selected_groups()

        for group_name in selected:
            if group_name not in available_groups:
                errors.append(
                    f"Group '{group_name}' does not exist in setup type '{setup_type.slug}'"
                )

        if "core" not in selected:
            errors.append("Core dependencies must be selected")

        return errors

    def to_install_list(self) -> List[str]:
        """Get packages formatted for dependency installer (Phase 6).

        Returns:
            List of packages ready for pip/uv/poetry install
        """
        return self.all_packages.copy()

    def get_total_package_count(self) -> int:
        """Get total count of packages to install.

        Returns:
            Number of packages
        """
        return len(self.all_packages)

    def get_group_count(self) -> int:
        """Get count of selected groups.

        Returns:
            Number of groups selected
        """
        return len(self.get_selected_groups())

    def get_readable_summary(self) -> str:
        """Get human-readable summary of selection.

        Returns:
            String like "Core (4), Dev (6), Optional (3) - 13 packages total"
        """
        selected = self.get_selected_groups()
        return f"{', '.join([g.title() for g in selected])} - {self.get_total_package_count()} packages total"

    def __repr__(self) -> str:
        """String representation."""
        return f"DependencySelection(setup_type={self.setup_type_slug}, groups={self.get_selected_groups()}, packages={self.get_total_package_count()})"
