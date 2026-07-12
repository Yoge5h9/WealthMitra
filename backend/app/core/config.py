from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    llm_provider: str = "claude_cli"
    gemini_api_key: str | None = None
    gemini_api_key_2: str | None = None
    anthropic_api_key: str | None = None
    openai_api_key: str | None = None
    openai_base_url: str = "https://api.openai.com/v1"
    llm_model_complex: str = "gpt-5.4-mini"
    llm_model_simple: str = "gpt-5.4-nano"
    port: int = 8000

    @property
    def gemini_api_keys(self) -> list[str]:
        """All configured Gemini keys, primary first.

        GEMINI_API_KEY also accepts a comma-separated list; GEMINI_API_KEY_2
        is appended after. Extra keys are quota-exhaustion fallbacks.
        """
        keys: list[str] = []
        for raw in (self.gemini_api_key, self.gemini_api_key_2):
            if raw:
                keys.extend(k.strip() for k in raw.split(",") if k.strip())
        return keys

    @model_validator(mode="after")
    def _require_key_for_active_provider(self) -> "Settings":
        if self.llm_provider == "gemini" and not self.gemini_api_key:
            raise ValueError(
                "llm_provider is 'gemini' but gemini_api_key is not set "
                "(set GEMINI_API_KEY in the environment or .env)"
            )
        if self.llm_provider == "anthropic" and not self.anthropic_api_key:
            raise ValueError(
                "llm_provider is 'anthropic' but anthropic_api_key is not set "
                "(set ANTHROPIC_API_KEY in the environment or .env)"
            )
        if self.llm_provider == "openai_compatible" and not self.openai_api_key:
            raise ValueError(
                "llm_provider is 'openai_compatible' but openai_api_key is not set "
                "(set OPENAI_API_KEY in the environment or .env)"
            )
        return self


settings = Settings()
