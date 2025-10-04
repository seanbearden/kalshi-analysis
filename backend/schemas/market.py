"""Market API schemas for request/response validation."""

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field

from domain.models import DataSource


class MarketSnapshotResponse(BaseModel):
    """Market snapshot response schema."""

    id: UUID
    ticker: str
    timestamp: datetime
    source: DataSource
    sequence: int | None = None
    yes_price: Decimal = Field(description="YES price in cents")
    no_price: Decimal = Field(description="NO price in cents")
    volume: int = Field(description="Total volume traded")
    created_at: datetime

    model_config = {"from_attributes": True}


class MarketSnapshotListResponse(BaseModel):
    """List of market snapshots response."""

    snapshots: list[MarketSnapshotResponse]
    total: int
    skip: int
    limit: int


class MarketQueryParams(BaseModel):
    """Query parameters for market endpoints."""

    status: str | None = Field(None, description="Filter by status (open/closed)")
    limit: int = Field(100, ge=1, le=1000, description="Maximum results")
    skip: int = Field(0, ge=0, description="Number of results to skip")


class SnapshotQueryParams(BaseModel):
    """Query parameters for snapshot endpoints."""

    ticker: str = Field(..., description="Market ticker")
    start_time: datetime | None = Field(None, description="Range start (inclusive)")
    end_time: datetime | None = Field(None, description="Range end (inclusive)")
    source: DataSource | None = Field(None, description="Filter by data source")
    limit: int = Field(100, ge=1, le=1000, description="Maximum results")
    skip: int = Field(0, ge=0, description="Number of results to skip")
