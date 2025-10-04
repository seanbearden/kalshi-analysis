"""Backtest API schemas for request/response validation."""

from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field, ValidationInfo, field_validator

from domain.models import StrategyType, TradeDirection


class BacktestExecutionResponse(BaseModel):
    """Trade execution response schema."""

    id: UUID
    ticker: str
    direction: TradeDirection
    entry_time: datetime
    entry_price: Decimal
    exit_time: datetime
    exit_price: Decimal
    size: int
    pnl: Decimal
    reason: str | None = None

    model_config = {"from_attributes": True}


class BacktestResultResponse(BaseModel):
    """Backtest result response schema."""

    id: UUID
    strategy: StrategyType
    start_date: datetime
    end_date: datetime
    market_filter: str | None = None
    total_pnl: Decimal
    sharpe_ratio: Decimal | None = None
    max_drawdown: Decimal | None = None
    win_rate: Decimal | None = None
    total_trades: int
    parameters: dict[str, Any]
    created_at: datetime
    executions: list[BacktestExecutionResponse] | None = None

    model_config = {"from_attributes": True}


class BacktestResultListResponse(BaseModel):
    """List of backtest results response."""

    results: list[BacktestResultResponse]
    total: int
    skip: int
    limit: int


class BacktestCreateRequest(BaseModel):
    """Create backtest request schema."""

    strategy: StrategyType = Field(..., description="Trading strategy to backtest")
    start_date: datetime = Field(..., description="Backtest period start")
    end_date: datetime = Field(..., description="Backtest period end")
    market_filter: str | None = Field(
        None, description="Market selection criteria (e.g., 'politics')"
    )
    parameters: dict[str, Any] = Field(
        default_factory=dict, description="Strategy-specific parameters"
    )

    @field_validator("end_date")
    @classmethod
    def validate_date_range(cls, v: datetime, info: ValidationInfo) -> datetime:
        """Ensure end_date is after start_date."""
        if "start_date" in info.data and v <= info.data["start_date"]:
            raise ValueError("end_date must be after start_date")
        return v


class BacktestQueryParams(BaseModel):
    """Query parameters for backtest endpoints."""

    strategy: StrategyType | None = Field(None, description="Filter by strategy")
    include_executions: bool = Field(False, description="Include trade executions in response")
    limit: int = Field(100, ge=1, le=1000, description="Maximum results")
    skip: int = Field(0, ge=0, description="Number of results to skip")
