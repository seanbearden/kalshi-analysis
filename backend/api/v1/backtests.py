"""Backtests API endpoints."""

from uuid import UUID

from fastapi import APIRouter, HTTPException, Query

from domain.models import StrategyType
from domain.repositories import BacktestRepository
from infrastructure.database.session import SessionDep
from schemas import (
    BacktestCreateRequest,
    BacktestQueryParams,
    BacktestResultListResponse,
    BacktestResultResponse,
)

router = APIRouter(prefix="/backtests", tags=["backtests"])


@router.get("/", response_model=BacktestResultListResponse)
async def list_backtests(
    session: SessionDep,
    strategy: StrategyType | None = None,
    include_executions: bool = False,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
) -> BacktestResultListResponse:
    """List all backtests with optional filtering.

    Args:
        session: Database session
        strategy: Filter by strategy type
        include_executions: Include trade executions
        skip: Number of results to skip
        limit: Maximum results to return

    Returns:
        List of backtest results
    """
    repo = BacktestRepository(session)

    if strategy:
        results = await repo.get_by_strategy(strategy, skip=skip, limit=limit)
    else:
        results = await repo.get_all(skip=skip, limit=limit)

    # Load executions if requested
    if include_executions:
        results_with_executions = []
        for result in results:
            loaded = await repo.get_with_executions(result.id)
            if loaded:
                results_with_executions.append(loaded)
        results = results_with_executions

    return BacktestResultListResponse(
        results=[
            BacktestResultResponse.model_validate(r) for r in results
        ],
        total=len(results),
        skip=skip,
        limit=limit,
    )


@router.get("/{id}", response_model=BacktestResultResponse)
async def get_backtest(
    id: UUID, session: SessionDep, include_executions: bool = False
) -> BacktestResultResponse:
    """Get backtest by ID.

    Args:
        id: Backtest UUID
        session: Database session
        include_executions: Include trade executions

    Returns:
        Backtest result

    Raises:
        HTTPException: If backtest not found
    """
    repo = BacktestRepository(session)

    if include_executions:
        backtest = await repo.get_with_executions(id)
    else:
        backtest = await repo.get(id)

    if backtest is None:
        raise HTTPException(
            status_code=404, detail=f"Backtest {id} not found"
        )

    return BacktestResultResponse.model_validate(backtest)


@router.post("/", response_model=BacktestResultResponse, status_code=201)
async def create_backtest(
    request: BacktestCreateRequest, session: SessionDep
) -> BacktestResultResponse:
    """Create new backtest (placeholder - actual backtesting in Phase 1).

    Args:
        request: Backtest configuration
        session: Database session

    Returns:
        Created backtest result

    Note:
        This is a placeholder. Actual backtesting logic will be implemented
        in Phase 1 using backtrader/vectorbt in Jupyter notebooks.
    """
    repo = BacktestRepository(session)

    # Placeholder: In Phase 1, this will trigger actual backtest execution
    # For now, create a stub result
    backtest = await repo.create_backtest(
        strategy=request.strategy,
        start_date=request.start_date,
        end_date=request.end_date,
        market_filter=request.market_filter,
        total_pnl=0,
        total_trades=0,
        parameters=request.parameters,
    )

    return BacktestResultResponse.model_validate(backtest)
