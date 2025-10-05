"""Kalshi Analysis Utilities

Reusable modules for data science workflows.
"""

__version__ = "0.1.0"

from .database import get_engine, load_market_data
from .backtesting import Strategy, Backtest, BacktestResult
from .metrics import PerformanceMetrics
from .visualization import plot_equity_curve, plot_returns_distribution, plot_reliability_diagram

__all__ = [
    "get_engine",
    "load_market_data",
    "Strategy",
    "Backtest",
    "BacktestResult",
    "PerformanceMetrics",
    "plot_equity_curve",
    "plot_returns_distribution",
    "plot_reliability_diagram",
]
