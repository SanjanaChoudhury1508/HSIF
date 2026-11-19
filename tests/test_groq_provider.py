from unittest.mock import Mock

import httpx
import pytest

from backend.app.services.llm import groq_provider
from backend.app.services.llm.errors import (
    LLMAuthenticationError,
    LLMConfigurationError,
    LLMIncompleteResponseError,
    LLMRateLimitError,
    LLMTimeoutError,
    LLMUnavailableError,
)
from backend.app.services.llm.groq_provider import (
    DEFAULT_GROQ_MODEL,
    GROQ_CHAT_COMPLETIONS_URL,
    GroqProvider,
)
from backend.app.services.llm.llm_service import LLMService


class FakeResponse:
    def __init__(self, status_code=200, payload=None):
        self.status_code = status_code
        self.payload = payload or {}

    def json(self):
        return self.payload


def configure_groq(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "test-groq-key")
    monkeypatch.setenv("GROQ_MODEL", DEFAULT_GROQ_MODEL)
    monkeypatch.delenv("GROQ_TIMEOUT_SECONDS", raising=False)
    monkeypatch.delenv("GROQ_MAX_OUTPUT_TOKENS", raising=False)
    monkeypatch.delenv("GROQ_MAX_RETRIES", raising=False)


def test_groq_provider_returns_nonempty_response_and_uses_config(monkeypatch):
    configure_groq(monkeypatch)
    response = FakeResponse(
        payload={
            "choices": [
                {
                    "message": {"content": "  Groq response text.  "},
                    "finish_reason": "stop",
                }
            ],
            "usage": {"completion_tokens": 12},
        }
    )
    request = Mock(return_value=response)
    monkeypatch.setattr(groq_provider.httpx, "post", request)

    provider = GroqProvider()
    result = provider.generate("Explain this.")

    assert result == "Groq response text."
    request.assert_called_once_with(
        GROQ_CHAT_COMPLETIONS_URL,
        headers={
            "Authorization": "Bearer test-groq-key",
            "Content-Type": "application/json",
        },
        json={
            "model": DEFAULT_GROQ_MODEL,
            "messages": [{"role": "user", "content": "Explain this."}],
            "max_completion_tokens": 2048,
        },
        timeout=45.0,
    )


def test_groq_provider_rejects_length_limited_response_and_logs_metadata(
    monkeypatch, caplog
):
    configure_groq(monkeypatch)
    prompt = "private prompt must not be logged"
    response_text = "A response that was cut short"
    response = FakeResponse(
        payload={
            "choices": [
                {
                    "message": {"content": response_text},
                    "finish_reason": "length",
                }
            ],
            "usage": {"completion_tokens": 2048},
        }
    )
    monkeypatch.setattr(groq_provider.httpx, "post", Mock(return_value=response))

    with pytest.raises(LLMIncompleteResponseError, match="cut off before it finished"):
        GroqProvider().generate(prompt)

    logs = caplog.text
    assert "finish_reason=length" in logs
    assert "output_tokens=2048" in logs
    assert f"response_chars={len(response_text)}" in logs
    assert prompt not in logs
    assert response_text not in logs


def test_groq_provider_respects_output_token_override(monkeypatch):
    configure_groq(monkeypatch)
    monkeypatch.setenv("GROQ_MAX_OUTPUT_TOKENS", "1536")
    request = Mock(
        return_value=FakeResponse(
            payload={
                "choices": [
                    {"message": {"content": "Complete."}, "finish_reason": "stop"}
                ],
                "usage": {"completion_tokens": 4},
            }
        )
    )
    monkeypatch.setattr(groq_provider.httpx, "post", request)

    assert GroqProvider().generate("Explain this.") == "Complete."
    assert request.call_args.kwargs["json"]["max_completion_tokens"] == 1536


@pytest.mark.parametrize("payload", [{}, {"choices": []}, {"choices": [{"message": {"content": "  "}}]}])
def test_groq_provider_rejects_empty_response(monkeypatch, payload):
    configure_groq(monkeypatch)
    monkeypatch.setattr(
        groq_provider.httpx,
        "post",
        Mock(return_value=FakeResponse(payload=payload)),
    )

    with pytest.raises(LLMUnavailableError, match="empty response"):
        GroqProvider().generate("Explain this.")


