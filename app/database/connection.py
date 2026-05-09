from sqlalchemy import create_engine

from app.core.config import Settings


settings = Settings()

engine = create_engine(
    settings.db_url,
    pool_pre_ping=True,
)