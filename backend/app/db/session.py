from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.pool import StaticPool
import os

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


def execute(sql: str, **params):
    """Execute a SQL statement with the given parameters."""
    with engine.begin() as conn:
        return conn.execute(text(sql), params)