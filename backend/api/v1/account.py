"""Account integration API endpoints."""

import logging
from datetime import UTC, datetime, timedelta

import jwt
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import get_settings
from core.exceptions import AuthenticationError, ConfigurationError
from infrastructure.database.session import get_session
from infrastructure.kalshi.authenticated_client import AuthenticatedKalshiClient
from schemas.account import (
    AuthenticateRequest,
    AuthenticateResponse,
    Balance,
    LogoutResponse,
    Portfolio,
    Position,
)
from services.account.credential_manager import CredentialManager
from services.account.position_tracker import PositionTracker

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/account", tags=["account"])
security = HTTPBearer()


def create_jwt_token(user_id: str) -> tuple[str, datetime]:
    """Create JWT session token.

    Args:
        user_id: User identifier to encode in token

    Returns:
        Tuple of (token string, expiration datetime)

    Raises:
        ConfigurationError: If JWT secret key not configured
    """
    settings = get_settings()

    if not settings.jwt_secret_key:
        raise ConfigurationError("JWT_SECRET_KEY not configured")

    now = datetime.now(UTC)
    expires_at = now + timedelta(hours=settings.jwt_expiration_hours)

    payload = {
        "sub": user_id,
        "iat": now,
        "exp": expires_at,
    }

    token = jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)
    return token, expires_at


def verify_jwt_token(token: str) -> str:
    """Verify JWT token and extract user_id.

    Args:
        token: JWT token string

    Returns:
        User ID from token

    Raises:
        HTTPException: If token is invalid or expired
    """
    settings = get_settings()

    if not settings.jwt_secret_key:
        raise ConfigurationError("JWT_SECRET_KEY not configured")

    try:
        payload = jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token: missing user ID"
            )
        return user_id

    except jwt.ExpiredSignatureError as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token expired") from e
    except jwt.InvalidTokenError as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token") from e


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> str:
    """Dependency to extract user_id from JWT token.

    Args:
        credentials: HTTP Bearer token credentials

    Returns:
        User ID from validated token
    """
    return verify_jwt_token(credentials.credentials)


@router.post("/authenticate", response_model=AuthenticateResponse)
async def authenticate(
    request: AuthenticateRequest,
    session: AsyncSession = Depends(get_session),
) -> AuthenticateResponse:
    """Authenticate with Kalshi API key and create session.

    Validates API key with Kalshi, stores encrypted credentials,
    and returns JWT session token.

    Args:
        request: Authentication request with API key
        session: Database session

    Returns:
        Authentication response with JWT token

    Raises:
        HTTPException: If API key is invalid or authentication fails
    """
    try:
        # Verify API key with Kalshi
        async with AuthenticatedKalshiClient(request.api_key) as kalshi_client:
            is_valid = await kalshi_client.verify_credentials()

            if not is_valid:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid Kalshi API key",
                )

        # Store encrypted credentials
        # For Phase 1 (single-user), use "default" as user_id
        user_id = "default"
        credential_manager = CredentialManager(session)
        await credential_manager.store_credentials(user_id, request.api_key)

        # Create JWT session token
        token, expires_at = create_jwt_token(user_id)

        logger.info(f"User {user_id} authenticated successfully")

        return AuthenticateResponse(
            status="authenticated",
            user_id=user_id,
            session_expires_at=expires_at,
            token=token,
        )

    except HTTPException:
        # Re-raise HTTPException without modification
        raise
    except AuthenticationError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
        ) from e
    except ConfigurationError as e:
        logger.error(f"Configuration error during authentication: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Server configuration error",
        ) from e
    except Exception as e:
        logger.error(f"Unexpected error during authentication: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Authentication failed",
        ) from e


