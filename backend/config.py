from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional


class Settings(BaseSettings):
    database_url: str = "postgresql://ielts:ielts@localhost:5432/ielts"
    valid_passcode: str
    frontend_origin: str = "http://localhost:5173"
    cookie_secure: bool = False
    vertex_api_key: Optional[str] = None
    vertex_project: Optional[str] = None
    vertex_location: str = "us-central1"
    writing_grader_model: str = "gemini-2.5-pro"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
