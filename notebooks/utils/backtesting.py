"""Backtesting framework for trading strategies."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Literal, Optional
import pandas as pd
import numpy as np


@dataclass
class Trade:
    """Individual trade record."""
    entry_time: pd.Timestamp
    exit_time: pd.Timestamp
    ticker: str
    position: Literal['LONG', 'SHORT']
    entry_price: float
    exit_price: float
    size: float
    pnl: float
    pnl_pct: float
    exit_reason: str


@dataclass
class BacktestResult:
    """Backtest execution results."""
    trades: pd.DataFrame
    equity_curve: pd.Series
    initial_capital: float
    final_capital: float
    total_return_pct: float
    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate: float

    # Additional metrics calculated by PerformanceMetrics
    sharpe_ratio: Optional[float] = None
    sortino_ratio: Optional[float] = None
    max_drawdown_pct: Optional[float] = None
    profit_factor: Optional[float] = None


class Strategy(ABC):
    """Base class for trading strategies.

    Subclasses must implement generate_signals() method.
    """

    def __init__(self, params: Optional[dict] = None):
        """Initialize strategy with optional parameters.

        Args:
            params: Strategy-specific parameters
        """
        self.params = params or {}

    @abstractmethod
    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        """Generate trading signals for market data.

        Args:
            df: Market data with columns: ticker, timestamp, yes_prob, no_prob

        Returns:
            DataFrame with additional 'signal' column:
                1 = buy signal
                -1 = sell signal
                0 = hold/no signal
        """
        pass

    def calculate_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calculate technical indicators (optional, override if needed).

        Args:
            df: Market data

        Returns:
            DataFrame with additional indicator columns
        """
        return df


