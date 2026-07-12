import os
import subprocess
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
_PROVIDER_ENV_KEYS = ("LLM_PROVIDER", "GEMINI_API_KEY", "ANTHROPIC_API_KEY")


def _import_app_main(extra_env: dict[str, str]) -> subprocess.CompletedProcess[str]:
    env = {k: v for k, v in os.environ.items() if k not in _PROVIDER_ENV_KEYS}
    env["PYTHONPATH"] = str(BACKEND_DIR)
    env.update(extra_env)
    return subprocess.run(
        [sys.executable, "-c", "import app.main"],
        env=env,
        capture_output=True,
        text=True,
    )


def test_app_import_fails_fast_for_gemini_without_key() -> None:
    result = _import_app_main({"LLM_PROVIDER": "gemini"})

    assert result.returncode != 0
    assert "gemini_api_key is not set" in result.stderr


def test_app_import_fails_fast_for_anthropic_without_key() -> None:
    result = _import_app_main({"LLM_PROVIDER": "anthropic"})

    assert result.returncode != 0
    assert "anthropic_api_key is not set" in result.stderr


def test_app_import_succeeds_for_claude_cli_default() -> None:
    result = _import_app_main({})

    assert result.returncode == 0, result.stderr


def test_app_import_succeeds_for_gemini_with_key() -> None:
    result = _import_app_main({"LLM_PROVIDER": "gemini", "GEMINI_API_KEY": "test-key"})

    assert result.returncode == 0, result.stderr
