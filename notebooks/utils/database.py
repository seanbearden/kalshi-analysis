"""Database connection and data loading utilities for Kalshi analysis."""

import pandas as pd
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from typing import Optional
from datetime import datetime


def get_engine(db_url: Optional[str] = None) -> Engine:
    """Create SQLAlchemy engine for database connection.

    Args:
        db_url: Database URL. Defaults to local PostgreSQL.

    Returns:
        SQLAlchemy engine instance
    """
    if db_url is None:
        db_url = 'postgresql://kalshi:kalshi@localhost:5432/kalshi'  # pragma: allowlist secret

    return create_engine(db_url)


def load_market_data(
    engine: Engine,
    ticker: Optional[str] = None,
    start_time: Optional[datetime] = None,
    end_time: Optional[datetime] = None,
    min_snapshots: int = 0
) -> pd.DataFrame:
    """Load market snapshot data from database.

    Args:
        engine: SQLAlchemy engine
        ticker: Optional ticker filter
        start_time: Optional start time filter
        end_time: Optional end time filter
        min_snapshots: Minimum snapshots per ticker (filters out low-data tickers)

    Returns:
        DataFrame with columns: ticker, timestamp, yes_price, no_price, volume, yes_prob, no_prob
    """
    # Build query with optional filters
    query_parts = [
        "SELECT ticker, timestamp, yes_price, no_price, volume, source",
        "FROM market_snapshots"
    ]

    where_clauses = []
    if ticker:
        where_clauses.append(f"ticker = '{ticker}'")
    if start_time:
        where_clauses.append(f"timestamp >= '{start_time}'")
    if end_time:
        where_clauses.append(f"timestamp <= '{end_time}'")

    if where_clauses:
        query_parts.append("WHERE " + " AND ".join(where_clauses))

    query_parts.append("ORDER BY ticker, timestamp")
    query = " ".join(query_parts)

    # Load data
    df = pd.read_sql(query, engine, parse_dates=['timestamp'])

    # Add probability columns (convert cents to 0-1 range)
    df['yes_prob'] = df['yes_price'] / 100
    df['no_prob'] = df['no_price'] / 100

    # Filter by minimum snapshots if requested
    if min_snapshots > 0:
        ticker_counts = df['ticker'].value_counts()
        valid_tickers = ticker_counts[ticker_counts >= min_snapshots].index
        df = df[df['ticker'].isin(valid_tickers)]

    return df


def get_ticker_summary(engine: Engine) -> pd.DataFrame:
    """Get summary statistics for all tickers.

    Args:
        engine: SQLAlchemy engine

    Returns:
        DataFrame with ticker statistics
    """
    query = """
    SELECT
        ticker,
        COUNT(*) as snapshot_count,
        MIN(timestamp) as first_snapshot,
        MAX(timestamp) as last_snapshot,
        MIN(yes_price) / 100.0 as min_yes_prob,
        MAX(yes_price) / 100.0 as max_yes_prob,
        AVG(yes_price) / 100.0 as avg_yes_prob,
        STDDEV(yes_price) / 100.0 as std_yes_prob,
        SUM(volume) as total_volume
    FROM market_snapshots
    GROUP BY ticker
    ORDER BY snapshot_count DESC
    """

    return pd.read_sql(query, engine, parse_dates=['first_snapshot', 'last_snapshot'])


def get_active_tickers(
    engine: Engine,
    min_snapshots: int = 50,
    min_price_range: float = 0.01
) -> pd.DataFrame:
    """Get tickers with sufficient data and price movement.

    Args:
        engine: SQLAlchemy engine
        min_snapshots: Minimum number of snapshots
        min_price_range: Minimum price range (max - min)

    Returns:
        DataFrame with active tickers
    """
    summary = get_ticker_summary(engine)
    summary['price_range'] = summary['max_yes_prob'] - summary['min_yes_prob']

    active = summary[
        (summary['snapshot_count'] >= min_snapshots) &
        (summary['price_range'] >= min_price_range)
    ].copy()

    return active.sort_values('price_range', ascending=False)
