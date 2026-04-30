from __future__ import annotations

import time
from dataclasses import dataclass, field

import httpx


@dataclass
class FetchResult:
    """Result of fetching both agent bundle and item1 text."""

    agent_bundle: dict | None
    item1_text: str | None
    errors: list[str] = field(default_factory=list)
    fetch_duration_seconds: float = 0.0
    success: bool = False  # True only if both fetched without error


class DataFetcher:
    """Fetches quantitative data from the backend API for the research agent."""

    def __init__(self, base_url: str = "http://localhost:8080/api/v1"):
        """Initialize the fetcher with the backend base URL.

        Args:
            base_url: Base URL of the backend API (default: http://localhost:8080/api/v1)
        """
        self.base_url = base_url

    def fetch_agent_bundle(self, ticker: str) -> dict:
        """Fetch the agent bundle for a given ticker.

        Calls GET /company/{ticker}/agent-bundle and returns parsed JSON dict.

        Args:
            ticker: Stock ticker symbol

        Returns:
            Parsed JSON response as dict

        Raises:
            httpx.HTTPStatusError: On any HTTP error (4xx, 5xx)
            httpx.ConnectError: On connection failure
            httpx.TimeoutException: On timeout
        """
        url = f"{self.base_url}/company/{ticker}/agent-bundle"
        with httpx.Client(timeout=30) as client:
            response = client.get(url)
            response.raise_for_status()
            return response.json()

    def fetch_item1_text(self, ticker: str) -> str:
        """Fetch the Item 1 business description for a given ticker.

        Calls POST /company/{ticker}/fourm/meaning/refresh and extracts the
        "text" field from the JSON response.

        Args:
            ticker: Stock ticker symbol

        Returns:
            Item 1 text as string

        Raises:
            httpx.HTTPStatusError: On any HTTP error (4xx, 5xx)
            httpx.ConnectError: On connection failure
            httpx.TimeoutException: On timeout
        """
        url = f"{self.base_url}/company/{ticker}/fourm/meaning/refresh"
        with httpx.Client(timeout=30) as client:
            response = client.post(url)
            response.raise_for_status()
            data = response.json()
            return data.get("item1_excerpt") or data.get("text") or ""

    def fetch_all(self, ticker: str) -> FetchResult:
        """Fetch both agent bundle and Item 1 text, capturing all errors.

        Calls both fetch_agent_bundle and fetch_item1_text. All errors are captured
        in the FetchResult.errors list; methods themselves do not raise.
        success=True only if both succeeded and errors list is empty.

        Args:
            ticker: Stock ticker symbol

        Returns:
            FetchResult with both payloads and any errors encountered
        """
        start_time = time.time()
        result = FetchResult(
            agent_bundle=None,
            item1_text=None,
            errors=[],
            fetch_duration_seconds=0.0,
            success=False,
        )

        # Fetch agent bundle
        try:
            result.agent_bundle = self.fetch_agent_bundle(ticker)
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                result.errors.append(
                    f"Company {ticker} not ingested. Run POST /company/{ticker}/ingest first."
                )
            else:
                result.errors.append(
                    f"HTTP {e.response.status_code} from /company/{ticker}/agent-bundle"
                )
        except httpx.ConnectError:
            result.errors.append(
                f"Backend API not reachable at {self.base_url}. Is Docker running?"
            )
        except httpx.TimeoutException:
            result.errors.append(f"API timeout after 30s for {ticker}/agent-bundle")

        # Fetch item1 text
        try:
            result.item1_text = self.fetch_item1_text(ticker)
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                result.errors.append(
                    f"Company {ticker} not ingested. Run POST /company/{ticker}/ingest first."
                )
            else:
                result.errors.append(
                    f"HTTP {e.response.status_code} from /company/{ticker}/fourm/meaning/refresh"
                )
        except httpx.ConnectError:
            result.errors.append(
                f"Backend API not reachable at {self.base_url}. Is Docker running?"
            )
        except httpx.TimeoutException:
            result.errors.append(f"API timeout after 30s for {ticker}/fourm/meaning/refresh")

        result.fetch_duration_seconds = time.time() - start_time
        result.success = (
            result.agent_bundle is not None
            and result.item1_text is not None
            and len(result.errors) == 0
        )

        return result
