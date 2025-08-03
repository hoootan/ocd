"""
Provider Registry
================

Registers all available providers with the factory for automatic discovery.
"""

from ocd.core.types import ProviderType
from ocd.providers.base import ProviderFactory
from ocd.providers.local_slm import LocalSLMProvider
from ocd.providers.remote_api import RemoteAPIProvider


def register_all_providers() -> None:
    """Register all available providers with the factory."""

    # Register Local SLM Provider
    ProviderFactory.register_provider(ProviderType.LOCAL_SLM, LocalSLMProvider)

    # Register Remote API Provider
    ProviderFactory.register_provider(ProviderType.REMOTE_API, RemoteAPIProvider)

    # TODO: Add local LLM provider when implemented
    # ProviderFactory.register_provider(ProviderType.LOCAL_LLM, LocalLLMProvider)


# Auto-register on import
register_all_providers()
