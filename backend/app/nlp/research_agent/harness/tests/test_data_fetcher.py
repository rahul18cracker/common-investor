from __future__ import annotations

from unittest.mock import MagicMock, patch

import httpx
import pytest

from app.nlp.research_agent.harness.data_fetcher import DataFetcher, FetchResult


@pytest.mark.unit
class TestFetchAll:
    """Tests for fetch_all method."""

    def test_fetch_all_happy_path(self):
        """Happy path: both endpoints return valid data, success=True, errors=[]."""
        fetcher = DataFetcher(base_url="http://localhost:8080/api/v1")

        agent_bundle_data = {
            "ticker": "AAPL",
            "company_name": "Apple Inc.",
            "metrics": {"rev_cagr_5y": 0.08},
        }
        item1_text = "Apple Inc. is a technology company..."

        with patch("httpx.Client") as mock_client_class:
            mock_client = MagicMock()
            mock_client_class.return_value.__enter__.return_value = mock_client

            # First call to client.get (agent-bundle)
            mock_get_response = MagicMock()
            mock_get_response.json.return_value = agent_bundle_data

            # Second call to client.post (item1)
            mock_post_response = MagicMock()
            mock_post_response.json.return_value = {"text": item1_text}

            mock_client.get.return_value = mock_get_response
            mock_client.post.return_value = mock_post_response

            result = fetcher.fetch_all("AAPL")

            assert result.agent_bundle == agent_bundle_data
            assert result.item1_text == item1_text
            assert result.success is True
            assert result.errors == []
            assert result.fetch_duration_seconds > 0

    def test_fetch_all_agent_bundle_404(self):
        """Agent bundle 404 → error message contains "not ingested"."""
        fetcher = DataFetcher(base_url="http://localhost:8080/api/v1")

        with patch("httpx.Client") as mock_client_class:
            mock_client = MagicMock()
            mock_client_class.return_value.__enter__.return_value = mock_client

            # First call to client.get raises 404
            mock_response_404 = MagicMock()
            mock_response_404.status_code = 404
            error_404 = httpx.HTTPStatusError("404 Not Found", request=MagicMock(), response=mock_response_404)
            mock_client.get.side_effect = error_404

            # Second call to client.post (succeeds)
            mock_post_response = MagicMock()
            mock_post_response.json.return_value = {"text": "Some text"}
            mock_client.post.return_value = mock_post_response

            result = fetcher.fetch_all("UNKNOWN")

            assert result.agent_bundle is None
            assert result.item1_text == "Some text"
            assert result.success is False
            assert len(result.errors) == 1
            assert "not ingested" in result.errors[0]

    def test_fetch_all_item1_404(self):
        """Item1 404 → error message contains "not ingested"."""
        fetcher = DataFetcher(base_url="http://localhost:8080/api/v1")

        agent_bundle_data = {"ticker": "AAPL"}

        with patch("httpx.Client") as mock_client_class:
            mock_client = MagicMock()
            mock_client_class.return_value.__enter__.return_value = mock_client

            # First call to client.get (succeeds)
            mock_get_response = MagicMock()
            mock_get_response.json.return_value = agent_bundle_data
            mock_client.get.return_value = mock_get_response

            # Second call to client.post raises 404
            mock_response_404 = MagicMock()
            mock_response_404.status_code = 404
            error_404 = httpx.HTTPStatusError("404 Not Found", request=MagicMock(), response=mock_response_404)
            mock_client.post.side_effect = error_404

            result = fetcher.fetch_all("UNKNOWN")

            assert result.agent_bundle == agent_bundle_data
            assert result.item1_text is None
            assert result.success is False
            assert len(result.errors) == 1
            assert "not ingested" in result.errors[0]

    def test_fetch_all_connection_refused(self):
        """Connection refused → error message contains "not reachable"."""
        fetcher = DataFetcher(base_url="http://localhost:8080/api/v1")

        with patch("httpx.Client") as mock_client_class:
            mock_client = MagicMock()
            mock_client_class.return_value.__enter__.return_value = mock_client

            # Both calls raise ConnectError
            connect_error = httpx.ConnectError("Connection refused")
            mock_client.get.side_effect = connect_error
            mock_client.post.side_effect = connect_error

            result = fetcher.fetch_all("AAPL")

            assert result.agent_bundle is None
            assert result.item1_text is None
            assert result.success is False
            assert len(result.errors) == 2
            assert "not reachable" in result.errors[0]
            assert "not reachable" in result.errors[1]

    def test_fetch_all_timeout(self):
        """Timeout → error message contains "timeout"."""
        fetcher = DataFetcher(base_url="http://localhost:8080/api/v1")

        with patch("httpx.Client") as mock_client_class:
            mock_client = MagicMock()
            mock_client_class.return_value.__enter__.return_value = mock_client

            # Both calls raise TimeoutException
            timeout_error = httpx.TimeoutException("Request timed out")
            mock_client.get.side_effect = timeout_error
            mock_client.post.side_effect = timeout_error

            result = fetcher.fetch_all("AAPL")

            assert result.agent_bundle is None
            assert result.item1_text is None
            assert result.success is False
            assert len(result.errors) == 2
            assert "timeout" in result.errors[0]
            assert "timeout" in result.errors[1]

    def test_fetch_all_http_500(self):
        """Unexpected HTTP status (500) → error message contains "HTTP 500"."""
        fetcher = DataFetcher(base_url="http://localhost:8080/api/v1")

        with patch("httpx.Client") as mock_client_class:
            mock_client = MagicMock()
            mock_client_class.return_value.__enter__.return_value = mock_client

            # First call raises 500
            mock_response_500 = MagicMock()
            mock_response_500.status_code = 500
            error_500 = httpx.HTTPStatusError(
                "500 Internal Server Error",
                request=MagicMock(),
                response=mock_response_500,
            )
            mock_client.get.side_effect = error_500

            # Second call succeeds
            mock_post_response = MagicMock()
            mock_post_response.json.return_value = {"text": "Some text"}
            mock_client.post.return_value = mock_post_response

            result = fetcher.fetch_all("AAPL")

            assert result.agent_bundle is None
            assert result.item1_text == "Some text"
            assert result.success is False
            assert len(result.errors) == 1
            assert "HTTP 500" in result.errors[0]

    def test_fetch_all_one_failure(self):
        """fetch_all with one failure → success=False, errors non-empty."""
        fetcher = DataFetcher(base_url="http://localhost:8080/api/v1")

        agent_bundle_data = {"ticker": "AAPL"}

        with patch("httpx.Client") as mock_client_class:
            mock_client = MagicMock()
            mock_client_class.return_value.__enter__.return_value = mock_client

            # First call succeeds
            mock_get_response = MagicMock()
            mock_get_response.json.return_value = agent_bundle_data
            mock_client.get.return_value = mock_get_response

            # Second call fails
            connect_error = httpx.ConnectError("Connection refused")
            mock_client.post.side_effect = connect_error

            result = fetcher.fetch_all("AAPL")

            assert result.agent_bundle == agent_bundle_data
            assert result.item1_text is None
            assert result.success is False
            assert len(result.errors) > 0

    def test_fetch_all_duration_populated(self):
        """fetch_all duration field is populated (> 0)."""
        fetcher = DataFetcher(base_url="http://localhost:8080/api/v1")

        agent_bundle_data = {"ticker": "AAPL"}
        item1_text = "Some text"

        with patch("httpx.Client") as mock_client_class:
            mock_client = MagicMock()
            mock_client_class.return_value.__enter__.return_value = mock_client

            mock_get_response = MagicMock()
            mock_get_response.json.return_value = agent_bundle_data
            mock_client.get.return_value = mock_get_response

            mock_post_response = MagicMock()
            mock_post_response.json.return_value = {"text": item1_text}
            mock_client.post.return_value = mock_post_response

            result = fetcher.fetch_all("AAPL")

            assert result.fetch_duration_seconds > 0


