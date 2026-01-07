"""Core utility functions for type conversions and common operations."""
from fastapi import HTTPException
from app.db.session import execute


def get_company_cik(ticker: str) -> str:
    """Resolve ticker to CIK or raise 404.
    
    Args:
        ticker: Company ticker symbol (case-insensitive)
        
    Returns:
        CIK string for the company
        
    Raises:
        HTTPException: 404 if company not found
        
    Example:
        >>> cik = get_company_cik("MSFT")
        >>> cik
        '0000789019'
    """
    row = execute(
        "SELECT cik FROM company WHERE upper(ticker)=upper(:t)", 
        t=ticker
    ).first()
    if not row:
        raise HTTPException(404, detail="Company not found. Ingest first.")
    return row[0]


def safe_float(value) -> float | None:
    """Convert value to float, returning None if value is None.
    
    Args:
        value: Value to convert (typically from database row)
        
    Returns:
        Float value or None if input is None
        
    Example:
        >>> safe_float(3.14)
        3.14
        >>> safe_float(None)
        None
        >>> safe_float("3.14")
        3.14
    """
    return float(value) if value is not None else None


def safe_int(value) -> int | None:
    """Convert value to int, returning None if value is None.
    
    Args:
        value: Value to convert (typically from database row)
        
    Returns:
        Integer value or None if input is None
        
    Example:
        >>> safe_int(42)
        42
        >>> safe_int(None)
        None
        >>> safe_int("42")
        42
    """
    return int(value) if value is not None else None


def convert_row_to_dict(row: tuple, fields: list[str], type_map: dict[str, type]) -> dict:
    """Convert database row tuple to typed dictionary with None-safe conversions.
    
    Args:
        row: Database row as tuple
        fields: List of field names matching row positions
        type_map: Dict mapping field names to conversion types (int, float, str)
    
    Returns:
        Dictionary with field names as keys and typed values (or None)
    
    Example:
        >>> row = (2023, 1000000.5, None, 50000)
        >>> fields = ['fy', 'revenue', 'ebit', 'shares']
        >>> type_map = {'fy': int, 'revenue': float, 'ebit': float, 'shares': float}
        >>> convert_row_to_dict(row, fields, type_map)
        {'fy': 2023, 'revenue': 1000000.5, 'ebit': None, 'shares': 50000.0}
    """
    result = {}
    for field, value in zip(fields, row):
        if value is None:
            result[field] = None
        else:
            result[field] = type_map[field](value)
    return result
