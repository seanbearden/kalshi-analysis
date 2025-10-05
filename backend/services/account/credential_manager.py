"""Secure credential storage and retrieval using Fernet encryption."""

from cryptography.fernet import Fernet
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import get_settings
from core.exceptions import ConfigurationError
from domain.models.account import UserCredential


class CredentialManager:
    """Manage encrypted user API credentials.

    Uses Fernet (AES-128-CBC + HMAC-SHA256) for symmetric encryption of Kalshi API keys.
    Encryption key must be set in ENCRYPTION_SECRET_KEY environment variable.

    For Phase 1 (single-user), user_id is always "default".
    """

    def __init__(self, session: AsyncSession):
        """Initialize credential manager.

        Args:
            session: Async database session

        Raises:
            ConfigurationError: If ENCRYPTION_SECRET_KEY is not set
        """
        self.session = session
        settings = get_settings()

        if not settings.encryption_secret_key:
            raise ConfigurationError(
                "ENCRYPTION_SECRET_KEY environment variable must be set. "
                'Generate with: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"'
            )

        self.cipher = Fernet(settings.encryption_secret_key.encode())

    async def store_credentials(self, user_id: str, api_key: str) -> None:
        """Encrypt and store user API key.

        Args:
            user_id: User identifier (default="default" for Phase 1)
            api_key: Plain Kalshi API key to encrypt

        Raises:
            ValueError: If api_key is empty or invalid
        """
        if not api_key or not api_key.strip():
            raise ValueError("API key cannot be empty")

        # Encrypt the API key
        encrypted_key = self.cipher.encrypt(api_key.encode()).decode()

        # Upsert to database
        stmt = select(UserCredential).where(UserCredential.user_id == user_id)
        result = await self.session.execute(stmt)
        credential = result.scalar_one_or_none()

        if credential:
            # Update existing credential
            credential.encrypted_api_key = encrypted_key
        else:
            # Insert new credential
            credential = UserCredential(
                user_id=user_id,
                encrypted_api_key=encrypted_key,
            )
            self.session.add(credential)

        await self.session.commit()

    async def get_credentials(self, user_id: str) -> str | None:
        """Decrypt and return user API key.

        Args:
            user_id: User identifier

        Returns:
            Decrypted API key or None if not found

        Raises:
            cryptography.fernet.InvalidToken: If decryption fails (corrupted data or wrong key)
        """
        stmt = select(UserCredential).where(UserCredential.user_id == user_id)
        result = await self.session.execute(stmt)
        credential = result.scalar_one_or_none()

        if not credential:
            return None

        # Decrypt the API key
        decrypted_key = self.cipher.decrypt(credential.encrypted_api_key.encode()).decode()
        return decrypted_key

    async def delete_credentials(self, user_id: str) -> None:
        """Remove user API key from storage.

        Args:
            user_id: User identifier
        """
        stmt = select(UserCredential).where(UserCredential.user_id == user_id)
        result = await self.session.execute(stmt)
        credential = result.scalar_one_or_none()

        if credential:
            await self.session.delete(credential)
            await self.session.commit()

    async def credentials_exist(self, user_id: str) -> bool:
        """Check if credentials exist for user.

        Args:
            user_id: User identifier

        Returns:
            True if credentials exist, False otherwise
        """
        stmt = select(UserCredential).where(UserCredential.user_id == user_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none() is not None
