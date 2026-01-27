"""VSCode configuration models for workspace settings, extensions, and launch configs."""

from typing import TYPE_CHECKING, Any, Dict, List

from pydantic import BaseModel, ConfigDict, Field, field_validator

if TYPE_CHECKING:
    from typysetup.models.setup_type import SetupType


class VSCodeSettings(BaseModel):
    """VSCode settings dictionary with validation.

    Represents the complete settings object for .vscode/settings.json
    Allows arbitrary keys/values as VSCode supports custom extensions.
    """

    model_config = ConfigDict(extra="allow")

    @field_validator("*", mode="before")
    @classmethod
    def validate_settings_value(cls, v: Any) -> Any:
        """Validate that settings values are JSON-serializable."""
        if v is None or isinstance(v, (bool, int, float, str, list, dict)):
            return v
        raise ValueError(f"Setting value must be JSON-serializable, got {type(v)}")


class VSCodeExtension(BaseModel):
    """Represents a single VSCode extension recommendation.

    Example: ms-python.python, charliermarsh.ruff
    """

    model_config = ConfigDict(extra="forbid")

    extension_id: str = Field(
        ...,
        pattern=r"^[a-z0-9][-a-z0-9]*\.[a-z0-9][-a-z0-9]*$",
        description="Extension ID in format publisher.name",
    )
    enabled: bool = Field(default=True, description="Whether extension is recommended")


class VSCodeLaunchConfiguration(BaseModel):
    """Represents a single debug launch configuration.

    Corresponds to a single item in .vscode/launch.json configurations array.
    """

    model_config = ConfigDict(extra="allow")

    name: str = Field(..., description="Human-readable name for launch config")
    type: str = Field(..., description="Debugger type (e.g., 'python', 'node')")
    request: str = Field(default="launch", description="'launch' or 'attach'")
    # Additional fields allowed for custom debugger options


class VSCodeConfiguration(BaseModel):
    """Complete VSCode workspace configuration.

    Aggregates settings, extensions, and launch configurations.
    """

    model_config = ConfigDict(extra="forbid")

    settings: Dict[str, Any] = Field(
        default_factory=dict, description="Settings for .vscode/settings.json"
    )
    extensions: List[str] = Field(
        default_factory=list, description="Extension IDs for .vscode/extensions.json"
    )
    launch_configurations: List[Dict[str, Any]] = Field(
        default_factory=list, description="Launch configs for .vscode/launch.json"
    )

    @field_validator("extensions")
    @classmethod
    def validate_extensions(cls, v: List[str]) -> List[str]:
        """Validate that all extensions have valid format."""
        for ext_id in v:
            if not isinstance(ext_id, str) or "." not in ext_id:
                raise ValueError(f"Invalid extension ID format: {ext_id}")
        return v

    def get_settings_dict(self) -> Dict[str, Any]:
        """Get settings formatted for settings.json."""
        return self.settings.copy()

    def get_extensions_dict(self) -> Dict[str, List[str]]:
        """Get extensions formatted for extensions.json."""
        return {"recommendations": self.extensions}

    def get_launch_dict(self) -> Dict[str, Any]:
        """Get launch config formatted for launch.json."""
        return {
            "version": "0.2.0",
            "configurations": self.launch_configurations,
        }

    def merge_with(self, other: "VSCodeConfiguration") -> "VSCodeConfiguration":
        """Merge this configuration with another.

        Args:
            other: Configuration to merge in (takes precedence)

        Returns:
            New merged VSCodeConfiguration
        """
        from typysetup.models.vscode_config_merge import DeepMergeStrategy

        merged_settings = DeepMergeStrategy.deep_merge_dicts(self.settings, other.settings)
        merged_extensions = DeepMergeStrategy.deduplicate_extensions(
            self.extensions, other.extensions
        )
        merged_launch = DeepMergeStrategy.merge_launch_configurations(
            self.launch_configurations, other.launch_configurations
        )

        return VSCodeConfiguration(
            settings=merged_settings,
            extensions=merged_extensions,
            launch_configurations=merged_launch,
        )

    @classmethod
    def from_setup_type(cls, setup_type: "SetupType") -> "VSCodeConfiguration":
        """Create VSCode configuration from a SetupType.

        Args:
            setup_type: SetupType to extract config from

        Returns:
            VSCodeConfiguration with values from setup type
        """
        # Import here to avoid circular dependency
        return cls(
            settings=setup_type.vscode_settings or {},
            extensions=setup_type.vscode_extensions or [],
            launch_configurations=(
                [setup_type.vscode_launch_config] if setup_type.vscode_launch_config else []
            ),
        )
