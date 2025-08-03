"""
OCD AI Providers
================

AI provider implementations using the Strategy pattern for seamless
switching between local SLMs, local LLMs, and remote APIs.
"""

from ocd.providers.base import BaseProvider, ProviderFactory
from ocd.providers.manager import ProviderManager

__all__ = [
    "BaseProvider",
    "ProviderFactory",
    "ProviderManager",
]
