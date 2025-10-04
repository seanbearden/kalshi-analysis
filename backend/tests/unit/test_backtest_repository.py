"""Unit tests for BacktestRepository."""

from datetime import UTC, datetime
from decimal import Decimal

from domain.models.backtest import StrategyType, TradeDirection
from domain.repositories import BacktestRepository


class TestBacktestRepository:
    """Test suite for BacktestRepository."""

    async def test_create_backtest(self, backtest_repository: BacktestRepository) -> None:
        """Test creating a backtest result."""
        result = await backtest_repository.create_backtest(
            strategy=StrategyType.MOMENTUM,
            start_date=datetime(2024, 1, 1),
            end_date=datetime(2024, 3, 31),
            total_pnl=Decimal("1500.00"),
            total_trades=25,
            parameters={"threshold": 0.05},
            sharpe_ratio=Decimal("1.25"),
            max_drawdown=Decimal("-0.15"),
            win_rate=Decimal("0.60"),
        )

        assert result.id is not None
        assert result.strategy == StrategyType.MOMENTUM
        assert result.total_pnl == Decimal("1500.00")
        assert result.sharpe_ratio == Decimal("1.25")
        assert result.total_trades == 25
        assert result.parameters == {"threshold": 0.05}

    async def test_create_backtest_minimal(self, backtest_repository: BacktestRepository) -> None:
        """Test creating backtest with only required fields."""
        result = await backtest_repository.create_backtest(
            strategy=StrategyType.LONG_FAVORITE,
            start_date=datetime(2024, 1, 1),
            end_date=datetime(2024, 2, 1),
            total_pnl=Decimal("500.00"),
            total_trades=10,
            parameters={},
        )

        assert result.id is not None
        assert result.sharpe_ratio is None
        assert result.max_drawdown is None
        assert result.win_rate is None

    async def test_get_by_strategy(self, backtest_repository: BacktestRepository) -> None:
        """Test retrieving backtests by strategy type."""
        # Create backtests for different strategies
        await backtest_repository.create_backtest(
            strategy=StrategyType.MOMENTUM,
            start_date=datetime(2024, 1, 1),
            end_date=datetime(2024, 2, 1),
            total_pnl=Decimal("100.00"),
            total_trades=5,
            parameters={},
        )

        await backtest_repository.create_backtest(
            strategy=StrategyType.MOMENTUM,
            start_date=datetime(2024, 2, 1),
            end_date=datetime(2024, 3, 1),
            total_pnl=Decimal("200.00"),
            total_trades=8,
            parameters={},
        )

        await backtest_repository.create_backtest(
            strategy=StrategyType.MEAN_REVERSION,
            start_date=datetime(2024, 1, 1),
            end_date=datetime(2024, 2, 1),
            total_pnl=Decimal("150.00"),
            total_trades=6,
            parameters={},
        )

        # Query by strategy
        momentum_results = await backtest_repository.get_by_strategy(StrategyType.MOMENTUM)
        assert len(momentum_results) == 2

        mean_reversion_results = await backtest_repository.get_by_strategy(
            StrategyType.MEAN_REVERSION
        )
        assert len(mean_reversion_results) == 1

    async def test_add_execution(self, backtest_repository: BacktestRepository) -> None:
        """Test adding trade execution to backtest."""
        # Create backtest
        backtest = await backtest_repository.create_backtest(
            strategy=StrategyType.MOMENTUM,
            start_date=datetime(2024, 1, 1),
            end_date=datetime(2024, 2, 1),
            total_pnl=Decimal("500.00"),
            total_trades=1,
            parameters={},
        )

        # Add execution
        execution = await backtest_repository.add_execution(
            backtest_id=backtest.id,
            ticker="TICKER-001",
            direction=TradeDirection.LONG,
            entry_time=datetime(2024, 1, 15, 10, 0, 0, tzinfo=UTC),
            entry_price=Decimal("45.00"),
            exit_time=datetime(2024, 1, 15, 16, 0, 0, tzinfo=UTC),
            exit_price=Decimal("55.00"),
            size=10,
            pnl=Decimal("100.00"),
            reason="momentum_signal",
            trade_metadata={"signal_strength": 0.8},
        )

        assert execution.id is not None
        assert execution.backtest_id == backtest.id
        assert execution.ticker == "TICKER-001"
        assert execution.direction == TradeDirection.LONG
        assert execution.pnl == Decimal("100.00")
        assert execution.reason == "momentum_signal"
        assert execution.trade_metadata == {"signal_strength": 0.8}

    async def test_get_with_executions(self, backtest_repository: BacktestRepository) -> None:
        """Test eager loading of executions."""
        # Create backtest
        backtest = await backtest_repository.create_backtest(
            strategy=StrategyType.FADE_OVERREACTION,
            start_date=datetime(2024, 1, 1),
            end_date=datetime(2024, 2, 1),
            total_pnl=Decimal("750.00"),
            total_trades=3,
            parameters={},
        )

        # Add multiple executions
        for i in range(3):
            await backtest_repository.add_execution(
                backtest_id=backtest.id,
                ticker=f"TICKER-{i:03d}",
                direction=TradeDirection.LONG if i % 2 == 0 else TradeDirection.SHORT,
                entry_time=datetime(2024, 1, 10 + i, 10, 0, 0, tzinfo=UTC),
                entry_price=Decimal("50.00"),
                exit_time=datetime(2024, 1, 10 + i, 16, 0, 0, tzinfo=UTC),
                exit_price=Decimal("55.00"),
                size=5,
                pnl=Decimal("25.00"),
            )

        # Get with executions
        result = await backtest_repository.get_with_executions(backtest.id)

        assert result is not None
        assert len(result.executions) == 3
        assert all(exec.backtest_id == backtest.id for exec in result.executions)

    async def test_get_with_executions_not_found(
        self, backtest_repository: BacktestRepository
    ) -> None:
        """Test getting non-existent backtest with executions."""
        from uuid import uuid4

        result = await backtest_repository.get_with_executions(uuid4())
        assert result is None

    async def test_backtest_cascade_delete(self, backtest_repository: BacktestRepository) -> None:
        """Test that deleting backtest also deletes executions."""
        # Create backtest with executions
        backtest = await backtest_repository.create_backtest(
            strategy=StrategyType.MOMENTUM,
            start_date=datetime(2024, 1, 1),
            end_date=datetime(2024, 2, 1),
            total_pnl=Decimal("100.00"),
            total_trades=2,
            parameters={},
        )

        await backtest_repository.add_execution(
            backtest_id=backtest.id,
            ticker="TICKER-001",
            direction=TradeDirection.LONG,
            entry_time=datetime.now(UTC),
            entry_price=Decimal("50.00"),
            exit_time=datetime.now(UTC),
            exit_price=Decimal("55.00"),
            size=1,
            pnl=Decimal("5.00"),
        )

        # Verify execution exists
        result = await backtest_repository.get_with_executions(backtest.id)
        assert len(result.executions) == 1

        # Delete backtest
        await backtest_repository.delete(backtest.id)

        # Verify both backtest and executions are deleted
        result = await backtest_repository.get_with_executions(backtest.id)
        assert result is None

    async def test_execution_with_metadata(self, backtest_repository: BacktestRepository) -> None:
        """Test execution with complex trade metadata."""
        backtest = await backtest_repository.create_backtest(
            strategy=StrategyType.MOMENTUM,
            start_date=datetime(2024, 1, 1),
            end_date=datetime(2024, 2, 1),
            total_pnl=Decimal("100.00"),
            total_trades=1,
            parameters={},
        )

        complex_metadata = {
            "entry_signal": {"type": "breakout", "strength": 0.85, "volume_ratio": 1.5},
            "exit_signal": {"type": "take_profit", "target_hit": True},
            "market_conditions": {"volatility": "high", "trend": "bullish"},
        }

        execution = await backtest_repository.add_execution(
            backtest_id=backtest.id,
            ticker="COMPLEX-TICKER",
            direction=TradeDirection.LONG,
            entry_time=datetime.now(UTC),
            entry_price=Decimal("50.00"),
            exit_time=datetime.now(UTC),
            exit_price=Decimal("60.00"),
            size=10,
            pnl=Decimal("100.00"),
            trade_metadata=complex_metadata,
        )

        assert execution.trade_metadata == complex_metadata
        assert execution.trade_metadata["entry_signal"]["strength"] == 0.85
