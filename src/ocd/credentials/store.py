"""
Credential Store Interface
=========================

Simple interface functions for credential operations.
"""

from typing import List, Optional

from ocd.core.types import CredentialInfo
from ocd.credentials.manager import CredentialManager

# Global credential manager instance
_credential_manager: Optional[CredentialManager] = None


def _get_manager() -> CredentialManager:
    """Get or create the global credential manager."""
    global _credential_manager
    if _credential_manager is None:
        _credential_manager = CredentialManager()
    return _credential_manager


async def set_credential(key: str, value: str, provider: str = "unknown") -> None:
    """
    Store a credential securely.

    Args:
        key: Credential key/name
        value: Credential value
        provider: Provider name for organization
    """
    manager = _get_manager()
    await manager.set_credential(key, value, provider)


async def get_credential(key: str) -> Optional[str]:
    """
    Retrieve a credential.

    Args:
        key: Credential key/name

    Returns:
        Credential value or None if not found
    """
    manager = _get_manager()
    return await manager.get_credential(key)


async def delete_credential(key: str) -> bool:
    """
    Delete a credential.

    Args:
        key: Credential key/name

    Returns:
        True if deleted, False if not found
    """
    manager = _get_manager()
    return await manager.delete_credential(key)


async def list_credentials() -> List[CredentialInfo]:
    """
    List all stored credentials.

    Returns:
        List of credential information
    """
    manager = _get_manager()
    return await manager.list_credentials()
