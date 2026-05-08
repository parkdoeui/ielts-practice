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
