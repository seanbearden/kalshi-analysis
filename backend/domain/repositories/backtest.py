"""Backtest repository with domain-specific queries."""

from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from domain.models import BacktestExecution, BacktestResult, StrategyType
from domain.repositories.base import BaseRepository


class BacktestRepository(BaseRepository[BacktestResult]):  # type: ignore[misc]
    """Repository for backtest operations."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(BacktestResult, session)

    async def get_with_executions(self, id: UUID) -> BacktestResult | None:
        """Get backtest with all trade executions eagerly loaded.

        Args:
            id: Backtest UUID

        Returns:
            Backtest with executions or None
        """
        stmt = (
            select(BacktestResult)
            .where(BacktestResult.id == id)
            .options(selectinload(BacktestResult.executions))
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_strategy(
        self, strategy: StrategyType, skip: int = 0, limit: int = 100
    ) -> list[BacktestResult]:
        """Get backtests by strategy type.

        Args:
            strategy: Strategy type
            skip: Number of records to skip
            limit: Maximum records to return

        Returns:
            Backtests for the strategy, ordered by created_at descending
        """
        stmt = (
            select(BacktestResult)
            .where(BacktestResult.strategy == strategy)
            .order_by(desc(BacktestResult.created_at))
            .offset(skip)
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def create_backtest(
        self,
        strategy: StrategyType,
        start_date: datetime,
        end_date: datetime,
        total_pnl: Decimal,
        total_trades: int,
        parameters: dict[str, Any],
        market_filter: str | None = None,
        sharpe_ratio: Decimal | None = None,
        max_drawdown: Decimal | None = None,
        win_rate: Decimal | None = None,
    ) -> BacktestResult:
        """Create backtest result with validation.

        Args:
            strategy: Strategy used
            start_date: Backtest period start
            end_date: Backtest period end
            total_pnl: Total profit/loss
            total_trades: Number of trades
            parameters: Strategy parameters
            market_filter: Market selection criteria (optional)
            sharpe_ratio: Risk-adjusted return (optional)
            max_drawdown: Maximum drawdown (optional)
            win_rate: Win rate percentage (optional)

        Returns:
            Created backtest result
        """
        return await self.create(
            strategy=strategy,
            start_date=start_date,
            end_date=end_date,
            market_filter=market_filter,
            total_pnl=total_pnl,
            sharpe_ratio=sharpe_ratio,
            max_drawdown=max_drawdown,
            win_rate=win_rate,
            total_trades=total_trades,
            parameters=parameters,
        )

    async def add_execution(
        self,
        backtest_id: UUID,
        ticker: str,
        direction: str,
        entry_time: datetime,
        entry_price: Decimal,
        exit_time: datetime,
        exit_price: Decimal,
        size: int,
        pnl: Decimal,
        reason: str | None = None,
        trade_metadata: dict[str, Any] | None = None,
    ) -> BacktestExecution:
        """Add trade execution to backtest.

        Args:
            backtest_id: Parent backtest UUID
            ticker: Market ticker
            direction: Trade direction (long/short)
            entry_time: Position entry time
            entry_price: Entry price
            exit_time: Position exit time
            exit_price: Exit price
            size: Position size
            pnl: Trade profit/loss
            reason: Entry/exit reason (optional)
            trade_metadata: Additional context (optional)

        Returns:
            Created execution
        """
        execution = BacktestExecution(
            backtest_id=backtest_id,
            ticker=ticker,
            direction=direction,
            entry_time=entry_time,
            entry_price=entry_price,
            exit_time=exit_time,
            exit_price=exit_price,
            size=size,
            pnl=pnl,
            reason=reason,
            trade_metadata=trade_metadata,
        )
        self.session.add(execution)
        await self.session.flush()
        await self.session.refresh(execution)
        return execution
