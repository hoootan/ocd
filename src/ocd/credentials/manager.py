"""
Credential Manager
=================

Cross-platform credential management using OS-native stores with
encrypted fallback for maximum security and compatibility.
"""

import platform
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import structlog

from ocd.core.exceptions import OCDCredentialError
from ocd.core.types import CredentialInfo

logger = structlog.get_logger(__name__)


class CredentialManager:
    """
    Cross-platform credential manager.

    Uses OS-native credential stores:
    - macOS: Keychain
    - Windows: Windows Credential Manager
    - Linux: Secret Service (libsecret) with encrypted file fallback
    """

    def __init__(self):
        """Initialize credential manager."""
        self.platform = platform.system().lower()
        self.backend = None
        self._initialize_backend()

    def _initialize_backend(self) -> None:
        """Initialize the appropriate credential backend."""
        try:
            import keyring

            # Test keyring functionality
            test_key = "ocd_test_key"
            test_value = "test_value"

            keyring.set_password("ocd_test", test_key, test_value)
            retrieved = keyring.get_password("ocd_test", test_key)
            keyring.delete_password("ocd_test", test_key)

            if retrieved == test_value:
                self.backend = "keyring"
                logger.info("Using keyring backend", platform=self.platform)
            else:
                raise Exception("Keyring test failed")

        except Exception as e:
            logger.warning(
                "Keyring not available, using encrypted file backend", error=str(e)
            )
            self.backend = "encrypted_file"
            self._initialize_encrypted_backend()

    def _initialize_encrypted_backend(self) -> None:
        """Initialize encrypted file backend."""
        try:
            from cryptography.fernet import Fernet
            import os
            from pathlib import Path

            # Create credentials directory
            self.creds_dir = Path.home() / ".ocd" / "credentials"
            self.creds_dir.mkdir(parents=True, exist_ok=True)

            # Generate or load encryption key
            key_file = self.creds_dir / "key.enc"
            if key_file.exists():
                with open(key_file, "rb") as f:
                    self.encryption_key = f.read()
            else:
                self.encryption_key = Fernet.generate_key()
                with open(key_file, "wb") as f:
                    f.write(self.encryption_key)
                # Set restrictive permissions
                os.chmod(key_file, 0o600)

            self.cipher = Fernet(self.encryption_key)

            # Credentials file
            self.creds_file = self.creds_dir / "credentials.enc"

            logger.info("Encrypted file backend initialized", creds_dir=self.creds_dir)

        except ImportError:
            raise OCDCredentialError(
                "Cryptography library required for encrypted storage. Install with: pip install cryptography"
            )

    async def set_credential(
        self, key: str, value: str, provider: str = "unknown"
    ) -> None:
        """
        Store a credential securely.

        Args:
            key: Credential key/name
            value: Credential value
            provider: Provider name for organization
        """
        try:
            if self.backend == "keyring":
                await self._set_keyring_credential(key, value, provider)
            else:
                await self._set_encrypted_credential(key, value, provider)

            logger.info(
                "Credential stored", key=key, provider=provider, backend=self.backend
            )

        except Exception as e:
            raise OCDCredentialError(
                f"Failed to store credential: {e}", credential_key=key, cause=e
            )

    async def get_credential(self, key: str) -> Optional[str]:
        """
        Retrieve a credential.

        Args:
            key: Credential key/name

        Returns:
            Credential value or None if not found
        """
        try:
            if self.backend == "keyring":
                return await self._get_keyring_credential(key)
            else:
                return await self._get_encrypted_credential(key)

        except Exception as e:
            logger.warning("Failed to retrieve credential", key=key, error=str(e))
            return None

    async def delete_credential(self, key: str) -> bool:
        """
        Delete a credential.

        Args:
            key: Credential key/name

        Returns:
            True if deleted, False if not found
        """
        try:
            if self.backend == "keyring":
                return await self._delete_keyring_credential(key)
            else:
                return await self._delete_encrypted_credential(key)

        except Exception as e:
            logger.warning("Failed to delete credential", key=key, error=str(e))
            return False

    async def list_credentials(self) -> List[CredentialInfo]:
        """
        List all stored credentials.

        Returns:
            List of credential information
        """
        try:
            if self.backend == "keyring":
                return await self._list_keyring_credentials()
            else:
                return await self._list_encrypted_credentials()

        except Exception as e:
            logger.warning("Failed to list credentials", error=str(e))
            return []

    # Keyring backend methods
    async def _set_keyring_credential(
        self, key: str, value: str, provider: str
    ) -> None:
        """Set credential using keyring."""
        import keyring

        service_name = f"ocd_{provider}"
        keyring.set_password(service_name, key, value)

    async def _get_keyring_credential(self, key: str) -> Optional[str]:
        """Get credential using keyring."""
        import keyring

        # Try different service names (for backward compatibility)
        service_names = [
            f"ocd_{provider}"
            for provider in ["openai", "anthropic", "google", "unknown"]
        ]
        service_names.append("ocd")  # Default service

        for service_name in service_names:
            try:
                value = keyring.get_password(service_name, key)
                if value:
                    return value
            except:
                continue

        return None

    async def _delete_keyring_credential(self, key: str) -> bool:
        """Delete credential using keyring."""
        import keyring

        # Try different service names
        service_names = [
            f"ocd_{provider}"
            for provider in ["openai", "anthropic", "google", "unknown"]
        ]
        service_names.append("ocd")

        deleted = False
        for service_name in service_names:
            try:
                keyring.delete_password(service_name, key)
                deleted = True
            except:
                continue

        return deleted

    async def _list_keyring_credentials(self) -> List[CredentialInfo]:
        """List credentials using keyring (limited functionality)."""
        # Keyring doesn't support listing, so return empty list
        # Could implement by maintaining a separate index
        return []

    # Encrypted file backend methods
    async def _set_encrypted_credential(
        self, key: str, value: str, provider: str
    ) -> None:
        """Set credential using encrypted file."""
        credentials = await self._load_encrypted_credentials()

        credentials[key] = {
            "value": value,
            "provider": provider,
            "created_at": datetime.now().isoformat(),
            "last_used": None,
        }

        await self._save_encrypted_credentials(credentials)

    async def _get_encrypted_credential(self, key: str) -> Optional[str]:
        """Get credential using encrypted file."""
        credentials = await self._load_encrypted_credentials()

        if key in credentials:
            # Update last used timestamp
            credentials[key]["last_used"] = datetime.now().isoformat()
            await self._save_encrypted_credentials(credentials)
            return credentials[key]["value"]

        return None

    async def _delete_encrypted_credential(self, key: str) -> bool:
        """Delete credential using encrypted file."""
        credentials = await self._load_encrypted_credentials()

        if key in credentials:
            del credentials[key]
            await self._save_encrypted_credentials(credentials)
            return True

        return False

    async def _list_encrypted_credentials(self) -> List[CredentialInfo]:
        """List credentials using encrypted file."""
        credentials = await self._load_encrypted_credentials()

        credential_list = []
        for key, data in credentials.items():
            created_at = datetime.fromisoformat(data["created_at"])
            last_used = None
            if data.get("last_used"):
                last_used = datetime.fromisoformat(data["last_used"])

            credential_list.append(
                CredentialInfo(
                    key_name=key,
                    provider=data["provider"],
                    encrypted=True,
                    created_at=created_at,
                    last_used=last_used,
                )
            )

        return credential_list

    async def _load_encrypted_credentials(self) -> Dict:
        """Load credentials from encrypted file."""
        if not self.creds_file.exists():
            return {}

        try:
            with open(self.creds_file, "rb") as f:
                encrypted_data = f.read()

            decrypted_data = self.cipher.decrypt(encrypted_data)

            import json

            return json.loads(decrypted_data.decode())

        except Exception as e:
            logger.error("Failed to load encrypted credentials", error=str(e))
            return {}

    async def _save_encrypted_credentials(self, credentials: Dict) -> None:
        """Save credentials to encrypted file."""
        try:
            import json
            import os

            json_data = json.dumps(credentials, indent=2)
            encrypted_data = self.cipher.encrypt(json_data.encode())

            # Write atomically
            temp_file = self.creds_file.with_suffix(".tmp")
            with open(temp_file, "wb") as f:
                f.write(encrypted_data)

            # Set restrictive permissions
            os.chmod(temp_file, 0o600)

            # Atomic rename
            temp_file.replace(self.creds_file)

        except Exception as e:
            logger.error("Failed to save encrypted credentials", error=str(e))
            raise OCDCredentialError(f"Failed to save credentials: {e}", cause=e)