class MeanReversionStrategy(Strategy):
    """Mean reversion strategy implementation.

    Buy when price deviates significantly below mean,
    sell when price deviates significantly above mean.
    """

    def __init__(
        self,
        window: int = 20,
        std_threshold: float = 1.5
    ):
        """Initialize mean reversion strategy.

        Args:
            window: Rolling window for mean/std calculation
            std_threshold: Number of standard deviations for signal
        """
        super().__init__({'window': window, 'std_threshold': std_threshold})
        self.window = window
        self.std_threshold = std_threshold

    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        """Generate mean reversion signals."""
        df = df.copy().sort_values('timestamp')

        # Calculate rolling statistics
        df['rolling_mean'] = df['yes_prob'].rolling(
            window=self.window,
            min_periods=max(5, self.window // 4)
        ).mean()

        df['rolling_std'] = df['yes_prob'].rolling(
            window=self.window,
            min_periods=max(5, self.window // 4)
        ).std()

        # Calculate bands
        df['lower_band'] = df['rolling_mean'] - self.std_threshold * df['rolling_std']
        df['upper_band'] = df['rolling_mean'] + self.std_threshold * df['rolling_std']

        # Generate signals
        df['signal'] = 0
        df.loc[df['yes_prob'] < df['lower_band'], 'signal'] = 1  # Buy undervalued
        df.loc[df['yes_prob'] > df['upper_band'], 'signal'] = -1  # Sell overvalued

        return df


class Backtest:
    """Backtesting engine for strategy evaluation."""

    def __init__(
        self,
        strategy: Strategy,
        initial_capital: float = 10000,
        position_size: float = 0.1,
        exit_neutral: bool = True,
        neutral_threshold: float = 0.02
    ):
        """Initialize backtest engine.

        Args:
            strategy: Trading strategy instance
            initial_capital: Starting capital
            position_size: Fraction of capital per trade (0-1)
            exit_neutral: Exit when price returns to neutral (0.50)
            neutral_threshold: Threshold for neutral exit
        """
        self.strategy = strategy
        self.initial_capital = initial_capital
        self.position_size = position_size
        self.exit_neutral = exit_neutral
        self.neutral_threshold = neutral_threshold

    def run(self, df: pd.DataFrame) -> BacktestResult:
        """Execute backtest on market data.

        Args:
            df: Market data with signals

        Returns:
            BacktestResult with trades and equity curve
        """
        # Handle empty dataframe
        if len(df) == 0:
            return BacktestResult(
                trades=pd.DataFrame(),
                equity_curve=pd.Series([self.initial_capital]),
                initial_capital=self.initial_capital,
                final_capital=self.initial_capital,
                total_return_pct=0.0,
                total_trades=0,
                winning_trades=0,
                losing_trades=0,
                win_rate=0.0
            )

        # Generate signals if not already present
        if 'signal' not in df.columns:
            df = self.strategy.generate_signals(df)

        df = df.copy().reset_index(drop=True)

        # Initialize state
        capital = self.initial_capital
        position = 0  # 0 = no position, 1 = long, -1 = short
        entry_price = 0
        entry_time = None
        ticker = df['ticker'].iloc[0] if 'ticker' in df.columns else 'UNKNOWN'

        trades = []
        equity = [self.initial_capital]

        # Simulate trading
        for i in range(len(df)):
            row = df.iloc[i]

            # Entry logic
            if position == 0 and row['signal'] != 0:
                position = int(row['signal'])
                entry_price = row['yes_prob']
                entry_time = row['timestamp']

            # Exit logic
            elif position != 0:
                should_exit = False
                exit_reason = ''

                # Exit at neutral
                if self.exit_neutral and abs(row['yes_prob'] - 0.5) < self.neutral_threshold:
                    should_exit = True
                    exit_reason = 'neutral'

                # Exit on opposite signal
                elif row['signal'] == -position:
                    should_exit = True
                    exit_reason = 'opposite_signal'

                if should_exit:
                    exit_price = row['yes_prob']

                    # Calculate P&L
                    if position == 1:  # Long
                        pnl_pct = (exit_price - entry_price) / entry_price if entry_price > 0 else 0
                    else:  # Short
                        pnl_pct = (entry_price - exit_price) / entry_price if entry_price > 0 else 0

                    trade_size = capital * self.position_size
                    trade_pnl = trade_size * pnl_pct
                    capital += trade_pnl

                    trades.append(Trade(
                        entry_time=entry_time,
                        exit_time=row['timestamp'],
                        ticker=ticker,
                        position='LONG' if position == 1 else 'SHORT',
                        entry_price=entry_price,
                        exit_price=exit_price,
                        size=trade_size,
                        pnl=trade_pnl,
                        pnl_pct=pnl_pct * 100,
                        exit_reason=exit_reason
                    ))

                    position = 0

            equity.append(capital)

        # Convert trades to DataFrame
        if trades:
            trades_df = pd.DataFrame([
                {
                    'entry_time': t.entry_time,
                    'exit_time': t.exit_time,
                    'ticker': t.ticker,
                    'position': t.position,
                    'entry_price': t.entry_price,
                    'exit_price': t.exit_price,
                    'size': t.size,
                    'pnl': t.pnl,
                    'pnl_pct': t.pnl_pct,
                    'exit_reason': t.exit_reason
                }
                for t in trades
            ])
        else:
            trades_df = pd.DataFrame()

        # Calculate basic metrics
        total_return_pct = (capital - self.initial_capital) / self.initial_capital * 100
        winning = trades_df[trades_df['pnl'] > 0] if len(trades_df) > 0 else pd.DataFrame()
        losing = trades_df[trades_df['pnl'] < 0] if len(trades_df) > 0 else pd.DataFrame()
        win_rate = len(winning) / len(trades_df) * 100 if len(trades_df) > 0 else 0

        return BacktestResult(
            trades=trades_df,
            equity_curve=pd.Series(equity),
            initial_capital=self.initial_capital,
            final_capital=capital,
            total_return_pct=total_return_pct,
            total_trades=len(trades_df),
            winning_trades=len(winning),
            losing_trades=len(losing),
            win_rate=win_rate
        )


def run_multi_ticker_backtest(
    df: pd.DataFrame,
    strategy: Strategy,
    initial_capital: float = 10000,
    position_size: float = 0.1
) -> BacktestResult:
    """Run backtest across multiple tickers.

    Args:
        df: Market data for multiple tickers
        strategy: Trading strategy
        initial_capital: Starting capital
        position_size: Position size per trade

    Returns:
        Aggregate BacktestResult
    """
    all_trades = []

    for ticker in df['ticker'].unique():
        ticker_df = df[df['ticker'] == ticker].copy()

        # Only backtest if enough data
        if len(ticker_df) >= 30:
            backtest = Backtest(strategy, initial_capital, position_size)
            result = backtest.run(ticker_df)

            if len(result.trades) > 0:
                result.trades['ticker'] = ticker
                all_trades.append(result.trades)

    # Combine all trades
    if all_trades:
        combined_trades = pd.concat(all_trades, ignore_index=True)

        # Calculate aggregate metrics
        total_pnl = combined_trades['pnl'].sum()
        final_capital = initial_capital + total_pnl
        total_return_pct = total_pnl / initial_capital * 100

        winning = combined_trades[combined_trades['pnl'] > 0]
        losing = combined_trades[combined_trades['pnl'] < 0]
        win_rate = len(winning) / len(combined_trades) * 100

        # Create equity curve
        combined_trades = combined_trades.sort_values('exit_time')
        cumulative_pnl = combined_trades['pnl'].cumsum()
        equity_curve = pd.Series([initial_capital] + (initial_capital + cumulative_pnl).tolist())

        return BacktestResult(
            trades=combined_trades,
            equity_curve=equity_curve,
            initial_capital=initial_capital,
            final_capital=final_capital,
            total_return_pct=total_return_pct,
            total_trades=len(combined_trades),
            winning_trades=len(winning),
            losing_trades=len(losing),
            win_rate=win_rate
        )
    else:
        # No trades
        return BacktestResult(
            trades=pd.DataFrame(),
            equity_curve=pd.Series([initial_capital]),
            initial_capital=initial_capital,
            final_capital=initial_capital,
            total_return_pct=0.0,
            total_trades=0,
            winning_trades=0,
            losing_trades=0,
            win_rate=0.0
        )
