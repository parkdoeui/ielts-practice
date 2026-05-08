import pytest
from pydantic import ValidationError

from config import Settings


def test_allowed_frontend_origins_supports_comma_separated_values() -> None:
    settings = Settings(
        valid_passcode="test",
        frontend_origin="http://localhost:5173",
        frontend_origins="https://parkdoeui.github.io, https://example.com",
    )

    assert settings.allowed_frontend_origins == [
        "https://parkdoeui.github.io",
        "https://example.com",
        "http://localhost:5173",
    ]


def test_cookie_samesite_must_be_supported_value() -> None:
    with pytest.raises(ValidationError):
        Settings(valid_passcode="test", cookie_samesite="invalid")


def test_writing_grader_api_key_prefers_gemini_key() -> None:
    settings = Settings(
        valid_passcode="test",
        gemini_api_key="gemini-key",
        vertex_api_key="legacy-key",
    )

    assert settings.writing_grader_api_key == "gemini-key"


def test_writing_grader_api_key_falls_back_to_legacy_vertex_key() -> None:
    settings = Settings(valid_passcode="test", vertex_api_key="legacy-key")

    assert settings.writing_grader_api_key == "legacy-key"
