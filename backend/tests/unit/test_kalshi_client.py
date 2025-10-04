"""Unit tests for Kalshi API client."""

from unittest.mock import AsyncMock, patch

import httpx
import pytest

from core.exceptions import KalshiAPIError
from infrastructure.kalshi.client import KalshiClient


class TestKalshiClient:
    """Test suite for KalshiClient."""

    @pytest.fixture
    async def kalshi_client(self) -> KalshiClient:
        """Create Kalshi client instance."""
        client = KalshiClient()
        yield client
        await client.close()

    async def test_context_manager(self) -> None:
        """Test async context manager usage."""
        async with KalshiClient() as client:
            assert client.client is not None

    @patch("infrastructure.kalshi.client.httpx.AsyncClient.request")
    async def test_get_events_success(
        self, mock_request: AsyncMock, kalshi_client: KalshiClient
    ) -> None:
        """Test successful events retrieval."""
        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "events": [{"event_ticker": "PRES-2024", "title": "Presidential Election 2024"}]
        }
        mock_request.return_value = mock_response

        result = await kalshi_client.get_events()

        assert "events" in result
        assert len(result["events"]) == 1
        mock_request.assert_called_once()

    @patch("infrastructure.kalshi.client.httpx.AsyncClient.request")
    async def test_get_events_with_filters(
        self, mock_request: AsyncMock, kalshi_client: KalshiClient
    ) -> None:
        """Test events retrieval with filters."""
        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"events": []}
        mock_request.return_value = mock_response

        await kalshi_client.get_events(status="open", limit=50)

        # Verify correct parameters were passed
        call_kwargs = mock_request.call_args[1]
        assert call_kwargs["params"]["status"] == "open"
        assert call_kwargs["params"]["limit"] == 50

    @patch("infrastructure.kalshi.client.httpx.AsyncClient.request")
    async def test_get_markets_success(
        self, mock_request: AsyncMock, kalshi_client: KalshiClient
    ) -> None:
        """Test successful markets retrieval."""
        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "markets": [
                {
                    "ticker": "PRES-2024",
                    "yes_bid": 55.5,
                    "no_bid": 44.5,
                }
            ]
        }
        mock_request.return_value = mock_response

        result = await kalshi_client.get_markets()

        assert "markets" in result
        assert result["markets"][0]["ticker"] == "PRES-2024"

    @patch("infrastructure.kalshi.client.httpx.AsyncClient.request")
    async def test_get_markets_with_event_filter(
        self, mock_request: AsyncMock, kalshi_client: KalshiClient
    ) -> None:
        """Test markets retrieval filtered by event."""
        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"markets": []}
        mock_request.return_value = mock_response

        await kalshi_client.get_markets(event_ticker="PRES", status="open")

        call_kwargs = mock_request.call_args[1]
        assert call_kwargs["params"]["event_ticker"] == "PRES"
        assert call_kwargs["params"]["status"] == "open"

    @patch("infrastructure.kalshi.client.httpx.AsyncClient.request")
    async def test_get_market_by_ticker(
        self, mock_request: AsyncMock, kalshi_client: KalshiClient
    ) -> None:
        """Test single market retrieval."""
        ticker = "PRES-2024"
        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "ticker": ticker,
            "title": "Presidential Election 2024",
        }
        mock_request.return_value = mock_response

        result = await kalshi_client.get_market(ticker)

        assert result["ticker"] == ticker
        # Verify endpoint called correctly
        call_args = mock_request.call_args[0]
        assert f"/markets/{ticker}" in call_args

    @patch("infrastructure.kalshi.client.httpx.AsyncClient.request")
    async def test_get_orderbook(
        self, mock_request: AsyncMock, kalshi_client: KalshiClient
    ) -> None:
        """Test order book retrieval."""
        ticker = "PRES-2024"
        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "yes": [{"price": 55.5, "size": 100}],
            "no": [{"price": 44.5, "size": 150}],
        }
        mock_request.return_value = mock_response

        result = await kalshi_client.get_orderbook(ticker, depth=5)

        assert "yes" in result
        assert "no" in result
        # Verify depth parameter
        call_kwargs = mock_request.call_args[1]
        assert call_kwargs["params"]["depth"] == 5

    @patch("infrastructure.kalshi.client.httpx.AsyncClient.request")
    async def test_get_trades(self, mock_request: AsyncMock, kalshi_client: KalshiClient) -> None:
        """Test trades retrieval."""
        ticker = "PRES-2024"
        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "trades": [
                {"price": 55.0, "size": 10, "side": "yes"},
            ]
        }
        mock_request.return_value = mock_response

        result = await kalshi_client.get_trades(ticker, limit=50)

        assert "trades" in result
        call_kwargs = mock_request.call_args[1]
        assert call_kwargs["params"]["limit"] == 50

    @patch("infrastructure.kalshi.client.httpx.AsyncClient.request")
    async def test_http_error_handling(
        self, mock_request: AsyncMock, kalshi_client: KalshiClient
    ) -> None:
        """Test HTTP error handling."""
        mock_response = AsyncMock()
        mock_response.status_code = 404
        mock_response.text = "Not found"
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Not found", request=AsyncMock(), response=mock_response
        )
        mock_request.return_value = mock_response

        with pytest.raises(KalshiAPIError) as exc_info:
            await kalshi_client.get_market("NONEXISTENT")

        assert "404" in str(exc_info.value)

    @patch("infrastructure.kalshi.client.httpx.AsyncClient.request")
    async def test_request_error_handling(
        self, mock_request: AsyncMock, kalshi_client: KalshiClient
    ) -> None:
        """Test network request error handling."""
        mock_request.side_effect = httpx.RequestError("Connection failed")

        with pytest.raises(KalshiAPIError) as exc_info:
            await kalshi_client.get_events()

        assert "Request failed" in str(exc_info.value)

    @patch("infrastructure.kalshi.client.httpx.AsyncClient.request")
    async def test_retry_mechanism(
        self, mock_request: AsyncMock, kalshi_client: KalshiClient
    ) -> None:
        """Test retry logic on transient failures."""
        # First call fails, second succeeds
        mock_error_response = AsyncMock()
        mock_error_response.status_code = 500
        mock_error_response.text = "Server error"
        mock_error_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Server error", request=AsyncMock(), response=mock_error_response
        )

        mock_success_response = AsyncMock()
        mock_success_response.status_code = 200
        mock_success_response.json.return_value = {"events": []}

        mock_request.side_effect = [mock_error_response, mock_success_response]

        result = await kalshi_client.get_events()

        assert result == {"events": []}
        assert mock_request.call_count == 2

    @patch("infrastructure.kalshi.client.httpx.AsyncClient.request")
    async def test_max_retries_exceeded(
        self, mock_request: AsyncMock, kalshi_client: KalshiClient
    ) -> None:
        """Test behavior when max retries are exceeded."""
        mock_response = AsyncMock()
        mock_response.status_code = 500
        mock_response.text = "Server error"
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Server error", request=AsyncMock(), response=mock_response
        )
        mock_request.return_value = mock_response

        with pytest.raises(KalshiAPIError):
            await kalshi_client.get_events()

        # Should retry 3 times (initial + 2 retries)
        assert mock_request.call_count == 3

    async def test_client_configuration(self, kalshi_client: KalshiClient) -> None:
        """Test client is properly configured."""
        assert kalshi_client.base_url is not None
        assert kalshi_client.timeout > 0
        assert kalshi_client.max_retries >= 1
        assert kalshi_client.client is not None

    async def test_close_client(self, kalshi_client: KalshiClient) -> None:
        """Test client cleanup."""
        await kalshi_client.close()
        # After closing, client should be closed
        assert kalshi_client.client.is_closed
