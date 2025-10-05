"""Unit tests for CredentialManager."""

import pytest
from cryptography.fernet import Fernet, InvalidToken
from sqlalchemy import select

from core.config import Settings
from core.exceptions import ConfigurationError
from domain.models.account import UserCredential
from services.account.credential_manager import CredentialManager


class TestCredentialManager:
    """Test suite for CredentialManager."""

    @pytest.mark.asyncio
    async def test_initialization_success(self, session, mock_settings):
        """Test CredentialManager initializes successfully with valid encryption key."""
        manager = CredentialManager(session)
        assert manager.cipher is not None
        assert isinstance(manager.cipher, Fernet)

    @pytest.mark.asyncio
    async def test_initialization_missing_key(self, session, monkeypatch):
        """Test CredentialManager raises ConfigurationError when encryption key is missing."""

        def mock_get_settings_no_key():
            return Settings(
                db_url="postgresql+asyncpg://test:test@localhost/test",  # pragma: allowlist secret
                encryption_secret_key=None,
            )

        monkeypatch.setattr(
            "services.account.credential_manager.get_settings", mock_get_settings_no_key
        )

        with pytest.raises(ConfigurationError) as exc_info:
            CredentialManager(session)

        assert "ENCRYPTION_SECRET_KEY" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_store_credentials_new_user(self, session, mock_settings):
        """Test storing credentials for a new user."""
        manager = CredentialManager(session)
        api_key = "test_api_key_12345"  # pragma: allowlist secret

        await manager.store_credentials("test_user", api_key)

        # Verify credential was stored
        stmt = select(UserCredential).where(UserCredential.user_id == "test_user")
        result = await session.execute(stmt)
        credential = result.scalar_one()

        assert credential.user_id == "test_user"
        assert credential.encrypted_api_key != api_key  # Should be encrypted
        assert len(credential.encrypted_api_key) > 0

    @pytest.mark.asyncio
    async def test_store_credentials_update_existing(self, session, mock_settings):
        """Test updating credentials for existing user."""
        manager = CredentialManager(session)
        user_id = "test_user"
        api_key_1 = "original_api_key"  # pragma: allowlist secret
        api_key_2 = "updated_api_key"  # pragma: allowlist secret

        # Store initial credentials
        await manager.store_credentials(user_id, api_key_1)

        # Update credentials
        await manager.store_credentials(user_id, api_key_2)

        # Verify only one credential exists and it's the updated one
        stmt = select(UserCredential).where(UserCredential.user_id == user_id)
        result = await session.execute(stmt)
        credentials = result.scalars().all()

        assert len(credentials) == 1
        decrypted = manager.cipher.decrypt(credentials[0].encrypted_api_key.encode()).decode()
        assert decrypted == api_key_2

    @pytest.mark.asyncio
    async def test_store_credentials_empty_key(self, session, mock_settings):
        """Test storing empty API key raises ValueError."""
        manager = CredentialManager(session)

        with pytest.raises(ValueError) as exc_info:
            await manager.store_credentials("test_user", "")

        assert "API key cannot be empty" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_get_credentials_success(self, session, mock_settings):
        """Test retrieving and decrypting credentials."""
        manager = CredentialManager(session)
        user_id = "test_user"
        api_key = "my_secret_kalshi_key"  # pragma: allowlist secret

        # Store credentials
        await manager.store_credentials(user_id, api_key)

        # Retrieve credentials
        retrieved_key = await manager.get_credentials(user_id)

        assert retrieved_key == api_key

    @pytest.mark.asyncio
    async def test_get_credentials_not_found(self, session, mock_settings):
        """Test retrieving credentials for non-existent user returns None."""
        manager = CredentialManager(session)

        result = await manager.get_credentials("nonexistent_user")

        assert result is None

    @pytest.mark.asyncio
    async def test_encryption_roundtrip(self, session, mock_settings):
        """Test encryption/decryption roundtrip maintains data integrity."""
        manager = CredentialManager(session)
        user_id = "test_user"
        original_key = "complex_api_key_with_special_chars!@#$%^&*()"  # pragma: allowlist secret

        # Store and retrieve
        await manager.store_credentials(user_id, original_key)
        retrieved_key = await manager.get_credentials(user_id)

        assert retrieved_key == original_key

    @pytest.mark.asyncio
    async def test_delete_credentials_success(self, session, mock_settings):
        """Test deleting credentials."""
        manager = CredentialManager(session)
        user_id = "test_user"
        api_key = "test_api_key"  # pragma: allowlist secret

        # Store credentials
        await manager.store_credentials(user_id, api_key)

        # Verify they exist
        assert await manager.credentials_exist(user_id) is True

        # Delete credentials
        await manager.delete_credentials(user_id)

        # Verify they're gone
        assert await manager.credentials_exist(user_id) is False

    @pytest.mark.asyncio
    async def test_delete_credentials_nonexistent(self, session, mock_settings):
        """Test deleting non-existent credentials doesn't raise error."""
        manager = CredentialManager(session)

        # Should not raise
        await manager.delete_credentials("nonexistent_user")

    @pytest.mark.asyncio
    async def test_credentials_exist_true(self, session, mock_settings):
        """Test credentials_exist returns True when credentials exist."""
        manager = CredentialManager(session)
        user_id = "test_user"

        await manager.store_credentials(user_id, "test_key")

        assert await manager.credentials_exist(user_id) is True

    @pytest.mark.asyncio
    async def test_credentials_exist_false(self, session, mock_settings):
        """Test credentials_exist returns False when credentials don't exist."""
        manager = CredentialManager(session)

        assert await manager.credentials_exist("nonexistent_user") is False

    @pytest.mark.asyncio
    async def test_multiple_users(self, session, mock_settings):
        """Test storing and retrieving credentials for multiple users."""
        manager = CredentialManager(session)

        users = {
            "user1": "key1",
            "user2": "key2",
            "user3": "key3",
        }

        # Store credentials for all users
        for user_id, api_key in users.items():
            await manager.store_credentials(user_id, api_key)

        # Verify all credentials can be retrieved correctly
        for user_id, expected_key in users.items():
            retrieved_key = await manager.get_credentials(user_id)
            assert retrieved_key == expected_key

    @pytest.mark.asyncio
    async def test_encryption_uses_different_ciphertext(self, session, mock_settings):
        """Test that encrypting the same plaintext twice produces different ciphertext (IV randomization)."""
        manager = CredentialManager(session)
        api_key = "same_plaintext"  # pragma: allowlist secret

        # Store for two different users
        await manager.store_credentials("user1", api_key)
        await manager.store_credentials("user2", api_key)

        # Get encrypted values from database
        stmt = select(UserCredential).where(UserCredential.user_id.in_(["user1", "user2"]))
        result = await session.execute(stmt)
        credentials = result.scalars().all()

        # Encrypted values should be different (Fernet uses random IV)
        encrypted_keys = [c.encrypted_api_key for c in credentials]
        assert encrypted_keys[0] != encrypted_keys[1]

        # But both decrypt to the same value
        for cred in credentials:
            decrypted = manager.cipher.decrypt(cred.encrypted_api_key.encode()).decode()
            assert decrypted == api_key

    @pytest.mark.asyncio
    async def test_decryption_with_wrong_key_fails(self, session, monkeypatch):
        """Test that decryption with wrong key raises InvalidToken."""
        # First create manager with test key and store credentials
        test_key = Fernet.generate_key().decode()

        def mock_get_settings_test_key():
            return Settings(
                db_url="postgresql+asyncpg://test:test@localhost/test",  # pragma: allowlist secret
                encryption_secret_key=test_key,
                jwt_secret_key="test",  # pragma: allowlist secret
            )

        monkeypatch.setattr(
            "services.account.credential_manager.get_settings", mock_get_settings_test_key
        )

        manager = CredentialManager(session)
        user_id = "test_user"
        api_key = "test_key"  # pragma: allowlist secret
        await manager.store_credentials(user_id, api_key)

        # Now create a different manager with a different encryption key
        different_key = Fernet.generate_key().decode()

        def mock_get_settings_different_key():
            return Settings(
                db_url="postgresql+asyncpg://test:test@localhost/test",  # pragma: allowlist secret
                encryption_secret_key=different_key,
                jwt_secret_key="test",  # pragma: allowlist secret
            )

        monkeypatch.setattr(
            "services.account.credential_manager.get_settings", mock_get_settings_different_key
        )

        wrong_key_manager = CredentialManager(session)

        # Should raise InvalidToken when trying to decrypt with wrong key
        with pytest.raises(InvalidToken):
            await wrong_key_manager.get_credentials(user_id)
