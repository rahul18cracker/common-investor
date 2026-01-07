"""
Comprehensive unit tests for app/core/utils.py and app/core/errors.py

Tests cover:
- get_company_cik: ticker to CIK resolution
- safe_float: None-safe float conversion
- safe_int: None-safe int conversion
- convert_row_to_dict: database row to typed dict conversion
- ApiError: custom exception class
- api_error_handler: FastAPI error handler
"""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from fastapi import HTTPException
from fastapi.responses import JSONResponse

from app.core.utils import (
    get_company_cik,
    safe_float,
    safe_int,
    convert_row_to_dict,
)
from app.core.errors import ApiError, api_error_handler


class TestGetCompanyCik:
    """Tests for get_company_cik function."""

    def test_get_company_cik_success(self):
        """Test successful CIK retrieval."""
        mock_result = MagicMock()
        mock_result.first.return_value = ["0000789019"]
        
        with patch("app.core.utils.execute", return_value=mock_result) as mock_execute:
            result = get_company_cik("MSFT")
            
            assert result == "0000789019"
            mock_execute.assert_called_once()

    def test_get_company_cik_case_insensitive(self):
        """Test ticker lookup is case-insensitive."""
        mock_result = MagicMock()
        mock_result.first.return_value = ["0000320193"]
        
        with patch("app.core.utils.execute", return_value=mock_result):
            result = get_company_cik("aapl")
            assert result == "0000320193"

    def test_get_company_cik_not_found(self):
        """Test raises HTTPException when company not found."""
        mock_result = MagicMock()
        mock_result.first.return_value = None
        
        with patch("app.core.utils.execute", return_value=mock_result):
            with pytest.raises(HTTPException) as exc_info:
                get_company_cik("INVALID")
            
            assert exc_info.value.status_code == 404
            assert "Company not found" in exc_info.value.detail

    def test_get_company_cik_uses_parameterized_query(self):
        """Test that query uses parameterized ticker."""
        mock_result = MagicMock()
        mock_result.first.return_value = ["0000123456"]
        
        with patch("app.core.utils.execute", return_value=mock_result) as mock_execute:
            get_company_cik("TEST")
            
            # Verify parameterized query is used (not string concatenation)
            call_args = mock_execute.call_args
            assert ":t" in call_args[0][0]  # Query contains parameter placeholder
            assert call_args[1]["t"] == "TEST"  # Parameter is passed


class TestSafeFloat:
    """Tests for safe_float function."""

    def test_safe_float_with_float(self):
        """Test conversion of float value."""
        assert safe_float(3.14) == 3.14

    def test_safe_float_with_int(self):
        """Test conversion of int to float."""
        assert safe_float(42) == 42.0
        assert isinstance(safe_float(42), float)

    def test_safe_float_with_string(self):
        """Test conversion of numeric string."""
        assert safe_float("3.14") == 3.14

    def test_safe_float_with_none(self):
        """Test returns None for None input."""
        assert safe_float(None) is None

    def test_safe_float_with_zero(self):
        """Test conversion of zero."""
        assert safe_float(0) == 0.0
        assert safe_float(0.0) == 0.0

    def test_safe_float_with_negative(self):
        """Test conversion of negative values."""
        assert safe_float(-123.45) == -123.45

    def test_safe_float_with_large_number(self):
        """Test conversion of large numbers."""
        assert safe_float(1e15) == 1e15

    def test_safe_float_with_small_number(self):
        """Test conversion of small decimal numbers."""
        assert abs(safe_float(0.0000001) - 0.0000001) < 1e-10


class TestSafeInt:
    """Tests for safe_int function."""

    def test_safe_int_with_int(self):
        """Test conversion of int value."""
        assert safe_int(42) == 42

    def test_safe_int_with_float(self):
        """Test conversion of float to int (truncates)."""
        assert safe_int(3.9) == 3
        assert isinstance(safe_int(3.9), int)

    def test_safe_int_with_string(self):
        """Test conversion of numeric string."""
        assert safe_int("42") == 42

    def test_safe_int_with_none(self):
        """Test returns None for None input."""
        assert safe_int(None) is None

    def test_safe_int_with_zero(self):
        """Test conversion of zero."""
        assert safe_int(0) == 0

    def test_safe_int_with_negative(self):
        """Test conversion of negative values."""
        assert safe_int(-123) == -123

    def test_safe_int_with_large_number(self):
        """Test conversion of large numbers."""
        assert safe_int(1000000000) == 1000000000


