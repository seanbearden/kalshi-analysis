"""Visualization utilities for trading strategy analysis."""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from typing import Optional, Tuple
from .backtesting import BacktestResult


# Set default plotting style
sns.set_style('darkgrid')
plt.rcParams['figure.figsize'] = (12, 6)


def plot_equity_curve(
    result: BacktestResult,
    title: str = "Equity Curve",
    figsize: Tuple[int, int] = (14, 7)
) -> plt.Figure:
    """Plot equity curve from backtest results.

    Args:
        result: BacktestResult with equity_curve
        title: Plot title
        figsize: Figure size (width, height)

    Returns:
        Matplotlib figure
    """
    fig, ax = plt.subplots(figsize=figsize)

    ax.plot(result.equity_curve.index, result.equity_curve.values, linewidth=2, label='Equity')
    ax.axhline(y=result.initial_capital, color='r', linestyle='--', alpha=0.5, label='Initial Capital')

    ax.set_xlabel('Trade Number')
    ax.set_ylabel('Equity ($)')
    ax.set_title(title)
    ax.legend()
    ax.grid(True, alpha=0.3)

    return fig


def plot_returns_distribution(
    result: BacktestResult,
    figsize: Tuple[int, int] = (16, 6)
) -> plt.Figure:
    """Plot distribution of returns.

    Args:
        result: BacktestResult with trades
        figsize: Figure size (width, height)

    Returns:
        Matplotlib figure
    """
    if len(result.trades) == 0:
        fig, ax = plt.subplots(figsize=figsize)
        ax.text(0.5, 0.5, 'No trades to display', ha='center', va='center')
        return fig

    fig, axes = plt.subplots(1, 2, figsize=figsize)

    # P&L distribution
    axes[0].hist(result.trades['pnl'], bins=30, edgecolor='black', alpha=0.7)
    axes[0].axvline(x=0, color='r', linestyle='--', linewidth=2)
    axes[0].set_xlabel('P&L ($)')
    axes[0].set_ylabel('Frequency')
    axes[0].set_title('P&L Distribution')
    axes[0].grid(True, alpha=0.3)

    # Returns distribution
    axes[1].hist(result.trades['pnl_pct'], bins=30, edgecolor='black', alpha=0.7, color='green')
    axes[1].axvline(x=0, color='r', linestyle='--', linewidth=2)
    axes[1].set_xlabel('Return (%)')
    axes[1].set_ylabel('Frequency')
    axes[1].set_title('Returns Distribution')
    axes[1].grid(True, alpha=0.3)

    plt.tight_layout()
    return fig


def plot_cumulative_returns(
    result: BacktestResult,
    figsize: Tuple[int, int] = (14, 7)
) -> plt.Figure:
    """Plot cumulative returns over time.

    Args:
        result: BacktestResult with trades
        figsize: Figure size (width, height)

    Returns:
        Matplotlib figure
    """
    if len(result.trades) == 0:
        fig, ax = plt.subplots(figsize=figsize)
        ax.text(0.5, 0.5, 'No trades to display', ha='center', va='center')
        return fig

    fig, ax = plt.subplots(figsize=figsize)

    cumulative_return = (result.trades['pnl'].cumsum() / result.initial_capital * 100)
    ax.plot(cumulative_return.index, cumulative_return.values, linewidth=2, color='purple')
    ax.axhline(y=0, color='r', linestyle='--', alpha=0.5)

    ax.set_xlabel('Trade Number')
    ax.set_ylabel('Cumulative Return (%)')
    ax.set_title('Cumulative Return Over Time')
    ax.grid(True, alpha=0.3)

    return fig


def plot_drawdown(
    result: BacktestResult,
    figsize: Tuple[int, int] = (14, 7)
) -> plt.Figure:
    """Plot drawdown over time.

    Args:
        result: BacktestResult with equity_curve
        figsize: Figure size (width, height)

    Returns:
        Matplotlib figure
    """
    fig, ax = plt.subplots(figsize=figsize)

    # Calculate drawdown
    cumulative_max = result.equity_curve.expanding().max()
    drawdown = (result.equity_curve - cumulative_max) / cumulative_max * 100

    ax.fill_between(drawdown.index, 0, drawdown.values, alpha=0.3, color='red')
    ax.plot(drawdown.index, drawdown.values, linewidth=1, color='darkred')

    ax.set_xlabel('Trade Number')
    ax.set_ylabel('Drawdown (%)')
    ax.set_title('Drawdown Over Time')
    ax.grid(True, alpha=0.3)

    return fig


