"""
Configuration Manager
====================

Manages OCD configuration with hierarchical loading,
validation, and persistence.
"""

import json
import toml
from pathlib import Path
from typing import Any, Dict, Optional
import structlog

from ocd.core.exceptions import OCDConfigError
from ocd.config.settings import OCDSettings

logger = structlog.get_logger(__name__)


class ConfigManager:
    """
    Configuration manager with hierarchical loading.

    Configuration hierarchy (highest to lowest priority):
    1. Command line arguments
    2. Environment variables
    3. User config file (~/.ocd/config.toml)
    4. Project config file (./ocd.toml)
    5. Default settings
    """

    def __init__(self, config_file: Optional[Path] = None):
        """
        Initialize configuration manager.

        Args:
            config_file: Optional config file path
        """
        self.config_file = config_file
        self.settings: Optional[OCDSettings] = None
        self._loaded = False

    def load_config(self, **overrides) -> OCDSettings:
        """
        Load configuration with hierarchy.

        Args:
            **overrides: Configuration overrides

        Returns:
            Loaded settings

        Raises:
            OCDConfigError: If configuration loading fails
        """
        try:
            logger.info("Loading OCD configuration")

            # Start with base config
            config_data = {}

            # 1. Load project config if exists
            project_config = Path.cwd() / "ocd.toml"
            if project_config.exists():
                logger.info("Loading project config", file=project_config)
                config_data.update(self._load_toml_file(project_config))

            # 2. Load user config if exists
            user_config = Path.home() / ".ocd" / "config.toml"
            if user_config.exists():
                logger.info("Loading user config", file=user_config)
                config_data.update(self._load_toml_file(user_config))

            # 3. Load specified config file if provided
            if self.config_file and self.config_file.exists():
                logger.info("Loading specified config", file=self.config_file)
                if self.config_file.suffix.lower() == ".json":
                    config_data.update(self._load_json_file(self.config_file))
                else:
                    config_data.update(self._load_toml_file(self.config_file))

            # 4. Apply overrides
            config_data.update(overrides)

            # 5. Create settings with environment variable support
            self.settings = OCDSettings(**config_data)

            # Create necessary directories
            self.settings.create_directories()

            self._loaded = True
            logger.info("Configuration loaded successfully")

            return self.settings

        except Exception as e:
            raise OCDConfigError(f"Failed to load configuration: {e}", cause=e)

    def save_config(self, config_file: Optional[Path] = None) -> None:
        """
        Save current configuration to file.

        Args:
            config_file: Optional config file path

        Raises:
            OCDConfigError: If saving fails
        """
        if not self.settings:
            raise OCDConfigError("No configuration loaded")

        target_file = (
            config_file or self.config_file or (Path.home() / ".ocd" / "config.toml")
        )

        try:
            logger.info("Saving configuration", file=target_file)

            # Ensure directory exists
            target_file.parent.mkdir(parents=True, exist_ok=True)

            # Convert settings to dict
            config_data = self.settings.dict()

            # Remove computed/derived fields
            config_data.pop("config_dir", None)
            config_data.pop("templates_dir", None)
            config_data.pop("cache_dir", None)
            config_data.pop("logs_dir", None)

            # Save based on file extension
            if target_file.suffix.lower() == ".json":
                self._save_json_file(target_file, config_data)
            else:
                self._save_toml_file(target_file, config_data)

            logger.info("Configuration saved successfully", file=target_file)

        except Exception as e:
            raise OCDConfigError(
                f"Failed to save configuration: {e}",
                config_path=str(target_file),
                cause=e,
            )

    def get_settings(self) -> OCDSettings:
        """
        Get current settings.

        Returns:
            Current settings

        Raises:
            OCDConfigError: If configuration not loaded
        """
        if not self._loaded or not self.settings:
            self.load_config()

        return self.settings

    def update_setting(self, key: str, value: Any) -> None:
        """
        Update a configuration setting.

        Args:
            key: Setting key (dot notation supported)
            value: New value

        Raises:
            OCDConfigError: If update fails
        """
        if not self.settings:
            raise OCDConfigError("No configuration loaded")

        try:
            # Handle nested keys with dot notation
            keys = key.split(".")
            current = self.settings

            # Navigate to parent
            for k in keys[:-1]:
                current = getattr(current, k)

            # Set final value
            setattr(current, keys[-1], value)

            logger.info("Setting updated", key=key, value=value)

        except Exception as e:
            raise OCDConfigError(
                f"Failed to update setting '{key}': {e}", config_key=key, cause=e
            )

    def get_setting(self, key: str, default: Any = None) -> Any:
        """
        Get a configuration setting.

        Args:
            key: Setting key (dot notation supported)
            default: Default value if not found

        Returns:
            Setting value or default
        """
        if not self.settings:
            self.load_config()

        try:
            # Handle nested keys with dot notation
            keys = key.split(".")
            current = self.settings

            for k in keys:
                current = getattr(current, k)

            return current

        except AttributeError:
            return default

    def _load_toml_file(self, file_path: Path) -> Dict[str, Any]:
        """Load configuration from TOML file."""
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                return toml.load(f)
        except Exception as e:
            raise OCDConfigError(
                f"Failed to load TOML file: {e}", config_path=str(file_path), cause=e
            )

    def _load_json_file(self, file_path: Path) -> Dict[str, Any]:
        """Load configuration from JSON file."""
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            raise OCDConfigError(
                f"Failed to load JSON file: {e}", config_path=str(file_path), cause=e
            )

    def _save_toml_file(self, file_path: Path, data: Dict[str, Any]) -> None:
        """Save configuration to TOML file."""
        try:
            with open(file_path, "w", encoding="utf-8") as f:
                toml.dump(data, f)
        except Exception as e:
            raise OCDConfigError(
                f"Failed to save TOML file: {e}", config_path=str(file_path), cause=e
            )

    def _save_json_file(self, file_path: Path, data: Dict[str, Any]) -> None:
        """Save configuration to JSON file."""
        try:
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, default=str)
        except Exception as e:
            raise OCDConfigError(
                f"Failed to save JSON file: {e}", config_path=str(file_path), cause=e
            )

    def reset_to_defaults(self) -> None:
        """Reset configuration to defaults."""
        logger.info("Resetting configuration to defaults")
        self.settings = OCDSettings()
        self._loaded = True

    def validate_config(self) -> List[str]:
        """
        Validate current configuration.

        Returns:
            List of validation errors (empty if valid)
        """
        errors = []

        if not self.settings:
            errors.append("No configuration loaded")
            return errors

        try:
            # Validate provider configurations
            for provider_name, provider_config in self.settings.providers.items():
                if not provider_config.name:
                    errors.append(f"Provider '{provider_name}' missing name")

                if not provider_config.provider_type:
                    errors.append(f"Provider '{provider_name}' missing type")

            # Validate directories are writable
            for dir_path in [
                self.settings.config_dir,
                self.settings.cache_dir,
                self.settings.logs_dir,
            ]:
                if not dir_path.exists():
                    try:
                        dir_path.mkdir(parents=True, exist_ok=True)
                    except Exception as e:
                        errors.append(f"Cannot create directory {dir_path}: {e}")
                elif not dir_path.is_dir():
                    errors.append(f"Path is not a directory: {dir_path}")

            # Validate numeric ranges
            if self.settings.max_files_analysis <= 0:
                errors.append("max_files_analysis must be positive")

            if self.settings.max_file_size <= 0:
                errors.append("max_file_size must be positive")

            if not 0.0 <= self.settings.default_temperature <= 2.0:
                errors.append("default_temperature must be between 0.0 and 2.0")

        except Exception as e:
            errors.append(f"Validation error: {e}")

        return errors
