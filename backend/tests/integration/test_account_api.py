"""Integration tests for Account API endpoints."""

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, patch

import jwt
import pytest
from httpx import AsyncClient
from sqlalchemy import select

from domain.models.account import PositionCache, UserCredential


class TestAccountAPI:
    """Integration tests for account authentication and portfolio endpoints."""

    @pytest.mark.asyncio
    async def test_authenticate_success(self, client: AsyncClient, session, mock_settings):
        """Test successful authentication with valid API key."""
        # Mock Kalshi API balance endpoint to verify credentials
        mock_balance_response = {"cash_balance": 100000, "total_value": 150000}

        with patch(
            "infrastructure.kalshi.authenticated_client.AuthenticatedKalshiClient.get_balance",
            new_callable=AsyncMock,
        ) as mock_get_balance:
            mock_get_balance.return_value = mock_balance_response

            # Authenticate
            response = await client.post(
                "/api/v1/account/authenticate",
                json={"api_key": "valid_test_api_key_12345"},  # pragma: allowlist secret
            )

            assert response.status_code == 200
            data = response.json()

            # Verify response structure
            assert data["status"] == "authenticated"
            assert data["user_id"] == "default"
            assert "token" in data
            assert "session_expires_at" in data

            # Verify JWT token is valid using the mocked settings
            decoded = jwt.decode(
                data["token"],
                str(mock_settings.jwt_secret_key),
                algorithms=[mock_settings.jwt_algorithm],
            )
            assert decoded["sub"] == "default"

            # Verify credentials were stored encrypted
            stmt = select(UserCredential).where(UserCredential.user_id == "default")
            result = await session.execute(stmt)
            credential = result.scalar_one_or_none()

            assert credential is not None
            assert credential.user_id == "default"
            assert (
                credential.encrypted_api_key
                != "valid_test_api_key_12345"  # pragma: allowlist secret
            )
            assert len(credential.encrypted_api_key) > 0

    @pytest.mark.asyncio
    async def test_authenticate_invalid_api_key(self, client: AsyncClient):
        """Test authentication fails with invalid API key."""
        # Mock Kalshi API to return authentication error
        with patch("api.v1.account.AuthenticatedKalshiClient") as MockAuthClient:
            # Create mock instance
            mock_instance = AsyncMock()
            mock_instance.verify_credentials = AsyncMock(return_value=False)
            mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
            mock_instance.__aexit__ = AsyncMock(return_value=None)
            MockAuthClient.return_value = mock_instance

            response = await client.post(
                "/api/v1/account/authenticate",
                json={"api_key": "invalid_key"},  # pragma: allowlist secret
            )

            assert response.status_code == 401
            assert "Invalid Kalshi API key" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_authenticate_empty_api_key(self, client: AsyncClient):
        """Test authentication fails with empty API key."""
        response = await client.post("/api/v1/account/authenticate", json={"api_key": ""})

        assert response.status_code == 422  # Validation error
        assert "api_key" in response.text.lower()

    @pytest.mark.asyncio
    async def test_get_portfolio_success(self, client: AsyncClient, session):
        """Test successful portfolio retrieval with valid authentication."""
        # First authenticate to get JWT token
        mock_balance_response = {"cash_balance": 100000, "total_value": 150000}
        mock_portfolio_response = {
            "balance": {"cash_balance": 100000, "total_value": 150000},
            "positions": [],
        }
        mock_positions_response = [
            {
                "ticker": "PRES-2024",
                "side": "YES",
                "quantity": 100,
                "avg_entry_price": 55,
                "current_price": 60,
                "entry_time": "2024-01-01T00:00:00Z",
            },
            {
                "ticker": "NFL-CHIEFS",
                "side": "NO",
                "quantity": 50,
                "avg_entry_price": 70,
                "current_price": 65,
                "entry_time": "2024-01-02T00:00:00Z",
            },
        ]

        with (
            patch(
                "infrastructure.kalshi.authenticated_client.AuthenticatedKalshiClient.get_balance",
                new_callable=AsyncMock,
            ) as mock_get_balance,
            patch(
                "infrastructure.kalshi.authenticated_client.AuthenticatedKalshiClient.get_portfolio",
                new_callable=AsyncMock,
            ) as mock_get_portfolio,
            patch(
                "infrastructure.kalshi.authenticated_client.AuthenticatedKalshiClient.get_positions",
                new_callable=AsyncMock,
            ) as mock_get_positions,
        ):
            # Setup mocks
            mock_get_balance.return_value = mock_balance_response
            mock_get_portfolio.return_value = mock_portfolio_response
            mock_get_positions.return_value = mock_positions_response

            # Authenticate
            auth_response = await client.post(
                "/api/v1/account/authenticate",
                json={
                    "api_key": "test_api_key"  # pragma: allowlist secret
                },
            )
            assert auth_response.status_code == 200
            token = auth_response.json()["token"]

            # Get portfolio
            portfolio_response = await client.get(
                "/api/v1/account/portfolio", headers={"Authorization": f"Bearer {token}"}
            )

            assert portfolio_response.status_code == 200
            portfolio = portfolio_response.json()

            # Verify portfolio structure
            assert "balance" in portfolio
            # Handle Decimal serialization (can be string or int)
            cash_balance = portfolio["balance"]["cash_balance"]
            assert int(cash_balance) if isinstance(cash_balance, str) else cash_balance == 100000
            total_value = portfolio["balance"]["total_value"]
            assert int(total_value) if isinstance(total_value, str) else total_value == 150000

            assert "positions" in portfolio
            assert len(portfolio["positions"]) == 2
            assert portfolio["num_positions"] == 2

            # Verify position data (handle Decimal serialization)
            yes_position = next(p for p in portfolio["positions"] if p["side"] == "YES")
            assert yes_position["ticker"] == "PRES-2024"
            assert yes_position["quantity"] == 100
            avg_entry = yes_position["avg_entry_price"]
            assert int(avg_entry) if isinstance(avg_entry, str) else avg_entry == 55
            current = yes_position["current_price"]
            assert int(current) if isinstance(current, str) else current == 60
            pnl_yes = yes_position["unrealized_pnl"]
            assert int(pnl_yes) if isinstance(pnl_yes, str) else pnl_yes == 500  # (60 - 55) * 100

            no_position = next(p for p in portfolio["positions"] if p["side"] == "NO")
            assert no_position["ticker"] == "NFL-CHIEFS"
            assert no_position["quantity"] == 50
            pnl_no = no_position["unrealized_pnl"]
            assert int(pnl_no) if isinstance(pnl_no, str) else pnl_no == 250  # (70 - 65) * 50

            # Verify total P&L
            total_pnl = portfolio["total_unrealized_pnl"]
            assert int(total_pnl) if isinstance(total_pnl, str) else total_pnl == 750  # 500 + 250

            # Verify positions were cached in database
            stmt = select(PositionCache).where(PositionCache.user_id == "default")
            result = await session.execute(stmt)
            cached_positions = result.scalars().all()

            assert len(cached_positions) == 2
            cached_tickers = {p.ticker for p in cached_positions}
            assert "PRES-2024" in cached_tickers
            assert "NFL-CHIEFS" in cached_tickers

    @pytest.mark.asyncio
    async def test_get_portfolio_no_credentials(self, client: AsyncClient, mock_settings):
        """Test portfolio retrieval fails without authentication."""
        # Create a fake token (not from actual authentication)
        fake_token = jwt.encode(
            {"sub": "nonexistent_user", "exp": datetime.now(UTC) + timedelta(hours=1)},
            str(mock_settings.jwt_secret_key),
            algorithm=mock_settings.jwt_algorithm,
        )

        response = await client.get(
            "/api/v1/account/portfolio", headers={"Authorization": f"Bearer {fake_token}"}
        )

        assert response.status_code == 401
        assert "No credentials found" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_get_portfolio_missing_token(self, client: AsyncClient):
        """Test portfolio retrieval fails without JWT token."""
        response = await client.get("/api/v1/account/portfolio")

        assert response.status_code == 403  # Forbidden - no credentials provided

    @pytest.mark.asyncio
    async def test_get_portfolio_invalid_token(self, client: AsyncClient):
        """Test portfolio retrieval fails with invalid JWT token."""
        response = await client.get(
            "/api/v1/account/portfolio", headers={"Authorization": "Bearer invalid_token"}
        )

        assert response.status_code == 401
        assert "Invalid token" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_get_portfolio_expired_token(self, client: AsyncClient, mock_settings):
        """Test portfolio retrieval fails with expired JWT token."""
        # Create an expired token
        expired_token = jwt.encode(
            {"sub": "default", "exp": datetime.now(UTC) - timedelta(hours=1)},
            str(mock_settings.jwt_secret_key),
            algorithm=mock_settings.jwt_algorithm,
        )

        response = await client.get(
            "/api/v1/account/portfolio", headers={"Authorization": f"Bearer {expired_token}"}
        )

        assert response.status_code == 401
        assert "Token expired" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_get_positions_success(self, client: AsyncClient):
        """Test successful positions retrieval."""
        mock_balance_response = {"cash_balance": 100000, "total_value": 150000}
        mock_portfolio_response = {"balance": mock_balance_response, "positions": []}
        mock_positions_response = [
            {
                "ticker": "TEST-MARKET",
                "side": "YES",
                "quantity": 10,
                "avg_entry_price": 50,
                "current_price": 55,
                "entry_time": "2024-01-01T00:00:00Z",
            }
        ]

        with (
            patch(
                "infrastructure.kalshi.authenticated_client.AuthenticatedKalshiClient.get_balance",
                new_callable=AsyncMock,
            ) as mock_get_balance,
            patch(
                "infrastructure.kalshi.authenticated_client.AuthenticatedKalshiClient.get_portfolio",
                new_callable=AsyncMock,
            ) as mock_get_portfolio,
            patch(
                "infrastructure.kalshi.authenticated_client.AuthenticatedKalshiClient.get_positions",
                new_callable=AsyncMock,
            ) as mock_get_positions,
        ):
            mock_get_balance.return_value = mock_balance_response
            mock_get_portfolio.return_value = mock_portfolio_response
            mock_get_positions.return_value = mock_positions_response

            # Authenticate
            auth_response = await client.post(
                "/api/v1/account/authenticate",
                json={
                    "api_key": "test_api_key"  # pragma: allowlist secret
                },
            )
            token = auth_response.json()["token"]

            # Get positions
            positions_response = await client.get(
                "/api/v1/account/positions", headers={"Authorization": f"Bearer {token}"}
            )

            assert positions_response.status_code == 200
            positions = positions_response.json()

            assert len(positions) == 1
            assert positions[0]["ticker"] == "TEST-MARKET"
            assert positions[0]["side"] == "YES"
            # Handle Decimal serialization (can be string or int)
            pnl = positions[0]["unrealized_pnl"]
            assert int(pnl) if isinstance(pnl, str) else pnl == 50  # (55 - 50) * 10

    @pytest.mark.asyncio
    async def test_logout_success(self, client: AsyncClient, session):
        """Test successful logout and credential cleanup."""
        mock_balance_response = {"cash_balance": 100000, "total_value": 150000}

        with patch(
            "infrastructure.kalshi.authenticated_client.AuthenticatedKalshiClient.get_balance",
            new_callable=AsyncMock,
        ) as mock_get_balance:
            mock_get_balance.return_value = mock_balance_response

            # Authenticate first
            auth_response = await client.post(
                "/api/v1/account/authenticate",
                json={
                    "api_key": "test_api_key"  # pragma: allowlist secret
                },
            )
            token = auth_response.json()["token"]

            # Verify credentials exist
            stmt = select(UserCredential).where(UserCredential.user_id == "default")
            result = await session.execute(stmt)
            credential = result.scalar_one_or_none()
            assert credential is not None

            # Logout
            logout_response = await client.delete(
                "/api/v1/account/logout", headers={"Authorization": f"Bearer {token}"}
            )

            assert logout_response.status_code == 200
            logout_data = logout_response.json()
            assert logout_data["status"] == "logged_out"

            # Verify credentials were deleted
            stmt = select(UserCredential).where(UserCredential.user_id == "default")
            result = await session.execute(stmt)
            credential = result.scalar_one_or_none()
            assert credential is None

            # Verify positions were cleared
            stmt = select(PositionCache).where(PositionCache.user_id == "default")
            result = await session.execute(stmt)
            positions = result.scalars().all()
            assert len(positions) == 0

    @pytest.mark.asyncio
    async def test_logout_missing_token(self, client: AsyncClient):
        """Test logout fails without JWT token."""
        response = await client.delete("/api/v1/account/logout")

        assert response.status_code == 403  # Forbidden - no credentials provided

    @pytest.mark.asyncio
    async def test_jwt_token_lifecycle(self, client: AsyncClient, mock_settings):
        """Test JWT token generation, validation, and expiration."""
        mock_balance_response = {"cash_balance": 100000, "total_value": 150000}

        with patch(
            "infrastructure.kalshi.authenticated_client.AuthenticatedKalshiClient.get_balance",
            new_callable=AsyncMock,
        ) as mock_get_balance:
            mock_get_balance.return_value = mock_balance_response

            # Authenticate and get token
            auth_response = await client.post(
                "/api/v1/account/authenticate",
                json={"api_key": "test_api_key"},  # pragma: allowlist secret
            )
            data = auth_response.json()
            token = data["token"]
            expires_at = datetime.fromisoformat(data["session_expires_at"].replace("Z", "+00:00"))

            # Verify token is valid using mocked settings
            decoded = jwt.decode(token, str(mock_settings.jwt_secret_key), algorithms=["HS256"])
            assert decoded["sub"] == "default"

            # Verify expiration time is approximately correct (24 hours from now)
            expected_expiration = datetime.now(UTC) + timedelta(
                hours=mock_settings.jwt_expiration_hours
            )
            time_diff = abs((expires_at - expected_expiration).total_seconds())
            assert time_diff < 5  # Within 5 seconds

    @pytest.mark.asyncio
    async def test_pnl_calculation_yes_position(self, client: AsyncClient):
        """Test P&L calculation for YES position."""
        mock_balance_response = {"cash_balance": 100000, "total_value": 150000}
        mock_portfolio_response = {"balance": mock_balance_response, "positions": []}
        mock_positions_response = [
            {
                "ticker": "TEST-YES",
                "side": "YES",
                "quantity": 100,
                "avg_entry_price": 50,  # Bought at 50 cents
                "current_price": 60,  # Now worth 60 cents
                "entry_time": "2024-01-01T00:00:00Z",
            }
        ]

        with (
            patch(
                "infrastructure.kalshi.authenticated_client.AuthenticatedKalshiClient.get_balance",
                new_callable=AsyncMock,
            ) as mock_get_balance,
            patch(
                "infrastructure.kalshi.authenticated_client.AuthenticatedKalshiClient.get_portfolio",
                new_callable=AsyncMock,
            ) as mock_get_portfolio,
            patch(
                "infrastructure.kalshi.authenticated_client.AuthenticatedKalshiClient.get_positions",
                new_callable=AsyncMock,
            ) as mock_get_positions,
        ):
            mock_get_balance.return_value = mock_balance_response
            mock_get_portfolio.return_value = mock_portfolio_response
            mock_get_positions.return_value = mock_positions_response

            # Authenticate and get portfolio
            auth_response = await client.post(
                "/api/v1/account/authenticate",
                json={"api_key": "test_api_key"},  # pragma: allowlist secret
            )
            token = auth_response.json()["token"]

            portfolio_response = await client.get(
                "/api/v1/account/portfolio", headers={"Authorization": f"Bearer {token}"}
            )
            portfolio = portfolio_response.json()

            # YES position P&L = (current_price - avg_entry_price) * quantity
            # (60 - 50) * 100 = 1000 cents = $10.00
            position = portfolio["positions"][0]
            # Handle both int and string (from Decimal serialization)
            pnl = position["unrealized_pnl"]
            assert int(pnl) if isinstance(pnl, str) else pnl == 1000
            pnl_pct = float(position["unrealized_pnl_pct"])
            assert pnl_pct == pytest.approx(20.0, rel=0.01)  # 10/50 * 100 = 20%

    @pytest.mark.asyncio
    async def test_pnl_calculation_no_position(self, client: AsyncClient):
        """Test P&L calculation for NO position."""
        mock_balance_response = {"cash_balance": 100000, "total_value": 150000}
        mock_portfolio_response = {"balance": mock_balance_response, "positions": []}
        mock_positions_response = [
            {
                "ticker": "TEST-NO",
                "side": "NO",
                "quantity": 50,
                "avg_entry_price": 70,  # Bought NO at 70 (paid 30 cents per contract)
                "current_price": 65,  # YES now at 65 (NO worth 35)
                "entry_time": "2024-01-01T00:00:00Z",
            }
        ]

        with (
            patch(
                "infrastructure.kalshi.authenticated_client.AuthenticatedKalshiClient.get_balance",
                new_callable=AsyncMock,
            ) as mock_get_balance,
            patch(
                "infrastructure.kalshi.authenticated_client.AuthenticatedKalshiClient.get_portfolio",
                new_callable=AsyncMock,
            ) as mock_get_portfolio,
            patch(
                "infrastructure.kalshi.authenticated_client.AuthenticatedKalshiClient.get_positions",
                new_callable=AsyncMock,
            ) as mock_get_positions,
        ):
            mock_get_balance.return_value = mock_balance_response
            mock_get_portfolio.return_value = mock_portfolio_response
            mock_get_positions.return_value = mock_positions_response

            # Authenticate and get portfolio
            auth_response = await client.post(
                "/api/v1/account/authenticate",
                json={"api_key": "test_api_key"},  # pragma: allowlist secret
            )
            token = auth_response.json()["token"]

            portfolio_response = await client.get(
                "/api/v1/account/portfolio", headers={"Authorization": f"Bearer {token}"}
            )
            portfolio = portfolio_response.json()

            # NO position P&L = (avg_entry_price - current_price) * quantity
            # (70 - 65) * 50 = 250 cents = $2.50
            position = portfolio["positions"][0]
            # Handle both int and string (from Decimal serialization)
            pnl = position["unrealized_pnl"]
            assert int(pnl) if isinstance(pnl, str) else pnl == 250
            # P&L% = 250 / (70 * 50) * 100 = 7.14%
            pnl_pct = float(position["unrealized_pnl_pct"])
            assert pnl_pct == pytest.approx(7.14, rel=0.02)
