from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional


class Settings(BaseSettings):
    database_url: str = "postgresql://ielts:ielts@localhost:5432/ielts"
    valid_passcode: str
    frontend_origin: str = "http://localhost:5173"
    frontend_origins: str = "http://localhost:5174"
    cookie_secure: bool = False
    cookie_samesite: str = "lax"
    gemini_api_key: Optional[str] = None
    vertex_api_key: Optional[str] = None
    gcp_project: Optional[str] = None
    gcp_location: Optional[str] = None
    gcp_credentials_json: Optional[str] = None
    vertex_credentials_json: Optional[str] = None
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

    @property
    def effective_vertex_project(self) -> Optional[str]:
        return self.vertex_project or self.gcp_project

    @property
    def effective_vertex_location(self) -> str:
        return self.gcp_location or self.vertex_location

    @property
    def effective_vertex_credentials_json(self) -> Optional[str]:
        return self.vertex_credentials_json or self.gcp_credentials_json

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
