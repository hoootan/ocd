"""
Credential Management
====================

Secure cross-platform credential storage using OS-native stores
and encrypted fallback storage.
"""

from ocd.credentials.manager import CredentialManager
from ocd.credentials.store import (
    get_credential,
    set_credential,
    delete_credential,
    list_credentials,
)

__all__ = [
    "CredentialManager",
    "get_credential",
    "set_credential",
    "delete_credential",
    "list_credentials",
]
