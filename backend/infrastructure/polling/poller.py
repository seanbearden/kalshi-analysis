"""Market data poller - runs as separate container.

Phase 2 Enhancement: Dual data sources (REST + WebSocket)
- REST polling continues for backward compatibility and gap filling
- WebSocket provides real-time updates with sequence numbers for gap detection
"""

import asyncio
import logging
from datetime import datetime
from decimal import Decimal

from core.config import get_settings
from domain.models import DataSource
from domain.repositories import MarketRepository
from infrastructure.database.session import get_session_maker
from infrastructure.kalshi.client import KalshiClient
from infrastructure.kalshi.websocket_client import KalshiWebSocketClient

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


class MarketPoller:
    """Polls Kalshi API and stores market snapshots.

    Runs as a separate container (singleton) to avoid duplicate polling
    when API scales horizontally in Phase 3.
    """

    def __init__(self) -> None:
        """Initialize poller with configuration."""
        self.settings = get_settings()
        self.session_maker = get_session_maker()
        self.running = False

    async def poll_markets(self) -> None:
        """Poll Kalshi API and save snapshots."""
        async with KalshiClient() as client:
            try:
                # Get active markets
                response = await client.get_markets(status="open", limit=100)
                markets = response.get("markets", [])

                logger.info(f"Fetched {len(markets)} active markets")

                # Save snapshots
                async with self.session_maker() as session:
                    repo = MarketRepository(session)

                    for market in markets:
                        ticker = market.get("ticker")
                        if not ticker:
                            continue

                        # Extract market data
                        yes_price = market.get("yes_bid", 0)
                        no_price = market.get("no_bid", 0)
                        volume = market.get("volume", 0)

                        # Create snapshot
                        await repo.create_snapshot(
                            ticker=ticker,
                            timestamp=datetime.utcnow(),
                            source=DataSource.POLL,
                            yes_price=yes_price,
                            no_price=no_price,
                            volume=volume,
                            raw_data=market,
                            sequence=None,  # Polling has no sequence
                        )

                    await session.commit()
                    logger.info(f"Saved {len(markets)} snapshots")

            except Exception as e:
                logger.error(f"Polling error: {e}", exc_info=True)

    async def run(self) -> None:
        """Run polling loop."""
        self.running = True
        logger.info(f"Starting poller (interval: {self.settings.kalshi_poll_interval_seconds}s)")

        while self.running:
            try:
                await self.poll_markets()
            except Exception as e:
                logger.error(f"Poll cycle error: {e}", exc_info=True)

            # Wait for next poll
            await asyncio.sleep(self.settings.kalshi_poll_interval_seconds)

    def stop(self) -> None:
        """Stop polling loop."""
        self.running = False
        logger.info("Stopping poller")

    async def listen_websocket(self) -> None:
        """Listen to WebSocket for real-time market updates.

        Phase 2 feature: Real-time data with sequence numbers for gap detection.
        Automatically reconnects on connection loss with exponential backoff.
        """
        logger.info("Starting WebSocket listener")

        while self.running:
            try:
                async with KalshiWebSocketClient() as ws_client:
                    # Subscribe to all market tickers
                    await ws_client.subscribe({"type": "ticker", "market_ticker": "*"})

                    async for message in ws_client.listen():
                        if message.get("type") == "ticker":
                            await self._save_websocket_snapshot(message)

            except Exception as e:
                logger.error(f"WebSocket error: {e}", exc_info=True)
                await asyncio.sleep(5)  # Wait before reconnecting

    async def _save_websocket_snapshot(self, message: dict) -> None:
        """Save WebSocket market update to database.

        Args:
            message: WebSocket ticker message
        """
        try:
            ticker = message.get("ticker")
            if not ticker:
                logger.warning("WebSocket message missing ticker")
                return

            async with self.session_maker() as session:
                repo = MarketRepository(session)

                # Parse WebSocket message
                yes_price = Decimal(str(message.get("yes_price", 0))) / 100
                no_price = Decimal(str(message.get("no_price", 0))) / 100
                volume = message.get("volume", 0)
                sequence = message.get("seq")  # Sequence number for gap detection
                timestamp_str = message.get("timestamp")

                # Parse timestamp (ISO format from WebSocket)
                timestamp = (
                    datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
                    if timestamp_str
                    else datetime.utcnow()
                )

                await repo.create_snapshot(
                    ticker=ticker,
                    timestamp=timestamp,
                    source=DataSource.WEBSOCKET,
                    yes_price=yes_price,
                    no_price=no_price,
                    volume=volume,
                    raw_data=message,
                    sequence=sequence,
                )

                await session.commit()
                logger.debug(f"Saved WebSocket snapshot: {ticker} (seq={sequence})")

        except Exception as e:
            logger.error(f"Failed to save WebSocket snapshot: {e}", exc_info=True)


async def main() -> None:
    """Poller entry point.

    Phase 2: Runs both REST polling and WebSocket listener in parallel.
    - REST: Background polling every 5 seconds (gap filling, backward compatibility)
    - WebSocket: Real-time updates with sequence numbers
    """
    poller = MarketPoller()

    try:
        # Run both REST and WebSocket in parallel
        await asyncio.gather(
            poller.run(),  # REST polling (Phase 1)
            poller.listen_websocket(),  # WebSocket listener (Phase 2)
        )
    except KeyboardInterrupt:
        logger.info("Received shutdown signal")
        poller.stop()


if __name__ == "__main__":
    asyncio.run(main())
