from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional


class Settings(BaseSettings):
    database_url: str = "postgresql://ielts:ielts@localhost:5432/ielts"
    valid_passcode: str
    frontend_origin: str = "http://localhost:5173"
    frontend_origins: str = ""
    cookie_secure: bool = False
    cookie_samesite: str = "lax"
    gemini_api_key: Optional[str] = None
    vertex_api_key: Optional[str] = None
    vertex_project: Optional[str] = None
    vertex_location: str = "us-central1"
    writing_grader_model: str = "gemini-2.5-pro"

    @field_validator("cookie_samesite")
    @classmethod
    def validate_cookie_samesite(cls, value: str) -> str:
        normalized = value.lower()
        if normalized not in {"lax", "strict", "none"}:
            raise ValueError("COOKIE_SAMESITE must be one of: lax, strict, none")
        return normalized

    @property
    def allowed_frontend_origins(self) -> list[str]:
        configured = [
            origin.strip()
            for origin in self.frontend_origins.split(",")
            if origin.strip()
        ]
        if self.frontend_origin and self.frontend_origin not in configured:
            configured.append(self.frontend_origin)
        return configured

    @property
    def writing_grader_api_key(self) -> Optional[str]:
        return self.gemini_api_key or self.vertex_api_key

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
