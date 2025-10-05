"""Pydantic schemas for account integration endpoints."""

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field, field_validator

# Request Schemas


class AuthenticateRequest(BaseModel):
    """Request to authenticate with Kalshi API key."""

    api_key: str = Field(..., min_length=1, description="Kalshi API key")

    @field_validator("api_key")
    @classmethod
    def validate_api_key(cls, v: str) -> str:
        """Validate API key is not empty or whitespace."""
        if not v or not v.strip():
            raise ValueError("API key cannot be empty")
        return v.strip()


# Response Schemas


class AuthenticateResponse(BaseModel):
    """Response after successful authentication."""

    status: str = Field(..., description="Authentication status")
    user_id: str = Field(..., description="User identifier")
    session_expires_at: datetime = Field(..., description="JWT token expiration timestamp")
    token: str = Field(..., description="JWT session token")


class Balance(BaseModel):
    """User balance information."""

    cash_balance: Decimal = Field(..., description="Available cash balance in cents", ge=0)
    total_value: Decimal = Field(..., description="Total portfolio value in cents", ge=0)


class Position(BaseModel):
    """User position in a market."""

    ticker: str = Field(..., description="Market ticker")
    side: str = Field(..., description="Position side (YES or NO)")
    quantity: int = Field(..., description="Position quantity (number of contracts)", ge=0)
    avg_entry_price: Decimal = Field(..., description="Average entry price in cents", ge=0, le=100)
    current_price: Decimal = Field(..., description="Current market price in cents", ge=0, le=100)
    unrealized_pnl: Decimal = Field(..., description="Unrealized profit/loss in cents")
    unrealized_pnl_pct: Decimal = Field(..., description="Unrealized P&L percentage")
    entry_time: datetime = Field(..., description="Position entry timestamp")

    @field_validator("side")
    @classmethod
    def validate_side(cls, v: str) -> str:
        """Validate position side is YES or NO."""
        if v not in ("YES", "NO"):
            raise ValueError("Side must be YES or NO")
        return v


class Portfolio(BaseModel):
    """Complete portfolio snapshot."""

    balance: Balance = Field(..., description="Balance information")
    positions: list[Position] = Field(default_factory=list, description="List of current positions")
    total_unrealized_pnl: Decimal = Field(
        ..., description="Total unrealized P&L across all positions in cents"
    )
    num_positions: int = Field(..., description="Number of open positions", ge=0)
    snapshot_time: datetime = Field(..., description="Portfolio snapshot timestamp")


class LogoutResponse(BaseModel):
    """Response after logout."""

    status: str = Field(..., description="Logout status")
    message: str = Field(..., description="Human-readable message")
