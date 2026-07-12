import pytest
from pydantic import ValidationError

from app.core.config import Settings


def test_defaults_require_no_key() -> None:
    settings = Settings(_env_file=None)

    assert settings.llm_provider == "claude_cli"
    assert settings.port == 8000
    assert settings.gemini_api_key is None
    assert settings.anthropic_api_key is None


def test_gemini_provider_without_key_raises() -> None:
    with pytest.raises(ValidationError, match="gemini_api_key"):
        Settings(_env_file=None, llm_provider="gemini")


def test_gemini_provider_with_key_is_valid() -> None:
    settings = Settings(_env_file=None, llm_provider="gemini", gemini_api_key="test-key")

    assert settings.gemini_api_key == "test-key"


def test_anthropic_provider_without_key_raises() -> None:
    with pytest.raises(ValidationError, match="anthropic_api_key"):
        Settings(_env_file=None, llm_provider="anthropic")


def test_anthropic_provider_with_key_is_valid() -> None:
    settings = Settings(_env_file=None, llm_provider="anthropic", anthropic_api_key="test-key")

    assert settings.anthropic_api_key == "test-key"
