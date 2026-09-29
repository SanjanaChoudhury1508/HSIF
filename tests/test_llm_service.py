from backend.app.services.llm.llm_service import LLMService


def test_llm_service():
    service = LLMService()

    response = service.generate(
        "Hello, this is a test prompt."
    )

    assert isinstance(response, str)
    assert response.strip()


def test_llm_service_rejects_empty_prompt():
    service = LLMService()

    try:
        service.generate("")
        assert False
    except ValueError:
        assert True