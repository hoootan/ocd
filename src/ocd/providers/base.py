"""
Base Provider Interface
======================

Abstract base class and factory for AI providers implementing the Strategy pattern.
All providers must implement this interface for consistent behavior.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Type

from ocd.core.exceptions import OCDProviderError
from ocd.core.types import ProviderConfig, ProviderType, TaskRequest, TaskResponse


class BaseProvider(ABC):
    """
    Abstract base class for all AI providers.

    Implements the Strategy pattern to allow seamless switching between
    different AI providers (local SLMs, local LLMs, remote APIs).
    """

    def __init__(self, config: ProviderConfig):
        """Initialize provider with configuration."""
        self.config = config
        self.name = config.name
        self.provider_type = config.provider_type
        self._initialized = False

    @property
    def is_initialized(self) -> bool:
        """Check if provider is initialized and ready."""
        return self._initialized

    @property
    def is_available(self) -> bool:
        """Check if provider is available (online, has credentials, etc.)."""
        if not self.is_initialized:
            return False
        return self._check_availability()

    @abstractmethod
    async def initialize(self) -> None:
        """
        Initialize the provider.

        This method should:
        - Set up authentication
        - Verify connectivity
        - Load models (for local providers)
        - Set _initialized = True on success

        Raises:
            OCDProviderError: If initialization fails
        """
        pass

    @abstractmethod
    async def execute_task(self, request: TaskRequest) -> TaskResponse:
        """
        Execute an AI task.

        Args:
            request: Task request with prompt, context, and settings

        Returns:
            Task response with result and metadata

        Raises:
            OCDProviderError: If task execution fails
        """
        pass

    @abstractmethod
    def _check_availability(self) -> bool:
        """
        Check if provider is currently available.

        Returns:
            True if provider can handle requests
        """
        pass

    @abstractmethod
    async def cleanup(self) -> None:
        """
        Clean up provider resources.

        Should be called when provider is no longer needed.
        """
        pass

    def get_supported_tasks(self) -> List[str]:
        """
        Get list of supported task types.

        Returns:
            List of task type strings this provider can handle
        """
        return [
            "analyze_directory",
            "generate_script",
            "summarize_content",
            "extract_patterns",
            "classify_files",
        ]

    def validate_request(self, request: TaskRequest) -> None:
        """
        Validate a task request.

        Args:
            request: Task request to validate

        Raises:
            OCDProviderError: If request is invalid
        """
        if not request.task_type:
            raise OCDProviderError("Task type is required")

        if not request.prompt:
            raise OCDProviderError("Prompt is required")

        if request.task_type not in self.get_supported_tasks():
            raise OCDProviderError(
                f"Task type '{request.task_type}' not supported by {self.name}",
                provider_name=self.name,
                context={"supported_tasks": self.get_supported_tasks()},
            )

    def __repr__(self) -> str:
        """String representation of provider."""
        return f"{self.__class__.__name__}(name='{self.name}', type='{self.provider_type}')"


class ProviderFactory:
    """
    Factory for creating AI providers.

    Implements the Factory pattern to abstract provider creation.
    """

    _providers: Dict[ProviderType, Type[BaseProvider]] = {}

    @classmethod
    def register_provider(
        cls, provider_type: ProviderType, provider_class: Type[BaseProvider]
    ) -> None:
        """
        Register a provider class for a specific type.

        Args:
            provider_type: Type of provider
            provider_class: Provider class to register
        """
        cls._providers[provider_type] = provider_class

    @classmethod
    def create_provider(cls, config: ProviderConfig) -> BaseProvider:
        """
        Create a provider instance from configuration.

        Args:
            config: Provider configuration

        Returns:
            Initialized provider instance

        Raises:
            OCDProviderError: If provider type is not supported
        """
        provider_class = cls._providers.get(config.provider_type)

        if not provider_class:
            raise OCDProviderError(
                f"Provider type '{config.provider_type}' not supported",
                provider_type=config.provider_type.value,
                context={"available_types": list(cls._providers.keys())},
            )

        return provider_class(config)

    @classmethod
    def get_supported_types(cls) -> List[ProviderType]:
        """Get list of supported provider types."""
        return list(cls._providers.keys())

    @classmethod
    def list_providers(cls) -> Dict[ProviderType, str]:
        """Get mapping of provider types to class names."""
        return {
            provider_type: provider_class.__name__
            for provider_type, provider_class in cls._providers.items()
        }
