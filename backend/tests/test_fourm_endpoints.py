"""
Test cases for Four Ms API endpoints
"""
import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_fourm_analysis_endpoint_company_not_found():
    """Test Four Ms analysis endpoint when company is not found"""
    with patch('app.api.v1.routes.execute') as mock_execute:
        mock_execute.return_value.first.return_value = None
        
        response = client.get("/api/v1/company/INVALID/fourm")
        assert response.status_code == 404
        assert "Company not found" in response.json()["detail"]


def test_fourm_analysis_endpoint_success():
    """Test Four Ms analysis endpoint with successful response"""
    with patch('app.api.v1.routes.get_company_cik') as mock_cik, \
         patch('app.api.v1.routes.compute_moat') as mock_moat, \
         patch('app.api.v1.routes.compute_management') as mock_mgmt, \
         patch('app.api.v1.routes.compute_margin_of_safety_recommendation') as mock_mos:
        
        # Mock CIK lookup
        mock_cik.return_value = "0000123456"
        
        # Mock analysis functions
        mock_moat.return_value = {"roic_avg": 0.15, "score": 0.8}
        mock_mgmt.return_value = {"reinvest_ratio_avg": 0.4, "score": 0.7}
        mock_mos.return_value = {"recommended_mos": 0.5}
        
        response = client.get("/api/v1/company/MSFT/fourm")
        assert response.status_code == 200
        
        data = response.json()
        assert "moat" in data
        assert "management" in data
        assert "mos_recommendation" in data
        assert "cik" in data
        assert data["cik"] == "0000123456"


def test_meaning_refresh_endpoint_company_not_found():
    """Test meaning refresh endpoint when company is not found"""
    with patch('app.api.v1.routes.execute') as mock_execute:
        mock_execute.return_value.first.return_value = None
        
        response = client.post("/api/v1/company/INVALID/fourm/meaning/refresh")
        assert response.status_code == 404
        assert "Company not found" in response.json()["detail"]


def test_meaning_refresh_endpoint_no_filing():
    """Test meaning refresh endpoint when no 10-K filing is found"""
    with patch('app.api.v1.routes.get_company_cik') as mock_cik, \
         patch('app.api.v1.routes.get_meaning_item1') as mock_meaning:
        
        # Mock CIK lookup
        mock_cik.return_value = "0000123456"
        
        # Mock no filing found
        mock_meaning.return_value = {"status": "not_found"}
        
        response = client.post("/api/v1/company/MSFT/fourm/meaning/refresh")
        assert response.status_code == 404
        assert "No 10-K filing found" in response.json()["detail"]


def test_meaning_refresh_endpoint_success():
    """Test meaning refresh endpoint with successful extraction"""
    with patch('app.api.v1.routes.get_company_cik') as mock_cik, \
         patch('app.api.v1.routes.get_meaning_item1') as mock_meaning, \
         patch('app.api.v1.routes.execute') as mock_execute:
        
        # Mock CIK lookup
        mock_cik.return_value = "0000123456"
        
        # Mock database response for existing note check
        mock_execute.return_value.first.return_value = None  # No existing meaning note
        
        # Mock successful meaning extraction
        mock_meaning.return_value = {
            "status": "ok",
            "accession": "0000123456-23-000001",
            "doc": "msft-10k_20231231.htm",
            "item1_excerpt": "Microsoft Corporation develops and licenses software..."
        }
        
        response = client.post("/api/v1/company/MSFT/fourm/meaning/refresh")
        assert response.status_code == 200
        
        data = response.json()
        assert data["status"] == "ok"
        assert "item1_excerpt" in data
        assert "Microsoft Corporation" in data["item1_excerpt"]


def test_meaning_refresh_endpoint_existing_recent_note():
    """Test meaning refresh endpoint when recent note already exists"""
    with patch('app.api.v1.routes.get_company_cik') as mock_cik, \
         patch('app.api.v1.routes.get_meaning_item1') as mock_meaning, \
         patch('app.api.v1.routes.execute') as mock_execute:
        
        # Mock CIK lookup
        mock_cik.return_value = "0000123456"
        
        # Mock database response - existing meaning note found
        mock_execute.return_value.first.return_value = [1]  # Existing meaning note found
        
        # Mock successful meaning extraction
        mock_meaning.return_value = {
            "status": "ok",
            "accession": "0000123456-23-000001",
            "doc": "msft-10k_20231231.htm",
            "item1_excerpt": "Microsoft Corporation develops and licenses software..."
        }
        
        response = client.post("/api/v1/company/MSFT/fourm/meaning/refresh")
        assert response.status_code == 200
        
        data = response.json()
        assert data["status"] == "ok"
        
        # Verify that INSERT was not called (only 1 execute call: existing check)
        assert mock_execute.call_count == 1