class TestConvertRowToDict:
    """Tests for convert_row_to_dict function."""

    def test_convert_row_basic(self):
        """Test basic row conversion."""
        row = (2023, 1000000.5, 50000)
        fields = ["fy", "revenue", "shares"]
        type_map = {"fy": int, "revenue": float, "shares": float}
        
        result = convert_row_to_dict(row, fields, type_map)
        
        assert result == {"fy": 2023, "revenue": 1000000.5, "shares": 50000.0}

    def test_convert_row_with_none_values(self):
        """Test row conversion with None values."""
        row = (2023, None, 50000)
        fields = ["fy", "revenue", "shares"]
        type_map = {"fy": int, "revenue": float, "shares": float}
        
        result = convert_row_to_dict(row, fields, type_map)
        
        assert result["fy"] == 2023
        assert result["revenue"] is None
        assert result["shares"] == 50000.0

    def test_convert_row_all_none(self):
        """Test row conversion with all None values."""
        row = (None, None, None)
        fields = ["a", "b", "c"]
        type_map = {"a": int, "b": float, "c": str}
        
        result = convert_row_to_dict(row, fields, type_map)
        
        assert result == {"a": None, "b": None, "c": None}

    def test_convert_row_string_type(self):
        """Test row conversion with string type."""
        row = ("AAPL", 2023, 150.0)
        fields = ["ticker", "year", "price"]
        type_map = {"ticker": str, "year": int, "price": float}
        
        result = convert_row_to_dict(row, fields, type_map)
        
        assert result == {"ticker": "AAPL", "year": 2023, "price": 150.0}

    def test_convert_row_empty(self):
        """Test conversion of empty row."""
        row = ()
        fields = []
        type_map = {}
        
        result = convert_row_to_dict(row, fields, type_map)
        
        assert result == {}

    def test_convert_row_preserves_order(self):
        """Test that field order is preserved."""
        row = (1, 2, 3, 4, 5)
        fields = ["a", "b", "c", "d", "e"]
        type_map = {"a": int, "b": int, "c": int, "d": int, "e": int}
        
        result = convert_row_to_dict(row, fields, type_map)
        
        assert list(result.keys()) == ["a", "b", "c", "d", "e"]
        assert list(result.values()) == [1, 2, 3, 4, 5]

    def test_convert_row_type_conversion(self):
        """Test that types are properly converted."""
        row = ("100", "3.14", 42)
        fields = ["int_val", "float_val", "str_val"]
        type_map = {"int_val": int, "float_val": float, "str_val": str}
        
        result = convert_row_to_dict(row, fields, type_map)
        
        assert result["int_val"] == 100
        assert isinstance(result["int_val"], int)
        assert result["float_val"] == 3.14
        assert isinstance(result["float_val"], float)
        assert result["str_val"] == "42"
        assert isinstance(result["str_val"], str)


class TestApiError:
    """Tests for ApiError exception class."""

    def test_api_error_creation(self):
        """Test ApiError can be created with status code and detail."""
        error = ApiError(status_code=400, detail="Bad request")
        
        assert error.status_code == 400
        assert error.detail == "Bad request"

    def test_api_error_is_exception(self):
        """Test ApiError is an Exception subclass."""
        error = ApiError(status_code=500, detail="Server error")
        
        assert isinstance(error, Exception)

    def test_api_error_message(self):
        """Test ApiError message is set to detail."""
        error = ApiError(status_code=404, detail="Not found")
        
        assert str(error) == "Not found"

    def test_api_error_can_be_raised(self):
        """Test ApiError can be raised and caught."""
        with pytest.raises(ApiError) as exc_info:
            raise ApiError(status_code=403, detail="Forbidden")
        
        assert exc_info.value.status_code == 403
        assert exc_info.value.detail == "Forbidden"

    def test_api_error_various_status_codes(self):
        """Test ApiError with various HTTP status codes."""
        codes = [400, 401, 403, 404, 422, 500, 502, 503]
        
        for code in codes:
            error = ApiError(status_code=code, detail=f"Error {code}")
            assert error.status_code == code


class TestApiErrorHandler:
    """Tests for api_error_handler function."""

    @pytest.mark.asyncio
    async def test_api_error_handler_returns_json_response(self):
        """Test handler returns JSONResponse."""
        request = MagicMock()
        error = ApiError(status_code=400, detail="Bad request")
        
        response = await api_error_handler(request, error)
        
        assert isinstance(response, JSONResponse)

    @pytest.mark.asyncio
    async def test_api_error_handler_status_code(self):
        """Test handler sets correct status code."""
        request = MagicMock()
        error = ApiError(status_code=404, detail="Not found")
        
        response = await api_error_handler(request, error)
        
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_api_error_handler_content(self):
        """Test handler sets correct content."""
        request = MagicMock()
        error = ApiError(status_code=422, detail="Validation error")
        
        response = await api_error_handler(request, error)
        
        # JSONResponse body is bytes, decode it
        import json
        body = json.loads(response.body.decode())
        assert body == {"detail": "Validation error"}

    @pytest.mark.asyncio
    async def test_api_error_handler_various_errors(self):
        """Test handler with various error types."""
        request = MagicMock()
        
        test_cases = [
            (400, "Bad request"),
            (401, "Unauthorized"),
            (403, "Forbidden"),
            (404, "Resource not found"),
            (500, "Internal server error"),
        ]
        
        for status_code, detail in test_cases:
            error = ApiError(status_code=status_code, detail=detail)
            response = await api_error_handler(request, error)
            
            assert response.status_code == status_code
            
            import json
            body = json.loads(response.body.decode())
            assert body["detail"] == detail