@router.get("/portfolio", response_model=Portfolio)
async def get_portfolio(
    user_id: str = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> Portfolio:
    """Get complete portfolio snapshot.

    Fetches portfolio data from Kalshi, updates position cache,
    and returns comprehensive portfolio snapshot.

    Args:
        user_id: User ID from JWT token
        session: Database session

    Returns:
        Portfolio snapshot with balance and positions

    Raises:
        HTTPException: If credentials not found or Kalshi API fails
    """
    try:
        # Get stored credentials
        credential_manager = CredentialManager(session)
        api_key = await credential_manager.get_credentials(user_id)

        if not api_key:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="No credentials found. Please authenticate first.",
            )

        # Fetch portfolio from Kalshi
        async with AuthenticatedKalshiClient(api_key) as kalshi_client:
            balance_data = await kalshi_client.get_balance()
            positions_data = await kalshi_client.get_positions()

        # Update position tracker
        position_tracker = PositionTracker(session, user_id)
        await position_tracker.load_positions()

        # Process positions and calculate P&L
        positions = []
        for pos_data in positions_data:
            # Update position in tracker
            position_state = await position_tracker.update_position(
                ticker=pos_data["ticker"],
                side=pos_data["side"],
                quantity=pos_data["quantity"],
                avg_entry_price=pos_data["avg_entry_price"],
                current_price=pos_data["current_price"],
                entry_time=datetime.fromisoformat(pos_data["entry_time"])
                if "entry_time" in pos_data
                else None,
            )

            # Convert to schema
            position = Position(
                ticker=position_state.ticker,
                side=position_state.side,
                quantity=position_state.quantity,
                avg_entry_price=position_state.avg_entry_price,
                current_price=position_state.current_price,
                unrealized_pnl=position_state.unrealized_pnl,
                unrealized_pnl_pct=position_state.unrealized_pnl_pct,
                entry_time=position_state.entry_time,
            )
            positions.append(position)

        # Create portfolio response
        balance = Balance(
            cash_balance=balance_data.get("cash_balance", 0),
            total_value=balance_data.get("total_value", 0),
        )

        total_unrealized_pnl = await position_tracker.get_total_unrealized_pnl()

        return Portfolio(
            balance=balance,
            positions=positions,
            total_unrealized_pnl=total_unrealized_pnl,
            num_positions=len(positions),
            snapshot_time=datetime.now(UTC),
        )

    except HTTPException:
        # Re-raise HTTPException without modification
        raise
    except AuthenticationError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
        ) from e
    except Exception as e:
        logger.error(f"Error fetching portfolio: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch portfolio",
        ) from e


@router.get("/positions", response_model=list[Position])
async def get_positions(
    user_id: str = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> list[Position]:
    """Get all current positions.

    Args:
        user_id: User ID from JWT token
        session: Database session

    Returns:
        List of positions

    Raises:
        HTTPException: If credentials not found or Kalshi API fails
    """
    try:
        # Get stored credentials
        credential_manager = CredentialManager(session)
        api_key = await credential_manager.get_credentials(user_id)

        if not api_key:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="No credentials found. Please authenticate first.",
            )

        # Fetch positions from Kalshi
        async with AuthenticatedKalshiClient(api_key) as kalshi_client:
            positions_data = await kalshi_client.get_positions()

        # Update position tracker and build response
        position_tracker = PositionTracker(session, user_id)
        await position_tracker.load_positions()

        positions = []
        for pos_data in positions_data:
            # Update position in tracker
            position_state = await position_tracker.update_position(
                ticker=pos_data["ticker"],
                side=pos_data["side"],
                quantity=pos_data["quantity"],
                avg_entry_price=pos_data["avg_entry_price"],
                current_price=pos_data["current_price"],
                entry_time=datetime.fromisoformat(pos_data["entry_time"])
                if "entry_time" in pos_data
                else None,
            )

            # Convert to schema
            position = Position(
                ticker=position_state.ticker,
                side=position_state.side,
                quantity=position_state.quantity,
                avg_entry_price=position_state.avg_entry_price,
                current_price=position_state.current_price,
                unrealized_pnl=position_state.unrealized_pnl,
                unrealized_pnl_pct=position_state.unrealized_pnl_pct,
                entry_time=position_state.entry_time,
            )
            positions.append(position)

        return positions

    except HTTPException:
        # Re-raise HTTPException without modification
        raise
    except AuthenticationError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
        ) from e
    except Exception as e:
        logger.error(f"Error fetching positions: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch positions",
        ) from e


@router.delete("/logout", response_model=LogoutResponse)
async def logout(
    user_id: str = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> LogoutResponse:
    """Logout and clear stored credentials.

    Removes stored API key and clears position cache.

    Args:
        user_id: User ID from JWT token
        session: Database session

    Returns:
        Logout confirmation
    """
    try:
        # Delete credentials
        credential_manager = CredentialManager(session)
        await credential_manager.delete_credentials(user_id)

        # Clear positions
        position_tracker = PositionTracker(session, user_id)
        await position_tracker.clear_all_positions()

        logger.info(f"User {user_id} logged out successfully")

        return LogoutResponse(
            status="logged_out",
            message="Successfully logged out and cleared credentials",
        )

    except Exception as e:
        logger.error(f"Error during logout: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Logout failed",
        ) from e