def plot_reliability_diagram(
    predicted_probs: pd.Series,
    actual_outcomes: pd.Series,
    n_bins: int = 10,
    figsize: Tuple[int, int] = (10, 10)
) -> plt.Figure:
    """Plot reliability diagram (calibration plot).

    This is a CRITICAL visualization for Phase 1C success criteria.
    It shows how well predicted probabilities match actual outcomes.

    Perfect calibration = diagonal line
    Above diagonal = underconfident (predicted < actual)
    Below diagonal = overconfident (predicted > actual)

    Args:
        predicted_probs: Predicted probabilities (0-1)
        actual_outcomes: Actual binary outcomes (0 or 1)
        n_bins: Number of bins for grouping
        figsize: Figure size (width, height)

    Returns:
        Matplotlib figure
    """
    fig, ax = plt.subplots(figsize=figsize)

    # Create bins and calculate calibration
    bins = np.linspace(0, 1, n_bins + 1)
    bin_centers = (bins[:-1] + bins[1:]) / 2

    predicted_freq = []
    actual_freq = []
    counts = []

    for i in range(n_bins):
        mask = (predicted_probs >= bins[i]) & (predicted_probs < bins[i + 1])
        if i == n_bins - 1:  # Include 1.0 in last bin
            mask = mask | (predicted_probs == bins[i + 1])

        count = mask.sum()
        counts.append(count)

        if count > 0:
            predicted_freq.append(predicted_probs[mask].mean())
            actual_freq.append(actual_outcomes[mask].mean())
        else:
            predicted_freq.append(bin_centers[i])
            actual_freq.append(bin_centers[i])

    # Plot perfect calibration line
    ax.plot([0, 1], [0, 1], 'k--', label='Perfect Calibration', linewidth=2)

    # Plot actual calibration
    ax.plot(predicted_freq, actual_freq, 'o-', linewidth=2, markersize=8, label='Actual Calibration')

    # Add confidence bars based on sample size
    for i, (pred, actual, count) in enumerate(zip(predicted_freq, actual_freq, counts)):
        if count > 0:
            # Wilson score interval for binomial proportion
            z = 1.96  # 95% confidence
            p_hat = actual
            n = count
            denominator = 1 + z**2 / n
            margin = z * np.sqrt(p_hat * (1 - p_hat) / n + z**2 / (4 * n**2)) / denominator

            ax.errorbar(pred, actual, yerr=margin, fmt='none', ecolor='gray', alpha=0.5, capsize=5)

    # Annotations
    ax.set_xlabel('Predicted Probability', fontsize=12)
    ax.set_ylabel('Actual Frequency', fontsize=12)
    ax.set_title('Reliability Diagram (Calibration Plot)', fontsize=14, fontweight='bold')
    ax.legend(fontsize=11)
    ax.grid(True, alpha=0.3)
    ax.set_xlim([-0.05, 1.05])
    ax.set_ylim([-0.05, 1.05])

    # Add statistics box
    mse = np.mean((np.array(predicted_freq) - np.array(actual_freq)) ** 2)
    textstr = f'Calibration MSE: {mse:.4f}\nTotal Predictions: {len(predicted_probs)}'
    props = dict(boxstyle='round', facecolor='wheat', alpha=0.5)
    ax.text(0.05, 0.95, textstr, transform=ax.transAxes, fontsize=10,
            verticalalignment='top', bbox=props)

    plt.tight_layout()
    return fig


