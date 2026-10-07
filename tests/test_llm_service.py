from unittest.mock import Mock

from backend.app.services.llm.llm_service import LLMService


def test_llm_service():
    provider = Mock()
    provider.generate.return_value = "Test response"

    service = LLMService(provider=provider)

    result = service.generate("Hello")

    assert result == "Test response"
    provider.generate.assert_called_once_with("Hello")


def test_llm_service_rejects_empty_prompt():
    provider = Mock()

    service = LLMService(provider=provider)

    try:
        service.generate("")
        assert False, "Expected ValueError"
    except ValueError as exc:
        assert str(exc) == "prompt cannot be empty."