"""Backtest domain models."""

from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import JSON, ForeignKey, Index, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from infrastructure.database.base import Base


class StrategyType(str, Enum):
    """Supported trading strategies."""

    LONG_FAVORITE = "long_favorite"
    FADE_OVERREACTION = "fade_overreaction"
    MEAN_REVERSION = "mean_reversion"
    MOMENTUM = "momentum"


class TradeDirection(str, Enum):
    """Trade direction."""

    LONG = "long"  # Buy YES
    SHORT = "short"  # Buy NO


class BacktestResult(Base):
    """Backtest run results and metadata.

    Stores aggregate metrics for a complete backtest run.

    Attributes:
        id: Unique backtest identifier
        strategy: Strategy used
        start_date: Backtest period start
        end_date: Backtest period end
        market_filter: Market selection criteria
        total_pnl: Total profit/loss
        sharpe_ratio: Risk-adjusted return metric
        max_drawdown: Maximum peak-to-trough decline
        win_rate: Percentage of winning trades
        total_trades: Number of trades executed
        parameters: Strategy-specific parameters
        created_at: When backtest was run
        executions: Individual trade executions
    """

    __tablename__ = "backtest_results"

    # Primary key
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)

    # Backtest configuration
    strategy: Mapped[StrategyType] = mapped_column(index=True, nullable=False)
    start_date: Mapped[datetime] = mapped_column(nullable=False)
    end_date: Mapped[datetime] = mapped_column(nullable=False)
    market_filter: Mapped[str] = mapped_column(String(100), nullable=True)

    # Aggregate metrics
    total_pnl: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    sharpe_ratio: Mapped[Decimal] = mapped_column(Numeric(6, 3), nullable=True)
    max_drawdown: Mapped[Decimal] = mapped_column(Numeric(6, 3), nullable=True)
    win_rate: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=True)
    total_trades: Mapped[int] = mapped_column(nullable=False)

    # Strategy parameters (JSON for flexibility)
    parameters: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)

    # Metadata
    created_at: Mapped[datetime] = mapped_column(
        default=datetime.utcnow, nullable=False, index=True
    )

    # Relationships
    executions: Mapped[list["BacktestExecution"]] = relationship(
        back_populates="backtest", cascade="all, delete-orphan"
    )

    __table_args__ = (Index("ix_strategy_created", "strategy", "created_at"),)

    def __repr__(self) -> str:
        return (
            f"<BacktestResult(strategy={self.strategy.value}, "
            f"pnl={self.total_pnl}, trades={self.total_trades})>"
        )


class BacktestExecution(Base):
    """Individual trade execution within a backtest.

    Provides trade-level audit trail for analysis and debugging.

    Attributes:
        id: Unique execution identifier
        backtest_id: Parent backtest run
        ticker: Market ticker traded
        direction: Long (YES) or Short (NO)
        entry_time: When position was opened
        entry_price: Price paid at entry
        exit_time: When position was closed
        exit_price: Price received at exit
        size: Position size (contracts)
        pnl: Trade profit/loss
        reason: Entry/exit reason (e.g., "signal_threshold", "stop_loss")
        trade_metadata: Additional trade context
    """

    __tablename__ = "backtest_executions"

    # Primary key
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)

    # Foreign key
    backtest_id: Mapped[UUID] = mapped_column(
        ForeignKey("backtest_results.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )

    # Trade details
    ticker: Mapped[str] = mapped_column(String(50), index=True, nullable=False)
    direction: Mapped[TradeDirection] = mapped_column(nullable=False)

    # Entry
    entry_time: Mapped[datetime] = mapped_column(nullable=False)
    entry_price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)

    # Exit
    exit_time: Mapped[datetime] = mapped_column(nullable=False)
    exit_price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)

    # Position sizing
    size: Mapped[int] = mapped_column(nullable=False)

    # Results
    pnl: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)

    # Trade context
    reason: Mapped[str] = mapped_column(Text, nullable=True)
    trade_metadata: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)

    # Relationships
    backtest: Mapped["BacktestResult"] = relationship(back_populates="executions")

    __table_args__ = (
        # Composite index for time-series queries
        Index("ix_backtest_entry_time", "backtest_id", "entry_time"),
        # Index for ticker-based analysis
        Index("ix_ticker_entry_time", "ticker", "entry_time"),
    )

    def __repr__(self) -> str:
        return (
            f"<BacktestExecution(ticker={self.ticker}, "
            f"direction={self.direction.value}, pnl={self.pnl})>"
        )
