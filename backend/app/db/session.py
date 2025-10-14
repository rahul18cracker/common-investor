from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
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


def execute(sql: str, **params):
    """
    Execute a SQL statement with the given parameters.

    In tests, this will use the thread-local test session if set,
    otherwise it creates a new connection from the engine.
    """
    # Check if we have a test session set
    test_session = getattr(_test_session, 'value', None)
    if test_session is not None:
        # Use the test session directly - it handles its own transaction management
        result = test_session.execute(text(sql), params)
        # Flush to ensure writes are visible within the test
        test_session.flush()
        return result

    # Normal execution using engine
    with engine.begin() as conn:
        return conn.execute(text(sql), params)