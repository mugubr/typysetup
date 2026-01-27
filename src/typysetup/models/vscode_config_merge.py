"""Merging strategies for VSCode configurations with conflict resolution."""

from typing import Any, Dict, List, Set


class DeepMergeStrategy:
    """Strategy for deep merging VSCode configurations.

    Handles recursive merging of nested dictionaries while respecting
    VSCode-specific structures like language-specific settings.
    """

    @staticmethod
    def deep_merge_dicts(existing: Dict[str, Any], new: Dict[str, Any]) -> Dict[str, Any]:
        """Deep merge new config into existing config.

        Args:
            existing: Existing configuration (lower priority)
            new: New configuration (higher priority, overwrites conflicts)

        Returns:
            Merged dictionary with new values taking precedence

        Examples:
            >>> existing = {"python.linting.enabled": False, "editor.formatOnSave": True}
            >>> new = {"python.linting.enabled": True}
            >>> merged = DeepMergeStrategy.deep_merge_dicts(existing, new)
            >>> merged == {"python.linting.enabled": True, "editor.formatOnSave": True}
            True
        """
        result = existing.copy()

        for key, new_value in new.items():
            if key not in result:
                # New key from setup type
                result[key] = new_value
            elif isinstance(existing[key], dict) and isinstance(new_value, dict):
                # Recursively merge nested dicts (e.g., "[python]" language settings)
                result[key] = DeepMergeStrategy.deep_merge_dicts(existing[key], new_value)
            else:
                # Scalar value: new takes precedence
                result[key] = new_value

        return result

    @staticmethod
    def deduplicate_extensions(existing: List[str], new: List[str]) -> List[str]:
        """Deduplicate extensions, preserving order.

        Args:
            existing: Existing extension list (user's current extensions)
            new: New extensions to recommend (from setup type)

        Returns:
            Deduplicated list: existing + new unique extensions

        Examples:
            >>> existing = ["ms-python.python", "charliermarsh.ruff"]
            >>> new = ["ms-python.python", "ms-python.vscode-pylance"]
            >>> result = DeepMergeStrategy.deduplicate_extensions(existing, new)
            >>> result == ["ms-python.python", "charliermarsh.ruff", "ms-python.vscode-pylance"]
            True
        """
        seen: Set[str] = set(existing)
        result = existing.copy()

        for ext_id in new:
            if ext_id not in seen:
                result.append(ext_id)
                seen.add(ext_id)

        return result

    @staticmethod
    def merge_launch_configurations(
        existing: List[Dict[str, Any]], new: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Merge launch configurations with name-based deduplication.

        Args:
            existing: Existing launch configurations (user's custom configs)
            new: New launch configurations (from setup type)

        Returns:
            Merged configurations: existing + new (deduplicated by name)

        Notes:
            - Configurations are deduplicated by the "name" field
            - New configurations with same name as existing override them
            - This allows setup to provide updated debug configs
        """
        existing_names = {cfg.get("name"): i for i, cfg in enumerate(existing)}
        result = existing.copy()

        for new_cfg in new:
            name = new_cfg.get("name")
            if name and name in existing_names:
                # Update existing config with same name
                result[existing_names[name]] = new_cfg
            else:
                # Append new config
                result.append(new_cfg)

        return result

    @staticmethod
    def detect_overrides(
        existing: Dict[str, Any], new: Dict[str, Any]
    ) -> Dict[str, tuple[Any, Any]]:
        """Detect and report configuration overrides.

        Args:
            existing: Existing configuration
            new: New configuration to be merged

        Returns:
            Dictionary mapping override keys to (existing_value, new_value) tuples

        Used for displaying warnings or confirmations to the user.

        Examples:
            >>> existing = {"python.linting.enabled": False}
            >>> new = {"python.linting.enabled": True}
            >>> overrides = DeepMergeStrategy.detect_overrides(existing, new)
            >>> overrides == {"python.linting.enabled": (False, True)}
            True
        """
        overrides: Dict[str, tuple[Any, Any]] = {}

        def check_overrides(
            existing_dict: Dict[str, Any], new_dict: Dict[str, Any], prefix: str = ""
        ) -> None:
            for key, new_value in new_dict.items():
                full_key = f"{prefix}{key}" if not prefix else f"{prefix}.{key}"

                if key not in existing_dict:
                    # New key, not an override
                    continue

                existing_value = existing_dict[key]

                if isinstance(existing_value, dict) and isinstance(new_value, dict):
                    # Recurse into nested dicts
                    check_overrides(existing_value, new_value, full_key)
                elif existing_value != new_value:
                    # Value is being overridden
                    overrides[full_key] = (existing_value, new_value)

        check_overrides(existing, new)
        return overrides
