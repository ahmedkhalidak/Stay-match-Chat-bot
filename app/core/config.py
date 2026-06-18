from urllib.parse import quote_plus

from pydantic_settings import BaseSettings


class Settings(BaseSettings):

    groq_api_key: str
    gemini_api_key: str | None = None
    recommendation_service_url: str | None = None

    db_host: str
    db_port: int
    db_name: str
    db_user: str
    db_password: str

    # Chatbot database (PostgreSQL - Neon) - optional for backward compatibility
    database_url: str | None = None

    # Legacy SQL Server variables (for backward compatibility)
    chatbot_db_host: str | None = None
    chatbot_db_port: int | None = None
    chatbot_db_name: str | None = None
    chatbot_db_user: str | None = None
    chatbot_db_password: str | None = None

    # JWT Authentication configuration
    jwt_secret: str = ""
    jwt_issuer: str = ""
    jwt_audience: str = ""

    # Gemini FAQ settings
    enable_gemini_faq: bool = True
    gemini_daily_limit: int = 1000
    gemini_cache_ttl_seconds: int = 3600
    gemini_max_tokens: int = 150
    gemini_timeout_seconds: int = 10
    max_question_length: int = 200

    @property
    def db_url(self):
        encoded_password = quote_plus(self.db_password)
        return (
            f"mssql+pyodbc://{self.db_user}:{encoded_password}"
            f"@{self.db_host}:{self.db_port}/{self.db_name}"
            f"?driver=FreeTDS&TDS_Version=8.0&Encrypt=no"
        )

    @property
    def chatbot_db_url(self):
        """Connection string for chatbot database (PostgreSQL - Neon)"""
        if self.database_url:
            return self.database_url
        
        # Fallback to legacy CHATBOT_DB_* variables if set
        if all([self.chatbot_db_host, self.chatbot_db_port, self.chatbot_db_name,
                self.chatbot_db_user, self.chatbot_db_password]):
            encoded_password = quote_plus(self.chatbot_db_password)
            return (
                f"postgresql+psycopg2://{self.chatbot_db_user}:{encoded_password}"
                f"@{self.chatbot_db_host}:{self.chatbot_db_port}/{self.chatbot_db_name}"
            )
        
        # Final fallback to main database
        return self.db_url

    class Config:

        env_file = ".env"

        extra = "ignore"


# Singleton instance
settings = Settings()
