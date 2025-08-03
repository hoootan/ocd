"""
OCD Core Exceptions
==================

Defines custom exceptions for the OCD system with proper error handling
and context information.
"""

from typing import Any, Dict, Optional


class OCDError(Exception):
    """Base exception for all OCD-related errors."""

    def __init__(
        self,
        message: str,
        context: Optional[Dict[str, Any]] = None,
        cause: Optional[Exception] = None,
    ):
        super().__init__(message)
        self.message = message
        self.context = context or {}
        self.cause = cause

    def __str__(self) -> str:
        """Return formatted error message with context."""
        parts = [self.message]

        if self.context:
            context_str = ", ".join(f"{k}={v}" for k, v in self.context.items())
            parts.append(f"Context: {context_str}")

        if self.cause:
            parts.append(f"Caused by: {self.cause}")

        return " | ".join(parts)


class OCDConfigError(OCDError):
    """Raised when there's an issue with configuration."""

    def __init__(
        self,
        message: str,
        config_path: Optional[str] = None,
        config_key: Optional[str] = None,
        **kwargs,
    ):
        context = kwargs.get("context", {})
        if config_path:
            context["config_path"] = config_path
        if config_key:
            context["config_key"] = config_key

        super().__init__(message, context, kwargs.get("cause"))


class OCDProviderError(OCDError):
    """Raised when there's an issue with AI providers."""

    def __init__(
        self,
        message: str,
        provider_name: Optional[str] = None,
        provider_type: Optional[str] = None,
        **kwargs,
    ):
        context = kwargs.get("context", {})
        if provider_name:
            context["provider_name"] = provider_name
        if provider_type:
            context["provider_type"] = provider_type

        super().__init__(message, context, kwargs.get("cause"))


class OCDCredentialError(OCDError):
    """Raised when there's an issue with credentials management."""

    def __init__(self, message: str, credential_key: Optional[str] = None, **kwargs):
        context = kwargs.get("context", {})
        if credential_key:
            context["credential_key"] = credential_key

        super().__init__(message, context, kwargs.get("cause"))


class OCDAnalysisError(OCDError):
    """Raised when directory analysis fails."""

    def __init__(
        self,
        message: str,
        directory_path: Optional[str] = None,
        analysis_type: Optional[str] = None,
        **kwargs,
    ):
        context = kwargs.get("context", {})
        if directory_path:
            context["directory_path"] = directory_path
        if analysis_type:
            context["analysis_type"] = analysis_type

        super().__init__(message, context, kwargs.get("cause"))


class OCDExecutionError(OCDError):
    """Raised when script execution fails."""

    def __init__(
        self,
        message: str,
        script_path: Optional[str] = None,
        exit_code: Optional[int] = None,
        **kwargs,
    ):
        context = kwargs.get("context", {})
        if script_path:
            context["script_path"] = script_path
        if exit_code is not None:
            context["exit_code"] = exit_code

        super().__init__(message, context, kwargs.get("cause"))


class OCDValidationError(OCDError):
    """Raised when data validation fails."""

    def __init__(
        self,
        message: str,
        field_name: Optional[str] = None,
        field_value: Optional[Any] = None,
        **kwargs,
    ):
        context = kwargs.get("context", {})
        if field_name:
            context["field_name"] = field_name
        if field_value is not None:
            context["field_value"] = str(field_value)

        super().__init__(message, context, kwargs.get("cause"))


class OCDTimeoutError(OCDError):
    """Raised when operations timeout."""

    def __init__(
        self,
        message: str,
        operation: Optional[str] = None,
        timeout_seconds: Optional[float] = None,
        **kwargs,
    ):
        context = kwargs.get("context", {})
        if operation:
            context["operation"] = operation
        if timeout_seconds is not None:
            context["timeout_seconds"] = timeout_seconds

        super().__init__(message, context, kwargs.get("cause"))


class OCDPermissionError(OCDError):
    """Raised when permission issues occur."""

    def __init__(
        self,
        message: str,
        resource_path: Optional[str] = None,
        required_permission: Optional[str] = None,
        **kwargs,
    ):
        context = kwargs.get("context", {})
        if resource_path:
            context["resource_path"] = resource_path
        if required_permission:
            context["required_permission"] = required_permission

        super().__init__(message, context, kwargs.get("cause"))


class OCDModelError(OCDError):
    """Raised when SLM model operations fail."""

    def __init__(
        self,
        message: str,
        model_name: Optional[str] = None,
        model_type: Optional[str] = None,
        **kwargs,
    ):
        context = kwargs.get("context", {})
        if model_name:
            context["model_name"] = model_name
        if model_type:
            context["model_type"] = model_type

        super().__init__(message, context, kwargs.get("cause"))
