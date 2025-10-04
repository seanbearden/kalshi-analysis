"""Initial schema with enhanced models

Revision ID: 001
Revises:
Create Date: 2025-01-03 12:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# Mark as public to indicate these variables are used by Alembic via introspection
__all__ = ["revision", "down_revision", "branch_labels", "depends_on", "upgrade", "downgrade"]


def upgrade() -> None:
    # Create market_snapshots table
    op.create_table(
        "market_snapshots",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("ticker", sa.String(length=50), nullable=False),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "source", sa.Enum("POLL", "WEBSOCKET", "BACKFILL", name="datasource"), nullable=False
        ),
        sa.Column("sequence", sa.Integer(), nullable=True),
        sa.Column("yes_price", sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column("no_price", sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column("volume", sa.Integer(), nullable=False),
        sa.Column(
            "raw_data",
            postgresql.JSON(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )

    # Create indexes for market_snapshots
    op.create_index("ix_ticker_timestamp", "market_snapshots", ["ticker", "timestamp"])
    op.create_index(op.f("ix_market_snapshots_source"), "market_snapshots", ["source"])
    op.create_index(op.f("ix_market_snapshots_ticker"), "market_snapshots", ["ticker"])
    op.create_index(op.f("ix_market_snapshots_timestamp"), "market_snapshots", ["timestamp"])

    # Create unique index for WebSocket deduplication
    op.create_index(
        "ix_ticker_source_sequence",
        "market_snapshots",
        ["ticker", "source", "sequence"],
        unique=True,
        postgresql_where=sa.text("source = 'WEBSOCKET'"),
    )

    # Create backtest_results table
    op.create_table(
        "backtest_results",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "strategy",
            sa.Enum(
                "LONG_FAVORITE",
                "FADE_OVERREACTION",
                "MEAN_REVERSION",
                "MOMENTUM",
                name="strategytype",
            ),
            nullable=False,
        ),
        sa.Column("start_date", sa.DateTime(), nullable=False),
        sa.Column("end_date", sa.DateTime(), nullable=False),
        sa.Column("market_filter", sa.String(length=100), nullable=True),
        sa.Column("total_pnl", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column("sharpe_ratio", sa.Numeric(precision=6, scale=3), nullable=True),
        sa.Column("max_drawdown", sa.Numeric(precision=6, scale=3), nullable=True),
        sa.Column("win_rate", sa.Numeric(precision=5, scale=2), nullable=True),
        sa.Column("total_trades", sa.Integer(), nullable=False),
        sa.Column(
            "parameters",
            postgresql.JSON(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )

    # Create indexes for backtest_results
    op.create_index("ix_strategy_created", "backtest_results", ["strategy", "created_at"])
    op.create_index(op.f("ix_backtest_results_created_at"), "backtest_results", ["created_at"])
    op.create_index(op.f("ix_backtest_results_strategy"), "backtest_results", ["strategy"])

    # Create backtest_executions table
    op.create_table(
        "backtest_executions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("backtest_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("ticker", sa.String(length=50), nullable=False),
        sa.Column("direction", sa.Enum("LONG", "SHORT", name="tradedirection"), nullable=False),
        sa.Column("entry_time", sa.DateTime(), nullable=False),
        sa.Column("entry_price", sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column("exit_time", sa.DateTime(), nullable=False),
        sa.Column("exit_price", sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column("size", sa.Integer(), nullable=False),
        sa.Column("pnl", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column(
            "trade_metadata",
            postgresql.JSON(astext_type=sa.Text()),
            nullable=True,
        ),
        sa.ForeignKeyConstraint(["backtest_id"], ["backtest_results.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )

    # Create indexes for backtest_executions
    op.create_index("ix_backtest_entry_time", "backtest_executions", ["backtest_id", "entry_time"])
    op.create_index(
        op.f("ix_backtest_executions_backtest_id"), "backtest_executions", ["backtest_id"]
    )
    op.create_index("ix_ticker_entry_time", "backtest_executions", ["ticker", "entry_time"])
    op.create_index(op.f("ix_backtest_executions_ticker"), "backtest_executions", ["ticker"])


def downgrade() -> None:
    # Drop backtest_executions
    op.drop_index("ix_ticker_entry_time", table_name="backtest_executions")
    op.drop_index(op.f("ix_backtest_executions_ticker"), table_name="backtest_executions")
    op.drop_index(op.f("ix_backtest_executions_backtest_id"), table_name="backtest_executions")
    op.drop_index("ix_backtest_entry_time", table_name="backtest_executions")
    op.drop_table("backtest_executions")

    # Drop backtest_results
    op.drop_index(op.f("ix_backtest_results_strategy"), table_name="backtest_results")
    op.drop_index(op.f("ix_backtest_results_created_at"), table_name="backtest_results")
    op.drop_index("ix_strategy_created", table_name="backtest_results")
    op.drop_table("backtest_results")

    # Drop market_snapshots
    op.drop_index("ix_ticker_source_sequence", table_name="market_snapshots")
    op.drop_index(op.f("ix_market_snapshots_timestamp"), table_name="market_snapshots")
    op.drop_index(op.f("ix_market_snapshots_ticker"), table_name="market_snapshots")
    op.drop_index(op.f("ix_market_snapshots_source"), table_name="market_snapshots")
    op.drop_index("ix_ticker_timestamp", table_name="market_snapshots")
    op.drop_table("market_snapshots")

    # Drop enums
    op.execute("DROP TYPE tradedirection")
    op.execute("DROP TYPE strategytype")
    op.execute("DROP TYPE datasource")
