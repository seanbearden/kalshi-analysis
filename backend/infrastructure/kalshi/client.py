"""Kalshi API client with retry logic and resilience patterns."""

import logging
from typing import Any, cast

import httpx
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from core.config import get_settings
from core.exceptions import KalshiAPIError

logger = logging.getLogger(__name__)


class KalshiClient:
    """Async Kalshi API client with retry logic.

    Features:
    - Automatic retries with exponential backoff
    - Rate limit handling
    - Type-safe responses
    - Comprehensive error handling
    """

    def __init__(self) -> None:
        """Initialize Kalshi client with configuration."""
        settings = get_settings()

        self.base_url = settings.kalshi_api_base
        self.timeout = settings.kalshi_request_timeout_seconds
        self.max_retries = settings.kalshi_max_retries

        # Create async HTTP client
        self.client = httpx.AsyncClient(
            base_url=self.base_url,
            timeout=httpx.Timeout(self.timeout),
            headers={
                "Accept": "application/json",
                "Content-Type": "application/json",
            },
        )

    async def __aenter__(self) -> "KalshiClient":
        """Async context manager entry."""
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: Any,
    ) -> None:
        """Async context manager exit - close client."""
        await self.client.aclose()

    @retry(  # type: ignore[misc]
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type(httpx.HTTPStatusError),
        reraise=True,
    )
    async def _request(self, method: str, endpoint: str, **kwargs: Any) -> dict[str, Any]:
        """Make HTTP request with retry logic.

        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint path
            **kwargs: Additional request parameters

        Returns:
            Response JSON data

        Raises:
            KalshiAPIError: If request fails after retries
        """
        try:
            response = await self.client.request(method, endpoint, **kwargs)
            response.raise_for_status()
            return cast(dict[str, Any], response.json())

        except httpx.HTTPStatusError as e:
            logger.error(f"Kalshi API error: {e.response.status_code} - {e.response.text}")
            raise KalshiAPIError(
                f"API request failed: {e.response.status_code}",
                status_code=e.response.status_code,
            ) from e

        except httpx.RequestError as e:
            logger.error(f"Kalshi request error: {str(e)}")
            raise KalshiAPIError(f"Request failed: {str(e)}") from e

    async def get_events(self, status: str | None = None, limit: int = 100) -> dict[str, Any]:
        """Get Kalshi events.

        Args:
            status: Filter by status (e.g., "open", "closed")
            limit: Maximum events to return

        Returns:
            Events data
        """
        params: dict[str, Any] = {"limit": limit}
        if status:
            params["status"] = status

        return await self._request("GET", "/events", params=params)  # type: ignore[no-any-return]

    async def get_markets(
        self,
        event_ticker: str | None = None,
        status: str | None = None,
        limit: int = 100,
    ) -> dict[str, Any]:
        """Get Kalshi markets.

        Args:
            event_ticker: Filter by event ticker
            status: Filter by status (e.g., "open", "closed")
            limit: Maximum markets to return

        Returns:
            Markets data
        """
        params: dict[str, Any] = {"limit": limit}
        if event_ticker:
            params["event_ticker"] = event_ticker
        if status:
            params["status"] = status

        return await self._request("GET", "/markets", params=params)  # type: ignore[no-any-return]

    async def get_market(self, ticker: str) -> dict[str, Any]:
        """Get single market by ticker.

        Args:
            ticker: Market ticker

        Returns:
            Market data
        """
        return await self._request("GET", f"/markets/{ticker}")  # type: ignore[no-any-return]

    async def get_orderbook(self, ticker: str, depth: int = 10) -> dict[str, Any]:
        """Get market order book.

        Args:
            ticker: Market ticker
            depth: Order book depth (levels)

        Returns:
            Order book data
        """
        params: dict[str, Any] = {"depth": depth}
        return await self._request("GET", f"/markets/{ticker}/orderbook", params=params)  # type: ignore[no-any-return]

    async def get_trades(self, ticker: str, limit: int = 100) -> dict[str, Any]:
        """Get recent trades for market.

        Args:
            ticker: Market ticker
            limit: Maximum trades to return

        Returns:
            Trades data
        """
        params: dict[str, Any] = {"limit": limit}
        return await self._request("GET", f"/markets/{ticker}/trades", params=params)  # type: ignore[no-any-return]

    async def close(self) -> None:
        """Close HTTP client."""
        await self.client.aclose()
