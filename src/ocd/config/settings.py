"""
OCD Settings
===========

Pydantic-based settings with environment variable support
and hierarchical configuration.
"""

from pathlib import Path
from typing import Dict, List, Optional

from pydantic import Field
from pydantic_settings import BaseSettings

from ocd.core.types import ProviderConfig


class OCDSettings(BaseSettings):
    """
    Main OCD configuration settings.

    Supports environment variables with OCD_ prefix.
    """

    # General settings
    default_provider: str = Field(
        default="local_slm", description="Default AI provider"
    )
    max_files_analysis: int = Field(
        default=10000, description="Maximum files to analyze"
    )
    max_file_size: int = Field(
        default=10 * 1024 * 1024, description="Maximum file size to process (bytes)"
    )
    max_directory_depth: int = Field(
        default=10, description="Maximum directory depth to traverse"
    )

    # Provider configurations
    providers: Dict[str, ProviderConfig] = Field(
        default_factory=dict, description="AI provider configurations"
    )

    # Directories
    config_dir: Path = Field(
        default=Path.home() / ".ocd", description="Configuration directory"
    )
    templates_dir: Path = Field(
        default=Path.home() / ".ocd" / "templates", description="Templates directory"
    )
    cache_dir: Path = Field(
        default=Path.home() / ".ocd" / "cache", description="Cache directory"
    )
    logs_dir: Path = Field(
        default=Path.home() / ".ocd" / "logs", description="Logs directory"
    )

    # Analysis settings
    excluded_dirs: List[str] = Field(
        default=[
            ".git",
            ".svn",
            ".hg",
            "__pycache__",
            "node_modules",
            ".venv",
            "venv",
            "env",
            ".env",
            "build",
            "dist",
            ".DS_Store",
            "Thumbs.db",
            ".tmp",
            "temp",
        ],
        description="Directories to exclude from analysis",
    )

    excluded_extensions: List[str] = Field(
        default=[
            ".pyc",
            ".pyo",
            ".pyd",
            ".so",
            ".dll",
            ".dylib",
            ".exe",
            ".bin",
            ".obj",
            ".o",
            ".class",
            ".jar",
            ".log",
            ".tmp",
            ".temp",
            ".cache",
            ".lock",
        ],
        description="File extensions to exclude from analysis",
    )

    # Execution settings
    execution_timeout: float = Field(
        default=300.0, description="Script execution timeout (seconds)"
    )
    enable_script_execution: bool = Field(
        default=False, description="Enable script execution"
    )
    allowed_script_languages: List[str] = Field(
        default=["bash", "python", "powershell"], description="Allowed script languages"
    )

    # Security settings
    require_confirmation: bool = Field(
        default=True, description="Require confirmation for dangerous operations"
    )
    safe_mode: bool = Field(default=True, description="Enable safe mode restrictions")

    # Logging settings
    log_level: str = Field(default="INFO", description="Logging level")
    log_format: str = Field(default="json", description="Log format: json, text")

    # AI settings
    default_temperature: float = Field(
        default=0.7, description="Default AI temperature"
    )
    default_max_tokens: int = Field(default=2000, description="Default maximum tokens")

    class Config:
        """Pydantic configuration."""

        env_prefix = "OCD_"
        case_sensitive = False
        env_file = ".env"
        env_file_encoding = "utf-8"

    def create_directories(self) -> None:
        """Create necessary directories."""
        directories = [
            self.config_dir,
            self.templates_dir,
            self.cache_dir,
            self.logs_dir,
        ]

        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)

    def get_provider_config(self, provider_name: str) -> Optional[ProviderConfig]:
        """Get configuration for a specific provider."""
        return self.providers.get(provider_name)

    def add_provider_config(self, provider_config: ProviderConfig) -> None:
        """Add or update provider configuration."""
        self.providers[provider_config.name] = provider_config

    def remove_provider_config(self, provider_name: str) -> bool:
        """Remove provider configuration."""
        if provider_name in self.providers:
            del self.providers[provider_name]
            return True
        return False