@pytest.mark.unit
class TestFetchAgentBundle:
    """Tests for fetch_agent_bundle method."""

    def test_fetch_agent_bundle_returns_dict(self):
        """fetch_agent_bundle returns a dict (not a string)."""
        fetcher = DataFetcher(base_url="http://localhost:8080/api/v1")

        agent_bundle_data = {
            "ticker": "AAPL",
            "company_name": "Apple Inc.",
            "metrics": {"rev_cagr_5y": 0.08},
        }

        with patch("httpx.Client") as mock_client_class:
            mock_client = MagicMock()
            mock_client_class.return_value.__enter__.return_value = mock_client

            mock_response = MagicMock()
            mock_response.json.return_value = agent_bundle_data
            mock_client.get.return_value = mock_response

            result = fetcher.fetch_agent_bundle("AAPL")

            assert isinstance(result, dict)
            assert result == agent_bundle_data


@pytest.mark.unit
class TestFetchItem1Text:
    """Tests for fetch_item1_text method."""

    def test_fetch_item1_text_returns_string(self):
        """fetch_item1_text returns a string (not a dict)."""
        fetcher = DataFetcher(base_url="http://localhost:8080/api/v1")

        item1_text = "Apple Inc. is a technology company..."

        with patch("httpx.Client") as mock_client_class:
            mock_client = MagicMock()
            mock_client_class.return_value.__enter__.return_value = mock_client

            mock_response = MagicMock()
            mock_response.json.return_value = {"text": item1_text}
            mock_client.post.return_value = mock_response

            result = fetcher.fetch_item1_text("AAPL")

            assert isinstance(result, str)
            assert result == item1_text
