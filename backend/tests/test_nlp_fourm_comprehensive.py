"""
Comprehensive unit tests for NLP/Four Ms SEC document parsing module.

This test suite aims for 90%+ coverage of app/nlp/fourm/sec_item1.py
Following industry best practices: AAA pattern, mocking external APIs, edge cases.
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from app.nlp.fourm.sec_item1 import (
    _company_submissions,
    _fetch_primary_doc,
    latest_10k_primary_doc,
    extract_item_1_business,
    get_meaning_item1,
)


# Mark all tests in this file as unit tests
pytestmark = pytest.mark.unit


class TestCompanySubmissions:
    """Test SEC company submissions API retrieval."""

    @patch("app.nlp.fourm.sec_item1.httpx.Client")
    def test_company_submissions_success(self, mock_client_class):
        """Test successful retrieval of company submissions data."""
        # Arrange
        mock_response = Mock()
        mock_response.json.return_value = {
            "cik": "0000789019",
            "entityType": "operating",
            "name": "MICROSOFT CORP",
            "filings": {"recent": {"form": ["10-K"], "accessionNumber": ["0001564590-23-012345"]}}
        }
        mock_client = MagicMock()
        mock_client.__enter__.return_value.get.return_value = mock_response
        mock_client_class.return_value = mock_client

        # Act
        result = _company_submissions("789019")

        # Assert
        assert result["cik"] == "0000789019"
        assert "filings" in result
        mock_client.__enter__.return_value.get.assert_called_once()

    @patch("app.nlp.fourm.sec_item1.httpx.Client")
    def test_company_submissions_formats_cik_correctly(self, mock_client_class):
        """Test that CIK is zero-padded to 10 digits in URL."""
        # Arrange
        mock_response = Mock()
        mock_response.json.return_value = {"cik": "0000000320"}
        mock_client = MagicMock()
        mock_client.__enter__.return_value.get.return_value = mock_response
        mock_client_class.return_value = mock_client

        # Act
        _company_submissions("320")  # Apple's CIK

        # Assert
        call_args = mock_client.__enter__.return_value.get.call_args
        assert "CIK0000000320.json" in call_args[0][0]

    @patch("app.nlp.fourm.sec_item1.httpx.Client")
    def test_company_submissions_http_error(self, mock_client_class):
        """Test handling of HTTP errors from SEC API."""
        # Arrange
        mock_response = Mock()
        mock_response.raise_for_status.side_effect = Exception("404 Not Found")
        mock_client = MagicMock()
        mock_client.__enter__.return_value.get.return_value = mock_response
        mock_client_class.return_value = mock_client

        # Act & Assert
        with pytest.raises(Exception, match="404 Not Found"):
            _company_submissions("999999")


class TestFetchPrimaryDoc:
    """Test fetching primary document HTML from SEC EDGAR."""

    @patch("app.nlp.fourm.sec_item1.httpx.Client")
    def test_fetch_primary_doc_success(self, mock_client_class):
        """Test successful document retrieval."""
        # Arrange
        mock_html = "<html><body>Item 1. Business</body></html>"
        mock_response = Mock()
        mock_response.text = mock_html
        mock_client = MagicMock()
        mock_client.__enter__.return_value.get.return_value = mock_response
        mock_client_class.return_value = mock_client

        # Act
        result = _fetch_primary_doc("789019", "0001564590230123456", "msft-10k_20230630.htm")

        # Assert
        assert result == mock_html
        mock_client.__enter__.return_value.get.assert_called_once()

    @patch("app.nlp.fourm.sec_item1.httpx.Client")
    def test_fetch_primary_doc_constructs_correct_url(self, mock_client_class):
        """Test that document URL is correctly constructed."""
        # Arrange
        mock_response = Mock()
        mock_response.text = "<html></html>"
        mock_client = MagicMock()
        mock_client.__enter__.return_value.get.return_value = mock_response
        mock_client_class.return_value = mock_client

        # Act
        _fetch_primary_doc("320", "0000320193220001234", "aapl-20220924.htm")

        # Assert
        call_args = mock_client.__enter__.return_value.get.call_args
        url = call_args[0][0]
        assert "/Archives/edgar/data/320/" in url
        assert "0000320193220001234" in url
        assert "aapl-20220924.htm" in url


class TestLatest10KPrimaryDoc:
    """Test finding the latest 10-K filing metadata."""

    @patch("app.nlp.fourm.sec_item1._company_submissions")
    def test_latest_10k_found(self, mock_submissions):
        """Test finding latest 10-K when it exists."""
        # Arrange
        mock_submissions.return_value = {
            "filings": {
                "recent": {
                    "form": ["8-K", "10-Q", "10-K", "8-K"],
                    "accessionNumber": ["0001-23-001", "0001-23-002", "0001-23-003", "0001-23-004"],
                    "primaryDocument": ["doc1.htm", "doc2.htm", "doc3.htm", "doc4.htm"]
                }
            }
        }

        # Act
        accession, doc = latest_10k_primary_doc("789019")

        # Assert
        assert accession == "0001-23-003"
        assert doc == "doc3.htm"

    @patch("app.nlp.fourm.sec_item1._company_submissions")
    def test_latest_10k_with_20f(self, mock_submissions):
        """Test finding 20-F (foreign issuer annual report) instead of 10-K."""
        # Arrange
        mock_submissions.return_value = {
            "filings": {
                "recent": {
                    "form": ["6-K", "20-F", "6-K"],
                    "accessionNumber": ["0001-23-001", "0001-23-002", "0001-23-003"],
                    "primaryDocument": ["doc1.htm", "doc2.htm", "doc3.htm"]
                }
            }
        }

        # Act
        accession, doc = latest_10k_primary_doc("789019")

        # Assert
        assert accession == "0001-23-002"
        assert doc == "doc2.htm"

    @patch("app.nlp.fourm.sec_item1._company_submissions")
    def test_latest_10k_not_found(self, mock_submissions):
        """Test when no 10-K or 20-F exists."""
        # Arrange
        mock_submissions.return_value = {
            "filings": {
                "recent": {
                    "form": ["8-K", "10-Q", "8-K"],
                    "accessionNumber": ["0001-23-001", "0001-23-002", "0001-23-003"],
                    "primaryDocument": ["doc1.htm", "doc2.htm", "doc3.htm"]
                }
            }
        }

        # Act
        accession, doc = latest_10k_primary_doc("789019")

        # Assert
        assert accession is None
        assert doc is None

    @patch("app.nlp.fourm.sec_item1._company_submissions")
    def test_latest_10k_empty_filings(self, mock_submissions):
        """Test when filings data is empty."""
        # Arrange
        mock_submissions.return_value = {
            "filings": {
                "recent": {
                    "form": [],
                    "accessionNumber": [],
                    "primaryDocument": []
                }
            }
        }

        # Act
        accession, doc = latest_10k_primary_doc("789019")

        # Assert
        assert accession is None
        assert doc is None

    @patch("app.nlp.fourm.sec_item1._company_submissions")
    def test_latest_10k_missing_recent_key(self, mock_submissions):
        """Test when 'recent' key is missing from filings."""
        # Arrange
        mock_submissions.return_value = {"filings": {}}

        # Act
        accession, doc = latest_10k_primary_doc("789019")

        # Assert
        assert accession is None
        assert doc is None


class TestExtractItem1Business:
    """Test extraction of Item 1 Business section from 10-K HTML."""

    def test_extract_item1_typical_case(self):
        """Test extraction with typical Item 1 structure."""
        # Arrange
        html = """
        <html><body>
        <p>Item 1. Business</p>
        <p>We are a technology company that develops software...</p>
        <p>Our products include Windows, Office, and Azure...</p>
        <p>Item 1A. Risk Factors</p>
        <p>We face various risks...</p>
        </body></html>
        """

        # Act
        result = extract_item_1_business(html)

        # Assert
        assert "Item 1" in result
        assert "Business" in result
        assert "technology company" in result
        assert "Item 1A" not in result or result.index("Item 1A") > result.index("Business")

    def test_extract_item1_with_item2_boundary(self):
        """Test extraction stops at Item 2 if Item 1A not present."""
        # Arrange
        html = """
        <html><body>
        <p>ITEM 1.  BUSINESS</p>
        <p>Company description here...</p>
        <p>Item 2. Properties</p>
        <p>Our offices are located...</p>
        </body></html>
        """

        # Act
        result = extract_item_1_business(html)

        # Assert
        assert "BUSINESS" in result
        assert "Company description" in result
        assert "Item 2" not in result

    def test_extract_item1_fallback_pattern(self):
        """Test fallback to broader pattern if specific 'Business' not found."""
        # Arrange
        html = """
        <html><body>
        <p>Item 1</p>
        <p>General description of the company...</p>
        <p>Item 1A. Risk Factors</p>
        </body></html>
        """

        # Act
        result = extract_item_1_business(html)

        # Assert
        assert "Item 1" in result
        assert "General description" in result

    def test_extract_item1_no_match_returns_truncated(self):
        """Test that first 20000 chars are returned when no Item 1 found."""
        # Arrange
        html = "<html><body>" + "A" * 30000 + "</body></html>"

        # Act
        result = extract_item_1_business(html)

        # Assert
        assert len(result) == 20000
        assert "A" in result

    def test_extract_item1_cleans_multiple_newlines(self):
        """Test that excessive newlines are collapsed."""
        # Arrange
        html = """
        <html><body>
        <p>Item 1. Business</p>


        <p>Content with gaps</p>



        <p>More content</p>
        <p>Item 1A</p>
        </body></html>
        """

        # Act
        result = extract_item_1_business(html)

        # Assert
        # Should not have triple newlines
        assert "\n\n\n" not in result

    def test_extract_item1_case_insensitive(self):
        """Test that pattern matching is case insensitive."""
        # Arrange
        html = """
        <html><body>
        <p>item 1. business</p>
        <p>Company info</p>
        <p>ITEM 1a. RISK FACTORS</p>
        </body></html>
        """

        # Act
        result = extract_item_1_business(html)

        # Assert
        assert "item 1" in result.lower()
        assert "Company info" in result


class TestGetMeaningItem1:
    """Test end-to-end retrieval of Item 1 for Meaning analysis."""

    @patch("app.nlp.fourm.sec_item1._fetch_primary_doc")
    @patch("app.nlp.fourm.sec_item1.latest_10k_primary_doc")
    def test_get_meaning_item1_success(self, mock_latest, mock_fetch):
        """Test successful end-to-end Item 1 retrieval."""
        # Arrange
        mock_latest.return_value = ("0001564590-23-012345", "msft-10k.htm")
        mock_fetch.return_value = """
        <html><body>
        <p>Item 1. Business</p>
        <p>We develop and license software, services, devices...</p>
        <p>Item 1A. Risk Factors</p>
        </body></html>
        """

        # Act
        result = get_meaning_item1("789019")

        # Assert
        assert result["status"] == "ok"
        assert result["accession"] == "0001564590-23-012345"
        assert result["doc"] == "msft-10k.htm"
        assert "item1_excerpt" in result
        assert "software" in result["item1_excerpt"]

    @patch("app.nlp.fourm.sec_item1.latest_10k_primary_doc")
    def test_get_meaning_item1_not_found(self, mock_latest):
        """Test when no 10-K filing is available."""
        # Arrange
        mock_latest.return_value = (None, None)

        # Act
        result = get_meaning_item1("999999")

        # Assert
        assert result["status"] == "not_found"
        assert "accession" not in result
        assert "item1_excerpt" not in result

    @patch("app.nlp.fourm.sec_item1._fetch_primary_doc")
    @patch("app.nlp.fourm.sec_item1.latest_10k_primary_doc")
    def test_get_meaning_item1_truncates_to_25000(self, mock_latest, mock_fetch):
        """Test that excerpt is truncated (extract_item_1_business returns max 20000, then truncated to 25000 if needed)."""
        # Arrange
        mock_latest.return_value = ("0001-23-001", "doc.htm")
        # Create HTML that will produce >25000 chars after extraction
        long_html = "<html><body>Item 1. Business\n" + "X" * 50000 + "\nItem 1A. Risk</body></html>"
        mock_fetch.return_value = long_html

        # Act
        result = get_meaning_item1("789019")

        # Assert: The excerpt is limited (first by extraction, then by final truncation)
        assert len(result["item1_excerpt"]) <= 25000
        assert "Item 1" in result["item1_excerpt"]

    @patch("app.nlp.fourm.sec_item1._fetch_primary_doc")
    @patch("app.nlp.fourm.sec_item1.latest_10k_primary_doc")
    def test_get_meaning_item1_removes_dashes_from_accession(self, mock_latest, mock_fetch):
        """Test that accession number dashes are removed for URL construction."""
        # Arrange
        mock_latest.return_value = ("0001-564-590-23-012345", "doc.htm")
        mock_fetch.return_value = "<html>Item 1. Business</html>"

        # Act
        get_meaning_item1("789019")

        # Assert
        # Verify _fetch_primary_doc was called with de-dashed accession
        mock_fetch.assert_called_once()
        call_args = mock_fetch.call_args[0]
        assert "-" not in call_args[1]  # Second arg is accession_no_nodash
        assert call_args[1] == "000156459023012345"
