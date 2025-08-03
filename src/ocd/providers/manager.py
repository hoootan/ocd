"""
Provider Manager
===============

Manages multiple AI providers with automatic failover, load balancing,
and provider selection strategies.
"""

import asyncio
import time
from typing import Dict, List, Optional, Sequence
import structlog

from ocd.core.exceptions import OCDProviderError
from ocd.core.types import ProviderConfig, TaskRequest, TaskResponse
from ocd.providers.base import BaseProvider, ProviderFactory

logger = structlog.get_logger(__name__)


class ProviderManager:
    """
    Manages multiple AI providers with failover and selection strategies.

    Features:
    - Automatic failover on provider failures
    - Load balancing across providers
    - Provider health monitoring
    - Graceful degradation
    """

    def __init__(self, configs: Dict[str, ProviderConfig]):
        """
        Initialize provider manager.

        Args:
            configs: Dictionary of provider configurations
        """
        self.configs = configs
        self.providers: Dict[str, BaseProvider] = {}
        self.provider_health: Dict[str, bool] = {}
        self.provider_stats: Dict[str, Dict[str, int]] = {}
        self._initialized = False

    async def initialize(self) -> None:
        """Initialize all providers."""
        logger.info("Initializing provider manager", provider_count=len(self.configs))

        # Create providers
        for name, config in self.configs.items():
            try:
                provider = ProviderFactory.create_provider(config)
                self.providers[name] = provider
                self.provider_health[name] = False
                self.provider_stats[name] = {
                    "requests": 0,
                    "successes": 0,
                    "failures": 0,
                    "avg_response_time": 0.0,
                }
                logger.info(
                    "Created provider",
                    provider_name=name,
                    provider_type=config.provider_type,
                )

            except Exception as e:
                logger.error(
                    "Failed to create provider", provider_name=name, error=str(e)
                )

        # Initialize providers concurrently
        initialization_tasks = []
        for name, provider in self.providers.items():
            task = self._initialize_provider(name, provider)
            initialization_tasks.append(task)

        if initialization_tasks:
            await asyncio.gather(*initialization_tasks, return_exceptions=True)

        # Check if any providers are available
        available_providers = [
            name for name, health in self.provider_health.items() if health
        ]
        if not available_providers:
            logger.warning("No providers are available")
        else:
            logger.info(
                "Provider manager initialized", available_providers=available_providers
            )

        self._initialized = True

    async def _initialize_provider(self, name: str, provider: BaseProvider) -> None:
        """Initialize a single provider."""
        try:
            await provider.initialize()
            self.provider_health[name] = provider.is_available
            logger.info(
                "Provider initialized",
                provider_name=name,
                available=self.provider_health[name],
            )

        except Exception as e:
            logger.error(
                "Provider initialization failed", provider_name=name, error=str(e)
            )
            self.provider_health[name] = False

    async def execute_task(
        self, request: TaskRequest, preferred_providers: Optional[Sequence[str]] = None
    ) -> TaskResponse:
        """
        Execute a task using available providers with failover.

        Args:
            request: Task request
            preferred_providers: Ordered list of preferred providers

        Returns:
            Task response from successful provider

        Raises:
            OCDProviderError: If all providers fail
        """
        if not self._initialized:
            raise OCDProviderError("Provider manager not initialized")

        # Determine provider order
        provider_order = self._get_provider_order(request, preferred_providers)

        if not provider_order:
            raise OCDProviderError("No available providers")

        last_error = None

        for provider_name in provider_order:
            if not self.provider_health.get(provider_name, False):
                logger.debug("Skipping unhealthy provider", provider_name=provider_name)
                continue

            provider = self.providers.get(provider_name)
            if not provider:
                continue

            try:
                logger.info(
                    "Executing task",
                    provider_name=provider_name,
                    task_type=request.task_type,
                )

                start_time = time.time()
                response = await provider.execute_task(request)
                execution_time = time.time() - start_time

                # Update statistics
                self._update_provider_stats(provider_name, True, execution_time)

                logger.info(
                    "Task completed successfully",
                    provider_name=provider_name,
                    execution_time=execution_time,
                )

                return response

            except Exception as e:
                last_error = e
                self._update_provider_stats(provider_name, False, 0)

                logger.warning(
                    "Provider failed, trying next",
                    provider_name=provider_name,
                    error=str(e),
                )

                # Mark provider as unhealthy on repeated failures
                if self.provider_stats[provider_name]["failures"] >= 3:
                    self.provider_health[provider_name] = False
                    logger.warning(
                        "Marking provider as unhealthy", provider_name=provider_name
                    )

        # All providers failed
        raise OCDProviderError(
            "All providers failed to execute task",
            context={
                "task_type": request.task_type,
                "attempted_providers": provider_order,
                "last_error": str(last_error) if last_error else None,
            },
        )

    def _get_provider_order(
        self, request: TaskRequest, preferred_providers: Optional[Sequence[str]] = None
    ) -> List[str]:
        """
        Determine the order of providers to try.

        Args:
            request: Task request (may contain provider preference)
            preferred_providers: External provider preferences

        Returns:
            Ordered list of provider names to try
        """
        # Start with preferred providers
        provider_order = []

        # 1. Request-specific preference
        if (
            request.provider_preference
            and request.provider_preference in self.providers
        ):
            provider_order.append(request.provider_preference)

        # 2. External preferences
        if preferred_providers:
            for provider in preferred_providers:
                if provider in self.providers and provider not in provider_order:
                    provider_order.append(provider)

        # 3. Add remaining healthy providers sorted by success rate
        remaining_providers = [
            name
            for name in self.providers.keys()
            if name not in provider_order and self.provider_health.get(name, False)
        ]

        # Sort by success rate (descending)
        remaining_providers.sort(
            key=lambda name: self._get_success_rate(name), reverse=True
        )

        provider_order.extend(remaining_providers)

        return provider_order

    def _get_success_rate(self, provider_name: str) -> float:
        """Calculate success rate for a provider."""
        stats = self.provider_stats.get(provider_name, {})
        total = stats.get("requests", 0)
        if total == 0:
            return 1.0  # No history, assume perfect
        return stats.get("successes", 0) / total

    def _update_provider_stats(
        self, provider_name: str, success: bool, execution_time: float
    ) -> None:
        """Update provider statistics."""
        stats = self.provider_stats[provider_name]
        stats["requests"] += 1

        if success:
            stats["successes"] += 1
            # Update rolling average response time
            current_avg = stats["avg_response_time"]
            stats["avg_response_time"] = (current_avg + execution_time) / 2
        else:
            stats["failures"] += 1

    async def health_check(self) -> Dict[str, bool]:
        """
        Perform health check on all providers.

        Returns:
            Dictionary of provider health status
        """
        health_tasks = []

        for name, provider in self.providers.items():
            task = self._check_provider_health(name, provider)
            health_tasks.append(task)

        if health_tasks:
            await asyncio.gather(*health_tasks, return_exceptions=True)

        return self.provider_health.copy()

    async def _check_provider_health(self, name: str, provider: BaseProvider) -> None:
        """Check health of a single provider."""
        try:
            is_available = provider.is_available
            self.provider_health[name] = is_available
            logger.debug(
                "Health check completed", provider_name=name, healthy=is_available
            )

        except Exception as e:
            self.provider_health[name] = False
            logger.warning("Health check failed", provider_name=name, error=str(e))

    def get_provider_stats(self) -> Dict[str, Dict]:
        """Get statistics for all providers."""
        stats = {}
        for name, provider_stats in self.provider_stats.items():
            stats[name] = {
                **provider_stats,
                "healthy": self.provider_health.get(name, False),
                "success_rate": self._get_success_rate(name),
                "provider_type": self.configs[name].provider_type.value,
            }
        return stats

    async def cleanup(self) -> None:
        """Clean up all providers."""
        logger.info("Cleaning up provider manager")

        cleanup_tasks = []
        for provider in self.providers.values():
            task = provider.cleanup()
            cleanup_tasks.append(task)

        if cleanup_tasks:
            await asyncio.gather(*cleanup_tasks, return_exceptions=True)

        logger.info("Provider manager cleanup completed")
