import pytest
from unittest.mock import Mock

from google.genai import errors
from google.genai import types

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
        text="  HSIF test successful.  ",
        candidates=[],
    )

    assert provider.generate("Test prompt") == "HSIF test successful."
    provider.client.models.generate_content.assert_called_once()
    config = provider.client.models.generate_content.call_args.kwargs["config"]
    assert config.max_output_tokens == 1024
    assert (
        config.thinking_config.thinking_level
        == types.ThinkingLevel.MINIMAL
    )


def test_gemini_provider_logs_metadata_without_response_or_prompt(monkeypatch, capsys):
    from types import SimpleNamespace

    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    provider = GeminiProvider()
    provider.client = Mock()
    provider.client.models.generate_content.return_value = SimpleNamespace(
        text="private generated response",
        candidates=[SimpleNamespace(finish_reason=types.FinishReason.STOP)],
        usage_metadata=SimpleNamespace(
            candidates_token_count=12,
            thoughts_token_count=3,
        ),
    )

    assert provider.generate("private user prompt") == "private generated response"

    output = capsys.readouterr().out
    assert "STOP" in output
    assert "candidate_tokens=12" in output
    assert "thinking_tokens=3" in output
    assert "output_length=26" in output
    assert "private generated response" not in output
    assert "private user prompt" not in output


def test_gemini_provider_rejects_max_token_response_without_retry(monkeypatch):
    from types import SimpleNamespace

    from backend.app.services.llm.gemini_provider import (
        GeminiIncompleteResponseError,
    )

    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    provider = GeminiProvider()
    provider.client = Mock()
    provider.client.models.generate_content.return_value = SimpleNamespace(
        text="truncated output",
        candidates=[
            SimpleNamespace(finish_reason=types.FinishReason.MAX_TOKENS)
        ],
        usage_metadata=None,
    )

    with pytest.raises(GeminiIncompleteResponseError, match="output token limit"):
        provider.generate("Test prompt")

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

def test_gemini_provider_configures_request_timeout(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")

    provider = GeminiProvider()

    assert provider.client._api_client._http_options.timeout == 30_000


def test_gemini_provider_propagates_timeout(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")

    provider = GeminiProvider()
    provider.client = Mock()
    provider.client.models.generate_content.side_effect = TimeoutError(
        "Request timed out"
    )

    with pytest.raises(TimeoutError, match="Request timed out"):
        provider.generate("Test prompt")

    provider.client.models.generate_content.assert_called_once()


def test_gemini_provider_retries_transient_server_errors(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")

    provider = GeminiProvider()
    provider.client = Mock()
    provider.client.models.generate_content.side_effect = [
        errors.ServerError(503, {"error": {"message": "Unavailable"}}, None),
        errors.ServerError(503, {"error": {"message": "Unavailable"}}, None),
        Mock(text="Recovered response"),
    ]
    sleeps = []
    monkeypatch.setattr(
        "backend.app.services.llm.gemini_provider.time.sleep",
        sleeps.append,
    )

    assert provider.generate("Test prompt") == "Recovered response"
    assert provider.client.models.generate_content.call_count == 3
    assert sleeps == [1, 2]


def test_gemini_provider_retries_gateway_timeout(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")

    provider = GeminiProvider()
    provider.client = Mock()
    provider.client.models.generate_content.side_effect = [
        errors.ServerError(504, {"error": {"message": "Gateway timeout"}}, None),
        Mock(text="Recovered response", candidates=[]),
    ]
    sleeps = []
    monkeypatch.setattr(
        "backend.app.services.llm.gemini_provider.time.sleep",
        sleeps.append,
    )

    assert provider.generate("Test prompt") == "Recovered response"
    assert provider.client.models.generate_content.call_count == 2
    assert sleeps == [1]


def test_gemini_provider_propagates_server_error_after_retry_limit(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")

    provider = GeminiProvider()
    provider.client = Mock()
    provider.client.models.generate_content.side_effect = errors.ServerError(
        503,
        {"error": {"message": "Unavailable"}},
        None,
    )
    sleeps = []
    monkeypatch.setattr(
        "backend.app.services.llm.gemini_provider.time.sleep",
        sleeps.append,
    )

    with pytest.raises(errors.ServerError):
        provider.generate("Test prompt")

    assert provider.client.models.generate_content.call_count == 3
    assert sleeps == [1, 2]
