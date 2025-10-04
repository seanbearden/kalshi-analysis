"""Markets API endpoints."""

from fastapi import APIRouter, HTTPException, Query
from uuid import UUID

from domain.repositories import MarketRepository
from infrastructure.database.session import SessionDep
from schemas import (
    MarketSnapshotListResponse,
    MarketSnapshotResponse,
    SnapshotQueryParams,
)

router = APIRouter(prefix="/markets", tags=["markets"])


@router.get("", response_model=MarketSnapshotListResponse)
async def get_all_markets(
    session: SessionDep,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
) -> MarketSnapshotListResponse:
    """Get latest snapshot for all markets.

    Returns the most recent snapshot for each unique ticker.

    Args:
        session: Database session
        skip: Number of results to skip
        limit: Maximum results to return

    Returns:
        List of latest market snapshots
    """
    repo = MarketRepository(session)
    snapshots = await repo.get_all_latest(skip=skip, limit=limit)

    return MarketSnapshotListResponse(
        snapshots=[
            MarketSnapshotResponse.model_validate(s) for s in snapshots
        ],
        total=len(snapshots),
        skip=skip,
        limit=limit,
    )


@router.get("/{ticker}/snapshots", response_model=MarketSnapshotListResponse)
async def get_snapshots(
    ticker: str,
    session: SessionDep,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
) -> MarketSnapshotListResponse:
    """Get all snapshots for a market ticker.

    Args:
        ticker: Market ticker
        session: Database session
        skip: Number of results to skip
        limit: Maximum results to return

    Returns:
        List of market snapshots
    """
    repo = MarketRepository(session)
    snapshots = await repo.get_by_ticker(ticker, skip=skip, limit=limit)

    return MarketSnapshotListResponse(
        snapshots=[
            MarketSnapshotResponse.model_validate(s) for s in snapshots
        ],
        total=len(snapshots),
        skip=skip,
        limit=limit,
    )


@router.get("/{ticker}/latest", response_model=MarketSnapshotResponse)
async def get_latest_snapshot(
    ticker: str, session: SessionDep
) -> MarketSnapshotResponse:
    """Get most recent snapshot for a market.

    Args:
        ticker: Market ticker
        session: Database session

    Returns:
        Latest market snapshot

    Raises:
        HTTPException: If no snapshots found
    """
    repo = MarketRepository(session)
    snapshot = await repo.get_latest_by_ticker(ticker)

    if snapshot is None:
        raise HTTPException(
            status_code=404, detail=f"No snapshots found for ticker {ticker}"
        )

    return MarketSnapshotResponse.model_validate(snapshot)


@router.get("/{id}", response_model=MarketSnapshotResponse)
async def get_snapshot_by_id(
    id: UUID, session: SessionDep
) -> MarketSnapshotResponse:
    """Get market snapshot by ID.

    Args:
        id: Snapshot UUID
        session: Database session

    Returns:
        Market snapshot

    Raises:
        HTTPException: If snapshot not found
    """
    repo = MarketRepository(session)
    snapshot = await repo.get(id)

    if snapshot is None:
        raise HTTPException(
            status_code=404, detail=f"Snapshot {id} not found"
        )

    return MarketSnapshotResponse.model_validate(snapshot)
