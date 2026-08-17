import os

import pytest

from backend.app.services.llm.gemini_provider import GeminiProvider


def test_gemini_provider_requires_api_key(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)

    with pytest.raises(ValueError):
        GeminiProvider()


@pytest.mark.skipif(
    not os.getenv("GEMINI_API_KEY"),
    reason="GEMINI_API_KEY is not set",
)
def test_gemini_provider():
    provider = GeminiProvider()

    response = provider.generate(
        "Reply with exactly: HSIF Gemini test successful."
    )

    assert isinstance(response, str)
    assert response.strip()