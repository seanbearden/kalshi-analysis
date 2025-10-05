"""Position tracking service with P&L calculations and write-through caching."""

import logging
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from domain.models.account import PositionCache

logger = logging.getLogger(__name__)


@dataclass
class PositionState:
    """Position state with calculated P&L metrics.

    Calculates unrealized profit/loss based on position side (YES/NO),
    average entry price, and current market price.
    """

    ticker: str
    side: str  # YES or NO
    quantity: int
    avg_entry_price: int  # cents
    current_price: int  # cents
    entry_time: datetime

    @property
    def unrealized_pnl(self) -> int:
        """Calculate unrealized P&L in cents.

        For YES positions: (current_price - avg_entry_price) * quantity
        For NO positions: (avg_entry_price - current_price) * quantity

        Returns:
            Unrealized profit/loss in cents
        """
        if self.side == "YES":
            return (self.current_price - self.avg_entry_price) * self.quantity
        else:  # NO position
            return (self.avg_entry_price - self.current_price) * self.quantity

    @property
    def unrealized_pnl_pct(self) -> Decimal:
        """Calculate unrealized P&L as percentage.

        Returns:
            P&L percentage with 4 decimal places
        """
        if self.avg_entry_price == 0:
            return Decimal("0.0000")

        pnl_pct = (self.unrealized_pnl / (self.avg_entry_price * self.quantity)) * 100
        return Decimal(str(pnl_pct)).quantize(Decimal("0.0001"))

    @property
    def position_value(self) -> int:
        """Calculate current position value in cents.

        Returns:
            Position value based on current price and quantity
        """
        if self.side == "YES":
            return self.current_price * self.quantity
        else:  # NO position
            return (100 - self.current_price) * self.quantity

    @property
    def cost_basis(self) -> int:
        """Calculate cost basis (total amount paid) in cents.

        Returns:
            Cost basis for the position
        """
        if self.side == "YES":
            return self.avg_entry_price * self.quantity
        else:  # NO position
            return (100 - self.avg_entry_price) * self.quantity


class PositionTracker:
    """Track positions with write-through caching to database.

    Maintains in-memory position state with automatic persistence to
    position_cache table for resilience and offline mode support.
    """

    def __init__(self, session: AsyncSession, user_id: str):
        """Initialize position tracker.

        Args:
            session: Async database session
            user_id: User identifier for position ownership
        """
        self.session = session
        self.user_id = user_id
        self._positions: dict[str, PositionState] = {}

    async def load_positions(self) -> None:
        """Load positions from database cache into memory."""
        stmt = select(PositionCache).where(PositionCache.user_id == self.user_id)
        result = await self.session.execute(stmt)
        cached_positions = result.scalars().all()

        self._positions.clear()
        for cached in cached_positions:
            position = PositionState(
                ticker=cached.ticker,
                side=cached.side,
                quantity=cached.quantity,
                avg_entry_price=cached.avg_entry_price,
                current_price=cached.current_price,
                entry_time=cached.entry_time,
            )
            self._positions[cached.ticker] = position

        logger.info(f"Loaded {len(self._positions)} positions for user {self.user_id}")

    async def update_position(
        self,
        ticker: str,
        side: str,
        quantity: int,
        avg_entry_price: int,
        current_price: int,
        entry_time: datetime | None = None,
    ) -> PositionState:
        """Update or create position with write-through to database.

        Args:
            ticker: Market ticker
            side: Position side (YES or NO)
            quantity: Number of contracts
            avg_entry_price: Average entry price in cents
            current_price: Current market price in cents
            entry_time: Position entry time (defaults to now)

        Returns:
            Updated position state

        Raises:
            ValueError: If side is not YES or NO
        """
        if side not in ("YES", "NO"):
            raise ValueError(f"Invalid side: {side}. Must be YES or NO")

        if entry_time is None:
            entry_time = datetime.now(UTC)

        # Update in-memory state
        position = PositionState(
            ticker=ticker,
            side=side,
            quantity=quantity,
            avg_entry_price=avg_entry_price,
            current_price=current_price,
            entry_time=entry_time,
        )
        self._positions[ticker] = position

        # Write through to database
        stmt = select(PositionCache).where(
            PositionCache.user_id == self.user_id, PositionCache.ticker == ticker
        )
        result = await self.session.execute(stmt)
        cached = result.scalar_one_or_none()

        if cached:
            # Update existing
            cached.side = side
            cached.quantity = quantity
            cached.avg_entry_price = avg_entry_price
            cached.current_price = current_price
            cached.entry_time = entry_time
            cached.cached_at = datetime.now(UTC)
        else:
            # Insert new
            cached = PositionCache(
                user_id=self.user_id,
                ticker=ticker,
                side=side,
                quantity=quantity,
                avg_entry_price=avg_entry_price,
                current_price=current_price,
                entry_time=entry_time,
            )
            self.session.add(cached)

        await self.session.commit()
        logger.debug(f"Updated position for {ticker}: {quantity} {side} @ {avg_entry_price}")

        return position

    async def update_price(self, ticker: str, current_price: int) -> PositionState | None:
        """Update current price for existing position.

        Args:
            ticker: Market ticker
            current_price: New current price in cents

        Returns:
            Updated position state or None if position doesn't exist

        Raises:
            ValueError: If position doesn't exist for ticker
        """
        if ticker not in self._positions:
            raise ValueError(f"No position found for ticker: {ticker}")

        position = self._positions[ticker]
        position.current_price = current_price

        # Update database
        stmt = select(PositionCache).where(
            PositionCache.user_id == self.user_id, PositionCache.ticker == ticker
        )
        result = await self.session.execute(stmt)
        cached = result.scalar_one_or_none()

        if cached:
            cached.current_price = current_price
            cached.cached_at = datetime.now(UTC)
            await self.session.commit()

        return position

    async def remove_position(self, ticker: str) -> None:
        """Remove position from tracking.

        Args:
            ticker: Market ticker to remove
        """
        # Remove from memory
        self._positions.pop(ticker, None)

        # Remove from database
        stmt = delete(PositionCache).where(
            PositionCache.user_id == self.user_id, PositionCache.ticker == ticker
        )
        await self.session.execute(stmt)
        await self.session.commit()

        logger.debug(f"Removed position for {ticker}")

    async def get_position(self, ticker: str) -> PositionState | None:
        """Get position state for ticker.

        Args:
            ticker: Market ticker

        Returns:
            Position state or None if not found
        """
        return self._positions.get(ticker)

    async def get_all_positions(self) -> list[PositionState]:
        """Get all tracked positions.

        Returns:
            List of all position states
        """
        return list(self._positions.values())

    async def get_total_unrealized_pnl(self) -> int:
        """Calculate total unrealized P&L across all positions.

        Returns:
            Total unrealized P&L in cents
        """
        return sum(pos.unrealized_pnl for pos in self._positions.values())

    async def clear_all_positions(self) -> None:
        """Clear all positions (for logout or reset).

        Removes all positions from memory and database.
        """
        self._positions.clear()

        stmt = delete(PositionCache).where(PositionCache.user_id == self.user_id)
        await self.session.execute(stmt)
        await self.session.commit()

        logger.info(f"Cleared all positions for user {self.user_id}")
