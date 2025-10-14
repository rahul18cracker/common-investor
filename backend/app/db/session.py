from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.engine import Result
from sqlalchemy.pool import StaticPool
import os
import threading

# Get database URL from environment
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+psycopg2://ci:ci_pass@postgres:5432/ci_db")

# Check if we're in test mode
TESTING = os.getenv("TESTING", "0") == "1"

# Create engine with appropriate configuration
if TESTING and "sqlite" in DATABASE_URL:
    # Use StaticPool for SQLite in-memory testing to prevent connection issues
    engine: Engine = create_engine(
        DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        future=True
    )
else:
    # Production configuration
    engine: Engine = create_engine(DATABASE_URL, future=True)

# Thread-local storage for test session override
_test_session = threading.local()


def set_test_session(session):
    """Set a test session to use instead of creating new connections."""
    _test_session.value = session


def clear_test_session():
    """Clear the test session override."""
    _test_session.value = None


class AutoClosingResult:
    """Wrapper around SQLAlchemy Result that auto-closes cursor after consumption.
    
    This prevents SQLite 'cannot commit - SQL statements in progress' errors
    by ensuring cursors are closed immediately after fetching data.
    """
    
    def __init__(self, result: Result):
        self._result = result
        self._closed = False
    
    def first(self):
        """Fetch first row and close cursor."""
        try:
            row = self._result.first()
            return row
        finally:
            self._close()
    
    def all(self):
        """Fetch all rows and close cursor."""
        try:
            rows = self._result.all()
            return rows
        finally:
            self._close()
    
    def one(self):
        """Fetch exactly one row and close cursor."""
        try:
            row = self._result.one()
            return row
        finally:
            self._close()
    
    def one_or_none(self):
        """Fetch one row or None and close cursor."""
        try:
            row = self._result.one_or_none()
            return row
        finally:
            self._close()
    
    def scalar(self):
        """Fetch first column of first row and close cursor."""
        try:
            value = self._result.scalar()
            return value
        finally:
            self._close()
    
    def scalars(self):
        """Return scalars - note: caller must consume iterator."""
        return self._result.scalars()
    
    def fetchone(self):
        """Fetch one row and close cursor."""
        try:
            row = self._result.fetchone()
            return row
        finally:
            self._close()
    
    def fetchall(self):
        """Fetch all rows and close cursor."""
        try:
            rows = self._result.fetchall()
            return rows
        finally:
            self._close()
    
    def _close(self):
        """Close the underlying result cursor if not already closed."""
        if not self._closed:
            self._result.close()
            self._closed = True
    
    def close(self):
        """Explicitly close the cursor."""
        self._close()
    
    def __iter__(self):
        """Allow iteration - note: caller must close manually or consume fully."""
        return iter(self._result)


def execute(sql: str, **params):
    """
    Execute a SQL statement with the given parameters.

    In tests, this will use the thread-local test session if set,
    otherwise it creates a new connection from the engine.
    
    Returns an AutoClosingResult that automatically closes cursors
    after fetching data, preventing SQLite commit errors.
    """
    # Check if we have a test session set
    test_session = getattr(_test_session, 'value', None)
    if test_session is not None:
        # Use the test session directly - it handles its own transaction management
        result = test_session.execute(text(sql), params)
        # Wrap in AutoClosingResult to prevent "SQL statements in progress" errors
        wrapped_result = AutoClosingResult(result)
        # Flush AFTER wrapping to ensure cursor can be closed if needed
        # Note: flush() itself doesn't commit, but ensures writes are visible
        test_session.flush()
        return wrapped_result

    # Normal execution using engine
    # For non-test paths, execute in a transaction and immediately fetch results
    # to avoid SQLite cursor issues with commits
    with engine.begin() as conn:
        result = conn.execute(text(sql), params)
        # Immediately fetch all results to close the cursor before commit
        # This is necessary because SQLite cannot commit with open cursors
        if result.returns_rows:
            # For SELECT/RETURNING queries, fetch all rows immediately
            rows = result.fetchall()
            # Create a mock result that holds the fetched data
            class FetchedResult:
                def __init__(self, rows):
                    self._rows = rows
                    self._index = 0
                
                def first(self):
                    return self._rows[0] if self._rows else None
                
                def all(self):
                    return self._rows
                
                def one(self):
                    if len(self._rows) != 1:
                        raise Exception(f"Expected 1 row, got {len(self._rows)}")
                    return self._rows[0]
                
                def one_or_none(self):
                    if len(self._rows) == 0:
                        return None
                    if len(self._rows) > 1:
                        raise Exception(f"Expected at most 1 row, got {len(self._rows)}")
                    return self._rows[0]
                
                def scalar(self):
                    row = self.first()
                    return row[0] if row else None
                
                def fetchone(self):
                    return self.first()
                
                def fetchall(self):
                    return self._rows
                
                def __iter__(self):
                    return iter(self._rows)
                
                def close(self):
                    pass  # Already fetched, nothing to close
            
            return FetchedResult(rows)
        else:
            # For INSERT/UPDATE/DELETE without RETURNING, just return None
            return AutoClosingResult(result)