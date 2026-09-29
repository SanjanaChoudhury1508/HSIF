from backend.app.services.llm.provider import LLMProvider
from backend.app.services.llm.mock_provider import MockLLMProvider


class LLMService:

    def __init__(
        self,
        provider: LLMProvider | None = None,
    ):
        self.provider = provider or MockLLMProvider()

    def generate(self, prompt: str) -> str:
        if not isinstance(prompt, str):
            raise TypeError("prompt must be a string.")

        if not prompt.strip():
            raise ValueError("prompt cannot be empty.")

        return self.provider.generate(prompt)