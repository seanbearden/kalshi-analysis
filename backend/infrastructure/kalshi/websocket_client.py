"""Kalshi WebSocket client for real-time market data."""

import json
import logging
from collections.abc import AsyncIterator
from typing import Any

import websockets
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)
from websockets.exceptions import ConnectionClosed, WebSocketException

from core.config import get_settings

logger = logging.getLogger(__name__)


class KalshiWebSocketClient:
    """WebSocket client for Kalshi real-time market data.

    Features:
    - Automatic reconnection with exponential backoff
    - Market ticker subscription
    - Message streaming
    - Graceful error handling
    """

    def __init__(self) -> None:
        """Initialize WebSocket client with configuration."""
        settings = get_settings()
        self.endpoint = settings.kalshi_ws_url
        self.ws: Any = None  # WebSocket connection (type varies by websockets version)
        self._subscriptions: list[dict[str, Any]] = []

    @retry(
        stop=stop_after_attempt(5),
        wait=wait_exponential(multiplier=1, min=2, max=30),
        retry=retry_if_exception_type((ConnectionClosed, WebSocketException)),
    )
    async def connect(self) -> None:
        """Connect to WebSocket with exponential backoff retry.

        Raises:
            WebSocketException: If connection fails after retries
        """
        try:
            self.ws = await websockets.connect(self.endpoint)
            logger.info(f"WebSocket connected to {self.endpoint}")

            # Resubscribe to channels after reconnection
            for sub in self._subscriptions:
                await self._send(sub)

        except Exception as e:
            logger.error(f"WebSocket connection failed: {e}")
            raise

    async def subscribe(self, channel: dict[str, Any]) -> None:
        """Subscribe to a WebSocket channel.

        Args:
            channel: Subscription message (e.g., {'type': 'ticker', 'market_ticker': '*'})
        """
        if not self.ws:
            raise RuntimeError("WebSocket not connected. Call connect() first.")

        await self._send(channel)
        self._subscriptions.append(channel)
        logger.info(f"Subscribed to channel: {channel}")

    async def _send(self, message: dict[str, Any]) -> None:
        """Send message to WebSocket.

        Args:
            message: Message to send
        """
        if not self.ws:
            raise RuntimeError("WebSocket not connected")

        await self.ws.send(json.dumps(message))

    async def listen(self) -> AsyncIterator[dict[str, Any]]:
        """Listen for WebSocket messages.

        Yields:
            dict: Parsed JSON messages from WebSocket

        Raises:
            ConnectionClosed: When WebSocket connection is lost
        """
        if not self.ws:
            raise RuntimeError("WebSocket not connected. Call connect() first.")

        try:
            async for raw_message in self.ws:
                try:
                    message = json.loads(raw_message)
                    yield message
                except json.JSONDecodeError as e:
                    logger.error(f"Failed to parse WebSocket message: {e}")
                    continue

        except ConnectionClosed as e:
            logger.warning(f"WebSocket connection closed: {e}")
            raise

    async def close(self) -> None:
        """Close WebSocket connection gracefully."""
        if self.ws:
            await self.ws.close()
            self.ws = None
            logger.info("WebSocket connection closed")

    async def __aenter__(self) -> "KalshiWebSocketClient":
        """Async context manager entry."""
        await self.connect()
        return self

    async def __aexit__(
        self, exc_type: type[BaseException] | None, exc_val: BaseException | None, exc_tb: Any
    ) -> None:
        """Async context manager exit."""
        await self.close()
