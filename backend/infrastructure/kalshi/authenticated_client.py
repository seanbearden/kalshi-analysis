"""Authenticated Kalshi API client for user account operations."""

import logging
from typing import Any

from core.exceptions import AuthenticationError, KalshiAPIError
from infrastructure.kalshi.client import KalshiClient

logger = logging.getLogger(__name__)


class AuthenticatedKalshiClient(KalshiClient):
    """Kalshi API client with user authentication.

    Extends base KalshiClient with authenticated endpoints for portfolio,
    positions, and balance queries. Requires valid Kalshi API key.
    """

    def __init__(self, api_key: str) -> None:
        """Initialize authenticated client.

        Args:
            api_key: User's Kalshi API key for authentication

        Raises:
            ValueError: If api_key is empty or invalid
        """
        if not api_key or not api_key.strip():
            raise ValueError("API key cannot be empty")

        super().__init__()

        # Add Authorization header with API key
        self.client.headers.update({"Authorization": f"Bearer {api_key.strip()}"})
        self.api_key = api_key.strip()

    async def get_portfolio(self) -> dict[str, Any]:
        """Get complete portfolio snapshot.

        Returns:
            Portfolio data including balance and positions

        Raises:
            AuthenticationError: If API key is invalid
            KalshiAPIError: If request fails
        """
        try:
            return await self._request("GET", "/portfolio")
        except KalshiAPIError as e:
            if e.status_code == 401:
                raise AuthenticationError("Invalid API key") from e
            raise

    async def get_positions(self) -> list[dict[str, Any]]:
        """Get all open positions.

        Returns:
            List of position data dictionaries

        Raises:
            AuthenticationError: If API key is invalid
            KalshiAPIError: If request fails
        """
        try:
            response = await self._request("GET", "/portfolio/positions")
            # Kalshi API returns positions in a 'positions' key
            return response.get("positions", [])
        except KalshiAPIError as e:
            if e.status_code == 401:
                raise AuthenticationError("Invalid API key") from e
            raise

    async def get_balance(self) -> dict[str, Any]:
        """Get user balance information.

        Returns:
            Balance data with cash_balance and total_value

        Raises:
            AuthenticationError: If API key is invalid
            KalshiAPIError: If request fails
        """
        try:
            return await self._request("GET", "/portfolio/balance")
        except KalshiAPIError as e:
            if e.status_code == 401:
                raise AuthenticationError("Invalid API key") from e
            raise

    async def verify_credentials(self) -> bool:
        """Verify API key is valid by attempting a simple authenticated request.

        Returns:
            True if credentials are valid, False otherwise
        """
        try:
            await self.get_balance()
            return True
        except AuthenticationError:
            return False
        except KalshiAPIError as e:
            logger.warning(f"Credential verification failed with API error: {e}")
            return False
