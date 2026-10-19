
import pytest
from unittest.mock import Mock

from google.genai import errors

from backend.app.services.llm.gemini_provider import (
    GeminiProvider,
    GeminiQuotaExceededError,
)


def test_gemini_provider_requires_api_key(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)

    with pytest.raises(ValueError, match="GEMINI_API_KEY"):
        GeminiProvider()


def test_gemini_provider_returns_response(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")

    provider = GeminiProvider()
    provider.client = Mock()
    provider.client.models.generate_content.return_value = Mock(
        text="  HSIF test successful.  "
    )

    assert provider.generate("Test prompt") == "HSIF test successful."
    provider.client.models.generate_content.assert_called_once()


def test_gemini_provider_rejects_empty_prompt(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")

    provider = GeminiProvider()
    provider.client = Mock()

    with pytest.raises(ValueError):
        provider.generate("   ")

    provider.client.models.generate_content.assert_not_called()


def test_gemini_provider_does_not_retry_quota_errors(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")

    provider = GeminiProvider()
    provider.client = Mock()

    provider.client.models.generate_content.side_effect = (
        errors.ClientError(
            429,
            {"error": {"message": "Quota exceeded"}},
            None,
        )
    )

    with pytest.raises(GeminiQuotaExceededError):
        provider.generate("Test prompt")

    provider.client.models.generate_content.assert_called_once()