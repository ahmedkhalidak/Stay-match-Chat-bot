from sqlalchemy import create_engine, text

from app.core.config import Settings
from app.utils.logger import debug_log


settings = Settings()

# SQL Server Engine for Property Search
engine = create_engine(
    settings.db_url,
    pool_pre_ping=True,
    echo=False,
    connect_args={"trustservercertificate": "yes"}
)

# Log property database connection
try:
    with engine.connect() as conn:
        conn.execute(text("SELECT 1"))
        debug_log("PROPERTY_DB_CONNECTED", f"SQL Server - Host: {settings.db_host}, Database: {settings.db_name}")
except Exception as e:
    debug_log("PROPERTY_DB_ERROR", f"Failed to connect: {str(e)}")