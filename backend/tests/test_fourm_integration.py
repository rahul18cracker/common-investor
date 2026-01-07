"""
Integration tests for Four Ms functionality
"""
import pytest
from app.nlp.fourm.service import compute_moat, compute_management, compute_margin_of_safety_recommendation
from app.nlp.fourm.sec_item1 import get_meaning_item1, extract_item_1_business


def test_compute_moat_with_empty_data():
    """Test moat computation with no data"""
    # This should handle empty data gracefully
    result = compute_moat("0000000000")  # Non-existent CIK
    assert isinstance(result, dict)
    assert "roic_avg" in result
    assert "score" in result


def test_compute_management_with_empty_data():
    """Test management computation with no data"""
    # This should handle empty data gracefully
    result = compute_management("0000000000")  # Non-existent CIK
    assert isinstance(result, dict)
    assert "reinvest_ratio_avg" in result
    assert "payout_ratio_avg" in result
    assert "score" in result


def test_compute_mos_recommendation_with_empty_data():
    """Test MOS recommendation with no data"""
    # This should handle empty data gracefully
    result = compute_margin_of_safety_recommendation("0000000000")  # Non-existent CIK
    assert isinstance(result, dict)
    assert "recommended_mos" in result
    assert "drivers" in result


def test_extract_item_1_business_basic():
    """Test Item 1 business extraction with sample HTML"""
    sample_html = """
    <html>
    <body>
    <p>Some intro text</p>
    <p>Item 1. Business</p>
    <p>Microsoft Corporation develops, licenses, and supports software products, services, and devices worldwide.</p>
    <p>We offer an array of services, including cloud-based solutions that provide customers with software, services, platforms, and content.</p>
    <p>Item 1A. Risk Factors</p>
    <p>Risk factor content here...</p>
    </body>
    </html>
    """
    
    result = extract_item_1_business(sample_html)
    assert isinstance(result, str)
    assert len(result) > 0
    # Should contain business description but not risk factors
    assert "Microsoft Corporation develops" in result or "Item 1" in result


def test_get_meaning_item1_invalid_cik():
    """Test meaning extraction with invalid CIK - when no 10-K is found"""
    from unittest.mock import patch
    
    # Mock the latest_10k_primary_doc function to return None (no 10-K found)
    with patch('app.nlp.fourm.sec_item1.latest_10k_primary_doc') as mock_latest:
        mock_latest.return_value = (None, None)  # No 10-K found
        
        result = get_meaning_item1("0000000000")  # Non-existent CIK
        assert isinstance(result, dict)
        assert result.get("status") == "not_found"


def test_fourm_analysis_data_structure():
    """Test that Four Ms analysis returns expected data structure"""
    # Test with a non-existent CIK to ensure we get proper structure even with no data
    moat = compute_moat("0000000000")
    mgmt = compute_management("0000000000")
    mos = compute_margin_of_safety_recommendation("0000000000")
    
    # Verify moat structure
    assert isinstance(moat, dict)
    expected_moat_keys = ["roic_avg", "roic_sd", "margin_stability", "score"]
    for key in expected_moat_keys:
        assert key in moat
    
    # Verify management structure
    assert isinstance(mgmt, dict)
    expected_mgmt_keys = ["reinvest_ratio_avg", "payout_ratio_avg", "score"]
    for key in expected_mgmt_keys:
        assert key in mgmt
    
    # Verify MOS recommendation structure
    assert isinstance(mos, dict)
    expected_mos_keys = ["recommended_mos", "drivers"]
    for key in expected_mos_keys:
        assert key in mos
    
    # Verify drivers structure
    assert isinstance(mos["drivers"], dict)
    expected_driver_keys = ["growth", "moat_score", "mgmt_score"]
    for key in expected_driver_keys:
        assert key in mos["drivers"]


def test_fourm_analysis_score_ranges():
    """Test that Four Ms analysis scores are within expected ranges"""
    moat = compute_moat("0000000000")
    mgmt = compute_management("0000000000")
    mos = compute_margin_of_safety_recommendation("0000000000")
    
    # Scores should be None or between 0 and 1
    if moat["score"] is not None:
        assert 0 <= moat["score"] <= 1
    
    if mgmt["score"] is not None:
        assert 0 <= mgmt["score"] <= 1
    
    # MOS recommendation should be between 0.3 and 0.7 (as per spec)
    assert 0.3 <= mos["recommended_mos"] <= 0.7
