"""
Configuration Management
=======================

Configuration system for OCD with hierarchical settings,
environment variable support, and validation.
"""

from ocd.config.manager import ConfigManager
from ocd.config.settings import OCDSettings

__all__ = [
    "ConfigManager",
    "OCDSettings",
]
