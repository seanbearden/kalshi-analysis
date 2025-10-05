"""add account integration tables

Revision ID: 413e47bb0bb2
Revises: 001
Create Date: 2025-10-05 01:43:21.888212+00:00

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "413e47bb0bb2"
down_revision: str | None = "001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add user_credentials and position_cache tables for account integration."""

    # Create user_credentials table
    op.create_table(
        "user_credentials",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("user_id", sa.String(length=255), nullable=False),
        sa.Column("encrypted_api_key", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id"),
    )

    # Create index for user_id lookup
    op.create_index(op.f("ix_user_credentials_user_id"), "user_credentials", ["user_id"])

    # Create position_cache table
    op.create_table(
        "position_cache",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("user_id", sa.String(length=255), nullable=False),
        sa.Column("ticker", sa.String(length=50), nullable=False),
        sa.Column("side", sa.String(length=10), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("avg_entry_price", sa.Integer(), nullable=False, comment="Price in cents"),
        sa.Column("current_price", sa.Integer(), nullable=False, comment="Price in cents"),
        sa.Column("entry_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "cached_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "ticker", name="uq_user_ticker"),
        sa.CheckConstraint("side IN ('YES', 'NO')", name="ck_position_side"),
    )

    # Create indexes for position_cache
    op.create_index(
        "ix_position_cache_user_ticker",
        "position_cache",
        ["user_id", "ticker"],
    )
    op.create_index(op.f("ix_position_cache_user_id"), "position_cache", ["user_id"])


def downgrade() -> None:
    """Drop account integration tables."""

    # Drop position_cache
    op.drop_index(op.f("ix_position_cache_user_id"), table_name="position_cache")
    op.drop_index("ix_position_cache_user_ticker", table_name="position_cache")
    op.drop_table("position_cache")

    # Drop user_credentials
    op.drop_index(op.f("ix_user_credentials_user_id"), table_name="user_credentials")
    op.drop_table("user_credentials")
