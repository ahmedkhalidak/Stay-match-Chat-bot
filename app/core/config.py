from urllib.parse import quote_plus

from pydantic_settings import BaseSettings


class Settings(BaseSettings):

    groq_api_key: str

    db_host: str
    db_port: int
    db_name: str
    db_user: str
    db_password: str

    @property
    def db_url(self):
        encoded_password = quote_plus(self.db_password)
        return (
            f"mssql+pyodbc://{self.db_user}:{encoded_password}"
            f"@{self.db_host}:{self.db_port}/{self.db_name}"
            f"?driver=FreeTDS&TDS_Version=8.0&Encrypt=no"
        )

    class Config:

        env_file = ".env"

        extra = "ignore"