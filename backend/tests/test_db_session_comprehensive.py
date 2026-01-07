"""
Comprehensive unit tests for DB session module.

Tests engine configuration, test session management, result wrappers, and execute function.
"""
import pytest
from unittest.mock import patch, MagicMock, PropertyMock
from sqlalchemy.engine import Result
from sqlalchemy.pool import StaticPool


pytestmark = pytest.mark.unit


class TestEngineConfiguration:
    """Test database engine configuration."""

    def test_engine_exists(self):
        """Test that engine is created on module import."""
        from app.db.session import engine
        assert engine is not None

    def test_database_url_from_env(self):
        """Test DATABASE_URL is read from environment."""
        from app.db.session import DATABASE_URL
        assert DATABASE_URL is not None
        assert isinstance(DATABASE_URL, str)


class TestSessionManagement:
    """Test thread-local test session management."""

    def test_set_and_clear_test_session(self):
        """Test setting and clearing test session."""
        from app.db.session import set_test_session, clear_test_session, _test_session
        
        mock_session = MagicMock()
        set_test_session(mock_session)
        assert hasattr(_test_session, 'value')
        assert _test_session.value == mock_session
        
        clear_test_session()
        assert _test_session.value is None


class TestResultWrapper:
    """Test ResultWrapper wrapper class."""

    def setup_method(self):
        """Set up test fixtures."""
        self.mock_result = MagicMock(spec=Result)
        from app.db.session import ResultWrapper
        self.wrapper = ResultWrapper(self.mock_result, is_fetched=False)

    def test_first_closes_cursor(self):
        """Test that first() closes cursor after fetching."""
        self.mock_result.first.return_value = ("row1",)
        
        result = self.wrapper.first()
        
        assert result == ("row1",)
        self.mock_result.close.assert_called_once()

    def test_all_closes_cursor(self):
        """Test that all() closes cursor after fetching."""
        self.mock_result.all.return_value = [("row1",), ("row2",)]
        
        result = self.wrapper.all()
        
        assert len(result) == 2
        self.mock_result.close.assert_called_once()

    def test_one_closes_cursor(self):
        """Test that one() closes cursor after fetching."""
        self.mock_result.one.return_value = ("row1",)
        
        result = self.wrapper.one()
        
        assert result == ("row1",)
        self.mock_result.close.assert_called_once()

    def test_one_or_none_closes_cursor(self):
        """Test that one_or_none() closes cursor after fetching."""
        self.mock_result.one_or_none.return_value = ("row1",)
        
        result = self.wrapper.one_or_none()
        
        assert result == ("row1",)
        self.mock_result.close.assert_called_once()

    def test_scalar_closes_cursor(self):
        """Test that scalar() closes cursor after fetching."""
        self.mock_result.scalar.return_value = 42
        
        result = self.wrapper.scalar()
        
        assert result == 42
        self.mock_result.close.assert_called_once()

    def test_scalars_returns_without_closing(self):
        """Test that scalars() returns iterator without closing."""
        mock_scalars = MagicMock()
        self.mock_result.scalars.return_value = mock_scalars
        
        result = self.wrapper.scalars()
        
        assert result == mock_scalars
        self.mock_result.close.assert_not_called()

    def test_fetchone_closes_cursor(self):
        """Test that fetchone() closes cursor after fetching."""
        self.mock_result.first.return_value = ("row1",)
        
        result = self.wrapper.fetchone()
        
        assert result == ("row1",)
        self.mock_result.close.assert_called_once()

    def test_fetchall_closes_cursor(self):
        """Test that fetchall() closes cursor after fetching."""
        self.mock_result.fetchall.return_value = [("row1",), ("row2",)]
        
        result = self.wrapper.fetchall()
        
        assert len(result) == 2
        self.mock_result.close.assert_called_once()

    def test_close_explicitly(self):
        """Test explicit close() call."""
        self.wrapper.close()
        self.mock_result.close.assert_called_once()

    def test_close_idempotent(self):
        """Test that multiple close() calls don't error."""
        self.wrapper.close()
        self.wrapper.close()
        self.mock_result.close.assert_called_once()

    def test_iter_returns_iterator(self):
        """Test that __iter__ returns iterator."""
        mock_iter = iter([("row1",), ("row2",)])
        self.mock_result.__iter__.return_value = mock_iter
        
        result = iter(self.wrapper)
        
        assert result == mock_iter


class TestExecuteWithTestSession:
    """Test execute() function with test session."""

    def test_execute_with_test_session(self):
        """Test execute using thread-local test session."""
        from app.db.session import execute, set_test_session, clear_test_session
        
        mock_session = MagicMock()
        mock_result = MagicMock(spec=Result)
        mock_session.execute.return_value = mock_result
        
        set_test_session(mock_session)
        try:
            result = execute("SELECT * FROM company")
            
            mock_session.execute.assert_called_once()
            mock_session.flush.assert_called_once()
        finally:
            clear_test_session()

    def test_execute_with_params(self):
        """Test execute with parameters."""
        from app.db.session import execute, set_test_session, clear_test_session
        from sqlalchemy import text
        
        mock_session = MagicMock()
        mock_result = MagicMock(spec=Result)
        mock_session.execute.return_value = mock_result
        
        set_test_session(mock_session)
        try:
            execute("SELECT * FROM company WHERE ticker=:t", t="MSFT")
            
            # Verify execute was called
            assert mock_session.execute.called
            # Verify it was called with text() and params
            call_args = mock_session.execute.call_args
            assert call_args[0][0].text == "SELECT * FROM company WHERE ticker=:t"
            assert call_args[0][1] == {"t": "MSFT"}
        finally:
            clear_test_session()
