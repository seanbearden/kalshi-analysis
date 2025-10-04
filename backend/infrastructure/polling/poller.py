"""Market data poller - runs as separate container."""

import asyncio
import logging
from datetime import datetime

from core.config import get_settings
from domain.models import DataSource
from domain.repositories import MarketRepository
from infrastructure.database.session import get_session_maker
from infrastructure.kalshi.client import KalshiClient

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


async def main() -> None:
    """Poller entry point."""
    poller = MarketPoller()

    try:
        await poller.run()
    except KeyboardInterrupt:
        logger.info("Received shutdown signal")
        poller.stop()


if __name__ == "__main__":
    asyncio.run(main())
