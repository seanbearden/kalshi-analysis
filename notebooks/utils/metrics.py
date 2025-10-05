"""Performance metrics calculation for trading strategies."""

import pandas as pd
import numpy as np
from typing import Dict, Any
from .backtesting import BacktestResult


class PerformanceMetrics:
    """Calculate comprehensive performance metrics for backtest results."""

    @staticmethod
    def calculate_all(result: BacktestResult, risk_free_rate: float = 0.0) -> Dict[str, Any]:
        """Calculate all performance metrics.

        Args:
            result: BacktestResult from backtest
            risk_free_rate: Annual risk-free rate (default 0%)

        Returns:
            Dictionary of performance metrics
        """
        if len(result.trades) == 0:
            return PerformanceMetrics._empty_metrics()

        # Calculate individual metrics
        returns = result.trades['pnl'] / result.initial_capital

        metrics = {
            # Basic metrics
            'total_trades': result.total_trades,
            'winning_trades': result.winning_trades,
            'losing_trades': result.losing_trades,
            'win_rate_pct': result.win_rate,

            # Returns
            'total_return_pct': result.total_return_pct,
            'avg_return_pct': returns.mean() * 100,
            'std_return_pct': returns.std() * 100,

            # Risk-adjusted returns
            'sharpe_ratio': PerformanceMetrics.sharpe_ratio(returns, risk_free_rate),
            'sortino_ratio': PerformanceMetrics.sortino_ratio(returns, risk_free_rate),
            'calmar_ratio': PerformanceMetrics.calmar_ratio(
                result.total_return_pct / 100,
                PerformanceMetrics.max_drawdown(result.equity_curve)[0] / 100
            ),

            # Drawdown
            'max_drawdown_pct': PerformanceMetrics.max_drawdown(result.equity_curve)[0],
            'avg_drawdown_pct': PerformanceMetrics.avg_drawdown(result.equity_curve),

            # Trade statistics
            'avg_win_pct': result.trades[result.trades['pnl'] > 0]['pnl_pct'].mean() if result.winning_trades > 0 else 0,
            'avg_loss_pct': result.trades[result.trades['pnl'] < 0]['pnl_pct'].mean() if result.losing_trades > 0 else 0,
            'largest_win_pct': result.trades['pnl_pct'].max() if len(result.trades) > 0 else 0,
            'largest_loss_pct': result.trades['pnl_pct'].min() if len(result.trades) > 0 else 0,

            # Profit metrics
            'profit_factor': PerformanceMetrics.profit_factor(result.trades),
            'expectancy': PerformanceMetrics.expectancy(result.trades),

            # Recovery
            'recovery_factor': PerformanceMetrics.recovery_factor(
                result.total_return_pct / 100,
                PerformanceMetrics.max_drawdown(result.equity_curve)[0] / 100
            ),
        }

        # Update result object
        result.sharpe_ratio = metrics['sharpe_ratio']
        result.sortino_ratio = metrics['sortino_ratio']
        result.max_drawdown_pct = metrics['max_drawdown_pct']
        result.profit_factor = metrics['profit_factor']

        return metrics

    @staticmethod
    def sharpe_ratio(returns: pd.Series, risk_free_rate: float = 0.0) -> float:
        """Calculate annualized Sharpe ratio.

        Args:
            returns: Series of returns
            risk_free_rate: Annual risk-free rate

        Returns:
            Sharpe ratio
        """
        if returns.std() == 0:
            return 0.0

        excess_returns = returns - risk_free_rate / 252  # Daily risk-free rate
        return np.sqrt(252) * excess_returns.mean() / returns.std()

    @staticmethod
    def sortino_ratio(returns: pd.Series, risk_free_rate: float = 0.0, target_return: float = 0.0) -> float:
        """Calculate annualized Sortino ratio (uses downside deviation).

        Args:
            returns: Series of returns
            risk_free_rate: Annual risk-free rate
            target_return: Target return threshold

        Returns:
            Sortino ratio
        """
        excess_returns = returns - risk_free_rate / 252
        downside_returns = returns[returns < target_return]

        if len(downside_returns) == 0 or downside_returns.std() == 0:
            return 0.0

        downside_deviation = np.sqrt((downside_returns ** 2).mean())
        return np.sqrt(252) * excess_returns.mean() / downside_deviation

    @staticmethod
    def calmar_ratio(total_return: float, max_drawdown: float) -> float:
        """Calculate Calmar ratio (return / max drawdown).

        Args:
            total_return: Total return (as decimal, e.g., 0.15 for 15%)
            max_drawdown: Maximum drawdown (as positive decimal)

        Returns:
            Calmar ratio
        """
        if max_drawdown == 0:
            return 0.0
        return total_return / abs(max_drawdown)

    @staticmethod
    def max_drawdown(equity_curve: pd.Series) -> tuple[float, int, int]:
        """Calculate maximum drawdown.

        Args:
            equity_curve: Series of equity values

        Returns:
            Tuple of (max_drawdown_pct, start_idx, end_idx)
        """
        # Handle empty or single-point equity curve
        if len(equity_curve) == 0:
            return 0.0, 0, 0
        if len(equity_curve) == 1:
            return 0.0, 0, 0

        cumulative_max = equity_curve.expanding().max()
        drawdown = (equity_curve - cumulative_max) / cumulative_max * 100

        max_dd = drawdown.min()
        end_idx = drawdown.idxmin()

        # Find start of drawdown (last peak before max drawdown)
        # Handle edge case where end_idx is at the beginning
        if end_idx == equity_curve.index[0]:
            start_idx = end_idx
        else:
            peaks = equity_curve[:end_idx] == cumulative_max[:end_idx]
            if peaks.any():
                start_idx = peaks.iloc[::-1].idxmax()
            else:
                start_idx = equity_curve.index[0]

        return max_dd, start_idx, end_idx

    @staticmethod
    def avg_drawdown(equity_curve: pd.Series) -> float:
        """Calculate average drawdown.

        Args:
            equity_curve: Series of equity values

        Returns:
            Average drawdown percentage
        """
        cumulative_max = equity_curve.expanding().max()
        drawdown = (equity_curve - cumulative_max) / cumulative_max * 100

        # Only consider drawdown periods (negative values)
        drawdowns = drawdown[drawdown < 0]
        return drawdowns.mean() if len(drawdowns) > 0 else 0.0

    @staticmethod
    def profit_factor(trades: pd.DataFrame) -> float:
        """Calculate profit factor (gross profit / gross loss).

        Args:
            trades: DataFrame with 'pnl' column

        Returns:
            Profit factor
        """
        if len(trades) == 0:
            return 0.0

        gross_profit = trades[trades['pnl'] > 0]['pnl'].sum()
        gross_loss = abs(trades[trades['pnl'] < 0]['pnl'].sum())

        if gross_loss == 0:
            return float('inf') if gross_profit > 0 else 0.0

        return gross_profit / gross_loss

    @staticmethod
    def expectancy(trades: pd.DataFrame) -> float:
        """Calculate expectancy (average P&L per trade).

        Args:
            trades: DataFrame with 'pnl' column

        Returns:
            Expected value per trade
        """
        if len(trades) == 0:
            return 0.0

        return trades['pnl'].mean()

    @staticmethod
    def recovery_factor(total_return: float, max_drawdown: float) -> float:
        """Calculate recovery factor (net profit / max drawdown).

        Args:
            total_return: Total return (as decimal)
            max_drawdown: Maximum drawdown (as positive decimal)

        Returns:
            Recovery factor
        """
        if max_drawdown == 0:
            return 0.0
        return total_return / abs(max_drawdown)

    @staticmethod
    def _empty_metrics() -> Dict[str, Any]:
        """Return empty metrics dictionary when no trades."""
        return {
            'total_trades': 0,
            'winning_trades': 0,
            'losing_trades': 0,
            'win_rate_pct': 0.0,
            'total_return_pct': 0.0,
            'avg_return_pct': 0.0,
            'std_return_pct': 0.0,
            'sharpe_ratio': 0.0,
            'sortino_ratio': 0.0,
            'calmar_ratio': 0.0,
            'max_drawdown_pct': 0.0,
            'avg_drawdown_pct': 0.0,
            'avg_win_pct': 0.0,
            'avg_loss_pct': 0.0,
            'largest_win_pct': 0.0,
            'largest_loss_pct': 0.0,
            'profit_factor': 0.0,
            'expectancy': 0.0,
            'recovery_factor': 0.0,
        }

    @staticmethod
    def print_metrics(metrics: Dict[str, Any], title: str = "Performance Metrics") -> None:
        """Print metrics in formatted table.

        Args:
            metrics: Dictionary of metrics
            title: Title for metrics display
        """
        print("\n" + "=" * 60)
        print(f"{title:^60}")
        print("=" * 60)

        # Group metrics
        basic = [
            ('Total Trades', metrics['total_trades'], ''),
            ('Winning Trades', metrics['winning_trades'], ''),
            ('Losing Trades', metrics['losing_trades'], ''),
            ('Win Rate', metrics['win_rate_pct'], '%'),
        ]

        returns = [
            ('Total Return', metrics['total_return_pct'], '%'),
            ('Avg Return/Trade', metrics['avg_return_pct'], '%'),
            ('Std Dev Returns', metrics['std_return_pct'], '%'),
        ]

        risk_adjusted = [
            ('Sharpe Ratio', metrics['sharpe_ratio'], ''),
            ('Sortino Ratio', metrics['sortino_ratio'], ''),
            ('Calmar Ratio', metrics['calmar_ratio'], ''),
        ]

        drawdown = [
            ('Max Drawdown', metrics['max_drawdown_pct'], '%'),
            ('Avg Drawdown', metrics['avg_drawdown_pct'], '%'),
        ]

        profit = [
            ('Profit Factor', metrics['profit_factor'], ''),
            ('Expectancy/Trade', metrics['expectancy'], '$'),
            ('Recovery Factor', metrics['recovery_factor'], ''),
        ]

        for section, items in [
            ("Basic Statistics", basic),
            ("Returns", returns),
            ("Risk-Adjusted", risk_adjusted),
            ("Drawdown", drawdown),
            ("Profit Metrics", profit),
        ]:
            print(f"\n{section}:")
            print("-" * 60)
            for label, value, unit in items:
                if isinstance(value, int):
                    print(f"  {label:.<45} {value:>10}{unit}")
                else:
                    print(f"  {label:.<45} {value:>10.2f}{unit}")

        print("\n" + "=" * 60)
        sharpe = metrics['sharpe_ratio']
        status = "✅ ACHIEVED" if sharpe > 0.5 else "❌ NOT MET"
        print(f"PHASE 1 SUCCESS CRITERIA: {status}")
        print(f"Sharpe Ratio: {sharpe:.3f} (Target: >0.5)")
        print("=" * 60 + "\n")
