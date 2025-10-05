"""Tests for notebook utility modules."""

import pandas as pd
import numpy as np
from utils import (
    MeanReversionStrategy,
    Backtest,
    BacktestResult,
    PerformanceMetrics,
)


class TestBacktesting:
    """Test backtesting framework."""

    def test_mean_reversion_strategy(self, mock_db_data):
        """Test mean reversion strategy signal generation."""
        strategy = MeanReversionStrategy(window=10, std_threshold=1.5)

        result_df = strategy.generate_signals(mock_db_data)

        # Check that signals column exists
        assert 'signal' in result_df.columns

        # Check that signals are valid (-1, 0, or 1)
        assert result_df['signal'].isin([-1, 0, 1]).all()

        # Check that rolling mean and std are calculated
        assert 'rolling_mean' in result_df.columns
        assert 'rolling_std' in result_df.columns

    def test_backtest_execution(self, mock_db_data):
        """Test backtest engine execution."""
        strategy = MeanReversionStrategy(window=10, std_threshold=1.5)
        backtest = Backtest(
            strategy=strategy,
            initial_capital=10000,
            position_size=0.1
        )

        result = backtest.run(mock_db_data)

        # Check result structure
        assert isinstance(result, BacktestResult)
        assert isinstance(result.trades, pd.DataFrame)
        assert isinstance(result.equity_curve, pd.Series)

        # Check equity curve
        assert len(result.equity_curve) > 0
        assert result.equity_curve.iloc[0] == 10000  # Initial capital

    def test_backtest_result_metrics(self, mock_db_data):
        """Test backtest result calculations."""
        strategy = MeanReversionStrategy(window=10, std_threshold=1.5)
        backtest = Backtest(strategy, initial_capital=10000)
        result = backtest.run(mock_db_data)

        # Check basic metrics
        assert result.initial_capital == 10000
        assert isinstance(result.final_capital, (int, float))
        assert isinstance(result.total_return_pct, (int, float))
        assert isinstance(result.total_trades, int)
        assert isinstance(result.win_rate, float)


class TestPerformanceMetrics:
    """Test performance metrics calculations."""

    def test_sharpe_ratio(self):
        """Test Sharpe ratio calculation."""
        # Positive returns should give positive Sharpe
        returns = pd.Series([0.01, 0.02, 0.01, 0.03, 0.02])
        sharpe = PerformanceMetrics.sharpe_ratio(returns)
        assert sharpe > 0

        # Zero std should return 0
        constant_returns = pd.Series([0.01] * 5)
        sharpe_zero = PerformanceMetrics.sharpe_ratio(constant_returns)
        assert sharpe_zero == 0

    def test_max_drawdown(self):
        """Test maximum drawdown calculation."""
        # Equity curve with known drawdown
        equity = pd.Series([100, 110, 105, 95, 90, 100, 110])
        max_dd, start_idx, end_idx = PerformanceMetrics.max_drawdown(equity)

        # Should detect the drawdown from 110 to 90
        assert max_dd < 0  # Drawdown is negative
        assert abs(max_dd) > 15  # At least 15% drawdown

    def test_profit_factor(self):
        """Test profit factor calculation."""
        # Sample trades
        trades = pd.DataFrame({
            'pnl': [100, -50, 150, -30, 80]
        })

        pf = PerformanceMetrics.profit_factor(trades)
        assert pf > 1  # Positive profit factor for profitable trades

    def test_calculate_all_metrics(self, mock_db_data):
        """Test comprehensive metrics calculation."""
        strategy = MeanReversionStrategy(window=10, std_threshold=1.5)
        backtest = Backtest(strategy, initial_capital=10000)
        result = backtest.run(mock_db_data)

        metrics = PerformanceMetrics.calculate_all(result)

        # Check all expected metrics exist
        required_metrics = [
            'total_trades', 'winning_trades', 'losing_trades', 'win_rate_pct',
            'total_return_pct', 'sharpe_ratio', 'sortino_ratio', 'max_drawdown_pct',
            'profit_factor', 'expectancy'
        ]

        for metric in required_metrics:
            assert metric in metrics
            assert isinstance(metrics[metric], (int, float))


class TestStrategyFramework:
    """Test strategy framework components."""

    def test_strategy_parameters(self):
        """Test strategy parameter handling."""
        strategy = MeanReversionStrategy(window=20, std_threshold=2.0)

        assert strategy.window == 20
        assert strategy.std_threshold == 2.0
        assert 'window' in strategy.params
        assert 'std_threshold' in strategy.params

    def test_position_sizing(self, mock_db_data):
        """Test different position sizes."""
        strategy = MeanReversionStrategy(window=10)

        # Small position
        small_backtest = Backtest(strategy, initial_capital=10000, position_size=0.05)
        small_result = small_backtest.run(mock_db_data)

        # Large position
        large_backtest = Backtest(strategy, initial_capital=10000, position_size=0.15)
        large_result = large_backtest.run(mock_db_data)

        # Larger positions should generally have larger P&L variance
        # (though this isn't guaranteed with all strategies)
        assert isinstance(small_result.final_capital, (int, float))
        assert isinstance(large_result.final_capital, (int, float))


class TestDataQuality:
    """Test data quality and edge cases."""

    def test_empty_dataframe(self):
        """Test handling of empty data."""
        strategy = MeanReversionStrategy()
        empty_df = pd.DataFrame(columns=['ticker', 'timestamp', 'yes_prob', 'no_prob'])

        backtest = Backtest(strategy, initial_capital=10000)
        result = backtest.run(empty_df)

        # Should handle gracefully
        assert len(result.trades) == 0
        assert result.final_capital == result.initial_capital

    def test_insufficient_data(self):
        """Test handling of insufficient data for signals."""
        strategy = MeanReversionStrategy(window=20)

        # Only 10 rows, window needs 20
        small_df = pd.DataFrame({
            'ticker': ['TEST'] * 10,
            'timestamp': pd.date_range(start='2024-01-01', periods=10, freq='5min'),
            'yes_prob': np.random.uniform(0.3, 0.7, 10),
            'no_prob': np.random.uniform(0.3, 0.7, 10),
        })

        result_df = strategy.generate_signals(small_df)

        # Should still execute without error
        assert 'signal' in result_df.columns
