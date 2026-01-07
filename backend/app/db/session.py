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


class ResultWrapper:
    """Unified wrapper for SQLAlchemy Result or pre-fetched rows.
    
    Handles two scenarios:
    1. Live Result (is_fetched=False): Wraps SQLAlchemy Result, auto-closes cursor after operations
    2. Pre-fetched data (is_fetched=True): Wraps already-fetched rows, no cursor management needed
    
    This prevents SQLite 'cannot commit - SQL statements in progress' errors
    by ensuring cursors are closed immediately after fetching data.
    """
    
    def __init__(self, data, is_fetched=False):
        """Initialize wrapper.
        
        Args:
            data: Either a SQLAlchemy Result object or a list of pre-fetched rows
            is_fetched: True if data is pre-fetched rows, False if it's a live Result
        """
        self._is_fetched = is_fetched
        if is_fetched:
            self._rows = data
        else:
            self._result = data
            self._closed = False
    
    def first(self):
        """Fetch first row."""
        if self._is_fetched:
            return self._rows[0] if self._rows else None
        try:
            row = self._result.first()
            return row
        finally:
            self._close()
    
    def all(self):
        """Fetch all rows."""
        if self._is_fetched:
            return self._rows
        try:
            rows = self._result.all()
            return rows
        finally:
            self._close()
    
    def one(self):
        """Fetch exactly one row."""
        if self._is_fetched:
            if len(self._rows) != 1:
                raise Exception(f"Expected 1 row, got {len(self._rows)}")
            return self._rows[0]
        try:
            row = self._result.one()
            return row
        finally:
            self._close()
    
    def one_or_none(self):
        """Fetch one row or None."""
        if self._is_fetched:
            if len(self._rows) == 0:
                return None
            if len(self._rows) > 1:
                raise Exception(f"Expected at most 1 row, got {len(self._rows)}")
            return self._rows[0]
        try:
            row = self._result.one_or_none()
            return row
        finally:
            self._close()
    
    def scalar(self):
        """Fetch first column of first row."""
        if self._is_fetched:
            row = self.first()
            return row[0] if row else None
        try:
            value = self._result.scalar()
            return value
        finally:
            self._close()
    
    def scalars(self):
        """Return scalars - only valid for live Result."""
        if self._is_fetched:
            raise NotImplementedError("scalars() not supported for pre-fetched data")
        return self._result.scalars()
    
    def fetchone(self):
        """Fetch one row."""
        return self.first()
    
    def fetchall(self):
        """Fetch all rows."""
        if self._is_fetched:
            return self._rows
        try:
            rows = self._result.fetchall()
            return rows
        finally:
            self._close()
    
    def _close(self):
        """Close the underlying result cursor if not already closed."""
        if not self._is_fetched and not self._closed:
            self._result.close()
            self._closed = True
    
    def close(self):
        """Explicitly close the cursor."""
        self._close()
    
    def __iter__(self):
        """Allow iteration."""
        if self._is_fetched:
            return iter(self._rows)
        return iter(self._result)


def execute(sql: str, **params):
    """
    Execute a SQL statement with the given parameters.

    In tests, this will use the thread-local test session if set,
    otherwise it creates a new connection from the engine.
    
    Returns a ResultWrapper that automatically closes cursors
    after fetching data, preventing SQLite commit errors.
    """
    # Check if we have a test session set
    test_session = getattr(_test_session, 'value', None)
    if test_session is not None:
        # Use the test session directly - it handles its own transaction management
        result = test_session.execute(text(sql), params)
        # Wrap in ResultWrapper to prevent "SQL statements in progress" errors
        wrapped_result = ResultWrapper(result, is_fetched=False)
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
            # Return wrapper with pre-fetched data
            return ResultWrapper(rows, is_fetched=True)
        else:
            # For INSERT/UPDATE/DELETE without RETURNING, return live result wrapper
            return ResultWrapper(result, is_fetched=False)