def plot_strategy_summary(
    result: BacktestResult,
    figsize: Tuple[int, int] = (18, 12)
) -> plt.Figure:
    """Plot comprehensive strategy summary with multiple panels.

    Args:
        result: BacktestResult with all data
        figsize: Figure size (width, height)

    Returns:
        Matplotlib figure
    """
    if len(result.trades) == 0:
        fig, ax = plt.subplots(figsize=figsize)
        ax.text(0.5, 0.5, 'No trades to display', ha='center', va='center', fontsize=16)
        return fig

    fig = plt.figure(figsize=figsize)
    gs = fig.add_gridspec(3, 2, hspace=0.3, wspace=0.3)

    # 1. Equity Curve
    ax1 = fig.add_subplot(gs[0, :])
    ax1.plot(result.equity_curve.index, result.equity_curve.values, linewidth=2)
    ax1.axhline(y=result.initial_capital, color='r', linestyle='--', alpha=0.5, label='Initial Capital')
    ax1.set_xlabel('Trade Number')
    ax1.set_ylabel('Equity ($)')
    ax1.set_title('Equity Curve', fontweight='bold')
    ax1.legend()
    ax1.grid(True, alpha=0.3)

    # 2. Cumulative Returns
    ax2 = fig.add_subplot(gs[1, 0])
    cumulative_return = (result.trades['pnl'].cumsum() / result.initial_capital * 100)
    ax2.plot(cumulative_return.index, cumulative_return.values, linewidth=2, color='green')
    ax2.axhline(y=0, color='r', linestyle='--', alpha=0.5)
    ax2.set_xlabel('Trade Number')
    ax2.set_ylabel('Cumulative Return (%)')
    ax2.set_title('Cumulative Return', fontweight='bold')
    ax2.grid(True, alpha=0.3)

    # 3. Drawdown
    ax3 = fig.add_subplot(gs[1, 1])
    cumulative_max = result.equity_curve.expanding().max()
    drawdown = (result.equity_curve - cumulative_max) / cumulative_max * 100
    ax3.fill_between(drawdown.index, 0, drawdown.values, alpha=0.3, color='red')
    ax3.plot(drawdown.index, drawdown.values, linewidth=1, color='darkred')
    ax3.set_xlabel('Trade Number')
    ax3.set_ylabel('Drawdown (%)')
    ax3.set_title('Drawdown', fontweight='bold')
    ax3.grid(True, alpha=0.3)

    # 4. P&L Distribution
    ax4 = fig.add_subplot(gs[2, 0])
    ax4.hist(result.trades['pnl'], bins=30, edgecolor='black', alpha=0.7)
    ax4.axvline(x=0, color='r', linestyle='--', linewidth=2)
    ax4.set_xlabel('P&L ($)')
    ax4.set_ylabel('Frequency')
    ax4.set_title('P&L Distribution', fontweight='bold')
    ax4.grid(True, alpha=0.3)

    # 5. Returns Distribution
    ax5 = fig.add_subplot(gs[2, 1])
    ax5.hist(result.trades['pnl_pct'], bins=30, edgecolor='black', alpha=0.7, color='purple')
    ax5.axvline(x=0, color='r', linestyle='--', linewidth=2)
    ax5.set_xlabel('Return (%)')
    ax5.set_ylabel('Frequency')
    ax5.set_title('Returns Distribution', fontweight='bold')
    ax5.grid(True, alpha=0.3)

    return fig


def plot_price_history_with_signals(
    df: pd.DataFrame,
    ticker: Optional[str] = None,
    figsize: Tuple[int, int] = (16, 8)
) -> plt.Figure:
    """Plot price history with buy/sell signals.

    Args:
        df: DataFrame with columns: timestamp, yes_prob, signal
        ticker: Ticker name for title
        figsize: Figure size (width, height)

    Returns:
        Matplotlib figure
    """
    fig, ax = plt.subplots(figsize=figsize)

    # Plot price
    ax.plot(df['timestamp'], df['yes_prob'], label='Yes Price', linewidth=2, alpha=0.7)

    # Plot signals
    buy_signals = df[df['signal'] == 1]
    sell_signals = df[df['signal'] == -1]

    ax.scatter(buy_signals['timestamp'], buy_signals['yes_prob'],
               marker='^', color='green', s=100, label='Buy Signal', zorder=5)
    ax.scatter(sell_signals['timestamp'], sell_signals['yes_prob'],
               marker='v', color='red', s=100, label='Sell Signal', zorder=5)

    # Add bands if present
    if 'rolling_mean' in df.columns:
        ax.plot(df['timestamp'], df['rolling_mean'], '--', label='Mean', alpha=0.5)
    if 'lower_band' in df.columns and 'upper_band' in df.columns:
        ax.fill_between(df['timestamp'], df['lower_band'], df['upper_band'],
                        alpha=0.2, label='Signal Bands')

    title = f'Price History with Signals: {ticker}' if ticker else 'Price History with Signals'
    ax.set_xlabel('Time')
    ax.set_ylabel('Probability')
    ax.set_title(title, fontweight='bold')
    ax.legend()
    ax.grid(True, alpha=0.3)
    plt.xticks(rotation=45)
    plt.tight_layout()

    return fig
