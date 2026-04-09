import os


class Settings:
    """Application settings from environment variables."""

    database_url: str
    redis_url: str
    sec_user_agent: str
    testing: bool
    auto_seed: bool
    log_level: str

    def __init__(self):
        self.database_url = os.getenv("DATABASE_URL", "postgresql+psycopg2://ci:ci_pass@postgres:5432/ci_db")
        self.redis_url = os.getenv("REDIS_URL", "redis://redis:6379/0")
        self.sec_user_agent = os.getenv("SEC_USER_AGENT", "CommonInvestor/1.0 dev@example.com")
        self.testing = os.getenv("TESTING", "0") == "1"
        self.auto_seed = os.getenv("AUTO_SEED", "true").lower() in ("true", "1", "yes")
        self.log_level = os.getenv("LOG_LEVEL", "INFO")


settings = Settings()
