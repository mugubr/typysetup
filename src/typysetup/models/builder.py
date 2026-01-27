"""SetupTypeBuilder for fluent construction of SetupType instances."""

from typing import Any, Dict, List, Optional

from typysetup.models.setup_type import SetupType


class SetupTypeBuilder:
    """Fluent builder for constructing SetupType instances programmatically.

    Provides a chainable API for building setup types without requiring YAML files.
    Useful for testing, dynamic template creation, and programmatic configuration.

    Example:
        setup = (SetupTypeBuilder()
            .with_name("FastAPI")
            .with_slug("fastapi")
            .with_python_version("3.10+")
            .with_supported_managers(["uv", "pip", "poetry"])
            .add_dependency("core", "fastapi>=0.104.0")
            .add_dependency("dev", "pytest>=7.0")
            .add_vscode_extension("ms-python.python")
            .add_tag("web")
            .build())
    """

    def __init__(self):
        """Initialize builder with empty configuration."""
        self._name: Optional[str] = None
        self._slug: Optional[str] = None
        self._description: Optional[str] = None
        self._python_version: Optional[str] = None
        self._supported_managers: List[str] = []
        self._dependencies: Dict[str, List[str]] = {}
        self._vscode_settings: Dict[str, Any] = {}
        self._vscode_extensions: List[str] = []
        self._vscode_launch_config: Dict[str, Any] = {}
        self._tags: List[str] = []
        self._docs_url: Optional[str] = None

    def with_name(self, name: str) -> "SetupTypeBuilder":
        """Set the display name.

        Args:
            name: Human-readable setup type name (e.g., "FastAPI")

        Returns:
            Self for chaining
        """
        self._name = name
        return self

    def with_slug(self, slug: str) -> "SetupTypeBuilder":
        """Set the URL-friendly identifier.

        Args:
            slug: Lowercase alphanumeric with hyphens (e.g., "fastapi")

        Returns:
            Self for chaining
        """
        self._slug = slug
        return self

    def with_description(self, description: str) -> "SetupTypeBuilder":
        """Set the description.

        Args:
            description: User-friendly description

        Returns:
            Self for chaining
        """
        self._description = description
        return self

    def with_python_version(self, python_version: str) -> "SetupTypeBuilder":
        """Set the required Python version.

        Args:
            python_version: Version specification (e.g., "3.10+", "3.8-3.11")

        Returns:
            Self for chaining
        """
        self._python_version = python_version
        return self

    def with_supported_managers(self, managers: List[str]) -> "SetupTypeBuilder":
        """Set supported package managers.

        Args:
            managers: List of manager names (uv, pip, poetry)

        Returns:
            Self for chaining
        """
        self._supported_managers = managers
        return self

    def add_dependency(self, group: str, package: str) -> "SetupTypeBuilder":
        """Add a dependency to a group.

        Args:
            group: Group name (core, dev, optional, etc.)
            package: Package specification (e.g., "fastapi>=0.104.0")

        Returns:
            Self for chaining
        """
        if group not in self._dependencies:
            self._dependencies[group] = []
        self._dependencies[group].append(package)
        return self

    def add_dependencies(self, group: str, packages: List[str]) -> "SetupTypeBuilder":
        """Add multiple dependencies to a group.

        Args:
            group: Group name
            packages: List of package specifications

        Returns:
            Self for chaining
        """
        if group not in self._dependencies:
            self._dependencies[group] = []
        self._dependencies[group].extend(packages)
        return self

    def add_vscode_setting(self, key: str, value: Any) -> "SetupTypeBuilder":
        """Add a VSCode workspace setting.

        Args:
            key: Setting key (e.g., "python.formatting.provider")
            value: Setting value

        Returns:
            Self for chaining
        """
        self._vscode_settings[key] = value
        return self

    def add_vscode_settings(self, settings: Dict[str, Any]) -> "SetupTypeBuilder":
        """Add multiple VSCode settings.

        Args:
            settings: Dictionary of settings

        Returns:
            Self for chaining
        """
        self._vscode_settings.update(settings)
        return self

    def add_vscode_extension(self, extension_id: str) -> "SetupTypeBuilder":
        """Add a VSCode extension recommendation.

        Args:
            extension_id: Extension ID (e.g., "ms-python.python")

        Returns:
            Self for chaining
        """
        if extension_id not in self._vscode_extensions:
            self._vscode_extensions.append(extension_id)
        return self

    def add_vscode_extensions(self, extension_ids: List[str]) -> "SetupTypeBuilder":
        """Add multiple VSCode extension recommendations.

        Args:
            extension_ids: List of extension IDs

        Returns:
            Self for chaining
        """
        for ext_id in extension_ids:
            self.add_vscode_extension(ext_id)
        return self

    def with_vscode_settings(self, settings: Dict[str, Any]) -> "SetupTypeBuilder":
        """Set VSCode settings (replaces existing).

        Args:
            settings: Dictionary of VSCode settings

        Returns:
            Self for chaining
        """
        self._vscode_settings = settings.copy()
        return self

    def with_vscode_launch_config(self, launch_config: Dict[str, Any]) -> "SetupTypeBuilder":
        """Set VSCode launch configuration.

        Args:
            launch_config: Launch configuration dictionary

        Returns:
            Self for chaining
        """
        self._vscode_launch_config = launch_config
        return self

    def set_vscode_launch_config(self, config: Dict[str, Any]) -> "SetupTypeBuilder":
        """Set VSCode debug launch configuration.

        Args:
            config: Launch configuration dictionary

        Returns:
            Self for chaining
        """
        self._vscode_launch_config = config
        return self

    def add_tag(self, tag: str) -> "SetupTypeBuilder":
        """Add a tag for filtering/searching.

        Args:
            tag: Tag string (e.g., "web", "async", "api")

        Returns:
            Self for chaining
        """
        if tag not in self._tags:
            self._tags.append(tag)
        return self

    def add_tags(self, tags: List[str]) -> "SetupTypeBuilder":
        """Add multiple tags.

        Args:
            tags: List of tags

        Returns:
            Self for chaining
        """
        for tag in tags:
            self.add_tag(tag)
        return self

    def with_docs_url(self, docs_url: str) -> "SetupTypeBuilder":
        """Set documentation URL.

        Args:
            docs_url: URL to documentation

        Returns:
            Self for chaining
        """
        self._docs_url = docs_url
        return self

    def build(self) -> SetupType:
        """Build and validate the SetupType instance.

        Returns:
            Validated SetupType instance

        Raises:
            ValueError: If required fields are missing or invalid
        """
        # Validate required fields
        if not self._name:
            raise ValueError("Name is required. Use with_name()")
        if not self._slug:
            raise ValueError("Slug is required. Use with_slug()")
        if not self._description:
            raise ValueError("Description is required. Use with_description()")
        if not self._python_version:
            raise ValueError("Python version is required. Use with_python_version()")
        if not self._supported_managers:
            raise ValueError("Supported managers are required. Use with_supported_managers()")
        if not self._dependencies or "core" not in self._dependencies:
            raise ValueError("Core dependencies are required. Use add_dependency('core', ...)")

        # Build SetupType with collected data
        return SetupType(
            name=self._name,
            slug=self._slug,
            description=self._description,
            python_version=self._python_version,
            supported_managers=self._supported_managers,
            dependencies=self._dependencies,
            vscode_settings=self._vscode_settings if self._vscode_settings else None,
            vscode_extensions=self._vscode_extensions if self._vscode_extensions else None,
            vscode_launch_config=self._vscode_launch_config if self._vscode_launch_config else None,
            tags=self._tags if self._tags else None,
            docs_url=self._docs_url,
        )

    def reset(self) -> "SetupTypeBuilder":
        """Reset builder to initial state.

        Returns:
            Self for chaining
        """
        self.__init__()  # Reset all fields
        return self
