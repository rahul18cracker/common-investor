"""
Integration tests for SEC Item 1 extraction module
"""
import pytest
from unittest.mock import patch, MagicMock
import httpx


class TestCompanySubmissions:
    """Tests for _company_submissions function"""
    
    def test_company_submissions_success(self):
        """Test successful company submissions fetch"""
        from app.nlp.fourm.sec_item1 import _company_submissions
        
        with patch('app.nlp.fourm.sec_item1.httpx.Client') as mock_client:
            mock_response = MagicMock()
            mock_response.json.return_value = {
                "cik": "0000320193",
                "filings": {
                    "recent": {
                        "form": ["10-K", "10-Q"],
                        "accessionNumber": ["0000320193-23-000001", "0000320193-23-000002"],
                        "primaryDocument": ["aapl-10k.htm", "aapl-10q.htm"]
                    }
                }
            }
            mock_client.return_value.__enter__.return_value.get.return_value = mock_response
            
            result = _company_submissions("0000320193")
            
            assert result["cik"] == "0000320193"
            assert "filings" in result
    
    def test_company_submissions_http_error(self):
        """Test company submissions with HTTP error"""
        from app.nlp.fourm.sec_item1 import _company_submissions
        
        with patch('app.nlp.fourm.sec_item1.httpx.Client') as mock_client:
            mock_response = MagicMock()
            mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
                "404 Not Found",
                request=MagicMock(),
                response=MagicMock(status_code=404)
            )
            mock_client.return_value.__enter__.return_value.get.return_value = mock_response
            
            with pytest.raises(httpx.HTTPStatusError):
                _company_submissions("0000000000")


class TestFetchPrimaryDoc:
    """Tests for _fetch_primary_doc function"""
    
    def test_fetch_primary_doc_success(self):
        """Test successful primary document fetch"""
        from app.nlp.fourm.sec_item1 import _fetch_primary_doc
        
        with patch('app.nlp.fourm.sec_item1.httpx.Client') as mock_client:
            mock_response = MagicMock()
            mock_response.text = "<html><body>10-K Content</body></html>"
            mock_client.return_value.__enter__.return_value.get.return_value = mock_response
            
            result = _fetch_primary_doc("0000320193", "0000320193230001", "aapl-10k.htm")
            
            assert "10-K Content" in result


class TestLatest10kPrimaryDoc:
    """Tests for latest_10k_primary_doc function"""
    
    def test_latest_10k_found(self):
        """Test finding latest 10-K"""
        from app.nlp.fourm.sec_item1 import latest_10k_primary_doc
        
        with patch('app.nlp.fourm.sec_item1._company_submissions') as mock_submissions:
            mock_submissions.return_value = {
                "filings": {
                    "recent": {
                        "form": ["10-Q", "10-K", "8-K"],
                        "accessionNumber": ["acc1", "acc2", "acc3"],
                        "primaryDocument": ["doc1.htm", "doc2.htm", "doc3.htm"]
                    }
                }
            }
            
            acc, doc = latest_10k_primary_doc("0000320193")
            
            assert acc == "acc2"
            assert doc == "doc2.htm"
    
    def test_latest_20f_found(self):
        """Test finding latest 20-F (foreign company)"""
        from app.nlp.fourm.sec_item1 import latest_10k_primary_doc
        
        with patch('app.nlp.fourm.sec_item1._company_submissions') as mock_submissions:
            mock_submissions.return_value = {
                "filings": {
                    "recent": {
                        "form": ["10-Q", "20-F", "8-K"],
                        "accessionNumber": ["acc1", "acc2", "acc3"],
                        "primaryDocument": ["doc1.htm", "doc2.htm", "doc3.htm"]
                    }
                }
            }
            
            acc, doc = latest_10k_primary_doc("0000320193")
            
            assert acc == "acc2"
            assert doc == "doc2.htm"
    
    def test_no_10k_found(self):
        """Test when no 10-K is found"""
        from app.nlp.fourm.sec_item1 import latest_10k_primary_doc
        
        with patch('app.nlp.fourm.sec_item1._company_submissions') as mock_submissions:
            mock_submissions.return_value = {
                "filings": {
                    "recent": {
                        "form": ["10-Q", "8-K"],
                        "accessionNumber": ["acc1", "acc2"],
                        "primaryDocument": ["doc1.htm", "doc2.htm"]
                    }
                }
            }
            
            acc, doc = latest_10k_primary_doc("0000320193")
            
            assert acc is None
            assert doc is None


class TestExtractItem1Business:
    """Tests for extract_item_1_business function"""
    
    def test_extract_item1_with_business_section(self):
        """Test extraction with clear Item 1 Business section"""
        from app.nlp.fourm.sec_item1 import extract_item_1_business
        
        html = """
        <html><body>
        <p>Table of Contents</p>
        <p>Item 1. Business</p>
        <p>We are a technology company that develops software.</p>
        <p>Our products include cloud services and devices.</p>
        <p>Item 1A. Risk Factors</p>
        <p>Risk content here</p>
        </body></html>
        """
        
        result = extract_item_1_business(html)
        
        assert "technology company" in result or "Item 1" in result
    
    def test_extract_item1_fallback_pattern(self):
        """Test extraction with alternative pattern"""
        from app.nlp.fourm.sec_item1 import extract_item_1_business
        
        html = """
        <html><body>
        <p>Item 1 Overview</p>
        <p>Company description here.</p>
        <p>Item 2. Properties</p>
        </body></html>
        """
        
        result = extract_item_1_business(html)
        
        assert len(result) > 0
    
    def test_extract_item1_no_match_returns_truncated(self):
        """Test extraction returns truncated content when no pattern matches"""
        from app.nlp.fourm.sec_item1 import extract_item_1_business
        
        html = """
        <html><body>
        <p>Some random content without Item 1 markers</p>
        <p>More content here</p>
        </body></html>
        """
        
        result = extract_item_1_business(html)
        
        # Should return truncated content (up to 20000 chars)
        assert len(result) > 0
        assert len(result) <= 20000


class TestGetMeaningItem1:
    """Tests for get_meaning_item1 function"""
    
    def test_get_meaning_item1_success(self):
        """Test successful meaning extraction"""
        from app.nlp.fourm.sec_item1 import get_meaning_item1
        
        with patch('app.nlp.fourm.sec_item1.latest_10k_primary_doc') as mock_latest, \
             patch('app.nlp.fourm.sec_item1._fetch_primary_doc') as mock_fetch:
            
            mock_latest.return_value = ("0000320193-23-000001", "aapl-10k.htm")
            mock_fetch.return_value = """
            <html><body>
            <p>Item 1. Business</p>
            <p>Apple Inc. designs and manufactures consumer electronics.</p>
            <p>Item 1A. Risk Factors</p>
            </body></html>
            """
            
            result = get_meaning_item1("0000320193")
            
            assert result["status"] == "ok"
            assert "accession" in result
            assert "doc" in result
            assert "item1_excerpt" in result
    
    def test_get_meaning_item1_not_found(self):
        """Test when no 10-K is found"""
        from app.nlp.fourm.sec_item1 import get_meaning_item1
        
        with patch('app.nlp.fourm.sec_item1.latest_10k_primary_doc') as mock_latest:
            mock_latest.return_value = (None, None)
            
            result = get_meaning_item1("0000000000")
            
            assert result["status"] == "not_found"
