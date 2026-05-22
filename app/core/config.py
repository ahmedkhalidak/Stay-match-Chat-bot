from urllib.parse import quote_plus

from pydantic_settings import BaseSettings


class Settings(BaseSettings):

    groq_api_key: str

    db_host: str
    db_port: int
    db_name: str
    db_user: str
    db_password: str

    # Chatbot database (separate from backend)
    chatbot_db_host: str = None
    chatbot_db_port: int = None
    chatbot_db_name: str = None
    chatbot_db_user: str = None
    chatbot_db_password: str = None

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
        """Connection string for chatbot database (separate from backend)"""
        if not all([self.chatbot_db_host, self.chatbot_db_port, self.chatbot_db_name, 
                    self.chatbot_db_user, self.chatbot_db_password]):
            # Fallback to main database if chatbot DB not configured
            return self.db_url
        
        encoded_password = quote_plus(self.chatbot_db_password)
        return (
            f"mssql+pyodbc://{self.chatbot_db_user}:{encoded_password}"
            f"@{self.chatbot_db_host}:{self.chatbot_db_port}/{self.chatbot_db_name}"
            f"?driver=FreeTDS&TDS_Version=8.0&Encrypt=no"
        )

    class Config:

        env_file = ".env"

        extra = "ignore"