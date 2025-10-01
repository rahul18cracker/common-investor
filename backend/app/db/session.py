from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
import os
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+psycopg2://ci:ci_pass@postgres:5432/ci_db")
engine: Engine = create_engine(DATABASE_URL, future=True)
def execute(sql: str, **params):
    with engine.begin() as conn:
        return conn.execute(text(sql), params)