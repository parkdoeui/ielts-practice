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


def test_allowed_frontend_origins_include_vite_fallback_port_by_default() -> None:
    settings = Settings(valid_passcode="test")

    assert "http://localhost:5173" in settings.allowed_frontend_origins
    assert "http://localhost:5174" in settings.allowed_frontend_origins


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


def test_effective_vertex_settings_support_fin_agent_gcp_names(monkeypatch) -> None:
    monkeypatch.delenv("VERTEX_PROJECT", raising=False)
    monkeypatch.delenv("VERTEX_CREDENTIALS_JSON", raising=False)
    settings = Settings(
        _env_file=None,
        valid_passcode="test",
        gcp_project="fin-agent-project",
        gcp_location="us-east5",
        gcp_credentials_json='{"type":"service_account"}',
    )

    assert settings.effective_vertex_project == "fin-agent-project"
    assert settings.effective_vertex_location == "us-east5"
    assert settings.effective_vertex_credentials_json == '{"type":"service_account"}'


def test_effective_vertex_settings_prefer_vertex_names_over_gcp_aliases() -> None:
    settings = Settings(
        _env_file=None,
        valid_passcode="test",
        vertex_project="vertex-project",
        gcp_project="gcp-project",
        vertex_credentials_json='{"source":"vertex"}',
        gcp_credentials_json='{"source":"gcp"}',
    )

    assert settings.effective_vertex_project == "vertex-project"
    assert settings.effective_vertex_credentials_json == '{"source":"vertex"}'
