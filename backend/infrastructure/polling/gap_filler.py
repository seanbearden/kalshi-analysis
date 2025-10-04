"""Gap backfill module for recovering missing WebSocket data.

Phase 2: When sequence gaps are detected, use REST API to backfill missing snapshots.
"""

import asyncio
import logging

from domain.models import DataSource
from domain.repositories import MarketRepository
from infrastructure.database.session import get_session_maker

logger = logging.getLogger(__name__)


class GapFiller:
    """Backfills missing WebSocket data using REST API.

    Detects sequence gaps and attempts to recover missing snapshots
    from Kalshi REST API when possible.
    """

    def __init__(self) -> None:
        """Initialize gap filler."""
        self.session_maker = get_session_maker()

    async def check_and_fill_gaps(self, ticker: str) -> int:
        """Check for gaps and attempt backfill.

        Args:
            ticker: Market ticker to check

        Returns:
            Number of gaps filled
        """
        async with self.session_maker() as session:
            repo = MarketRepository(session)

            # Detect gaps
            gaps = await repo.detect_gaps(ticker)

            if not gaps:
                logger.debug(f"No gaps detected for {ticker}")
                return 0

            logger.info(f"Detected {len(gaps)} gaps for {ticker}: {gaps[:10]}...")

            # Attempt backfill (limited to recent gaps to avoid overload)
            max_backfill = 100
            gaps_to_fill = gaps[:max_backfill]

            # Note: Kalshi API may not support fetching by sequence
            # This is a placeholder for the backfill logic
            # In practice, we may need to use timestamp-based queries

            # For now, we'll use REST polling data as backfill
            # which doesn't have sequence numbers
            for gap_seq in gaps_to_fill:
                logger.debug(
                    f"Gap {gap_seq} cannot be backfilled (sequence-based fetch not supported)"
                )

            await session.commit()

            return 0  # No gaps filled (backfill not yet implemented)

    async def run_periodic_check(self, interval_seconds: int = 300) -> None:
        """Periodically check all tickers for gaps.

        Args:
            interval_seconds: Check interval (default: 5 minutes)
        """
        logger.info(f"Starting periodic gap check (interval: {interval_seconds}s)")

        while True:
            try:
                await self._check_all_tickers()
            except Exception as e:
                logger.error(f"Gap check error: {e}", exc_info=True)

            await asyncio.sleep(interval_seconds)

    async def _check_all_tickers(self) -> None:
        """Check all tickers for gaps and attempt backfill."""
        async with self.session_maker() as session:
            # Get unique tickers from WebSocket data
            from sqlalchemy import distinct, select

            from domain.models import MarketSnapshot

            stmt = select(distinct(MarketSnapshot.ticker)).where(
                MarketSnapshot.source == DataSource.WEBSOCKET
            )
            result = await session.execute(stmt)
            tickers = [row[0] for row in result.all()]

            logger.info(f"Checking {len(tickers)} tickers for gaps")

            for ticker in tickers:
                try:
                    await self.check_and_fill_gaps(ticker)
                except Exception as e:
                    logger.error(f"Gap check failed for {ticker}: {e}")


async def main() -> None:
    """Gap filler entry point (optional standalone service)."""
    filler = GapFiller()
    await filler.run_periodic_check()


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )
    asyncio.run(main())