def test_groq_provider_maps_timeout_without_retry(monkeypatch):
    configure_groq(monkeypatch)
    request = Mock(side_effect=httpx.ReadTimeout("private timeout details"))
    monkeypatch.setattr(groq_provider.httpx, "post", request)

    with pytest.raises(LLMTimeoutError) as exc_info:
        GroqProvider().generate("Explain this.")

    assert "private timeout details" not in str(exc_info.value)
    request.assert_called_once()


@pytest.mark.parametrize("status_code", [401, 403])
def test_groq_provider_maps_authentication_failure(monkeypatch, status_code):
    configure_groq(monkeypatch)
    monkeypatch.setattr(
        groq_provider.httpx,
        "post",
        Mock(return_value=FakeResponse(status_code=status_code)),
    )

    with pytest.raises(LLMAuthenticationError):
        GroqProvider().generate("Explain this.")


def test_groq_provider_does_not_retry_rate_limits_or_expose_provider_body(monkeypatch):
    configure_groq(monkeypatch)
    request = Mock(
        return_value=FakeResponse(
            status_code=429,
            payload={"error": "private quota details"},
        )
    )
    sleep = Mock()
    monkeypatch.setattr(groq_provider.httpx, "post", request)
    monkeypatch.setattr(groq_provider.time, "sleep", sleep)

    with pytest.raises(LLMRateLimitError) as exc_info:
        GroqProvider().generate("Explain this.")

    assert "private quota details" not in str(exc_info.value)
    request.assert_called_once()
    sleep.assert_not_called()


def test_groq_provider_retries_a_transient_server_error_once(monkeypatch):
    configure_groq(monkeypatch)
    request = Mock(
        side_effect=[
            FakeResponse(status_code=503),
            FakeResponse(
                payload={
                    "choices": [{"message": {"content": "Recovered."}}]
                }
            ),
        ]
    )
    sleep = Mock()
    monkeypatch.setattr(groq_provider.httpx, "post", request)
    monkeypatch.setattr(groq_provider.time, "sleep", sleep)

    assert GroqProvider().generate("Explain this.") == "Recovered."
    assert request.call_count == 2
    sleep.assert_called_once_with(0.25)


def test_groq_provider_requires_key_and_valid_settings(monkeypatch):
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    with pytest.raises(LLMConfigurationError, match="GROQ_API_KEY"):
        GroqProvider()

    configure_groq(monkeypatch)
    monkeypatch.setenv("GROQ_MAX_RETRIES", "2")
    with pytest.raises(LLMConfigurationError, match="0 or 1"):
        GroqProvider()


def test_llm_service_selects_groq_or_gemini_and_rejects_invalid_provider(monkeypatch):
    configure_groq(monkeypatch)
    monkeypatch.setenv("LLM_PROVIDER", "groq")
    assert isinstance(LLMService().provider, GroqProvider)
    assert LLMService.validate_provider_name() == "groq"

    monkeypatch.setenv("LLM_PROVIDER", "gemini")
    monkeypatch.setenv("GEMINI_API_KEY", "test-gemini-key")
    from backend.app.services.llm.gemini_provider import GeminiProvider

    assert isinstance(LLMService().provider, GeminiProvider)

    monkeypatch.setenv("LLM_PROVIDER", "unknown")
    with pytest.raises(LLMConfigurationError, match="groq.*gemini"):
        LLMService()


def test_startup_validation_requires_credentials_for_selected_provider(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "groq")
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    with pytest.raises(LLMConfigurationError, match="GROQ_API_KEY"):
        LLMService.validate_provider_configuration()

    monkeypatch.setenv("LLM_PROVIDER", "gemini")
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    with pytest.raises(LLMConfigurationError, match="GEMINI_API_KEY"):
        LLMService.validate_provider_configuration()


def test_pipeline_uses_selected_groq_provider_without_live_request(monkeypatch):
    configure_groq(monkeypatch)
    monkeypatch.setenv("LLM_PROVIDER", "groq")
    monkeypatch.setattr(
        groq_provider.httpx,
        "post",
        Mock(
            return_value=FakeResponse(
                payload={
                    "choices": [{"message": {"content": "Pipeline response."}}]
                }
            )
        ),
    )

    from backend.app.services.pipeline_service import PipelineService

    result = PipelineService().process_text("Explain this.")

    assert result["response"] == "Pipeline response."
