import os

from backend.app.services.llm.provider import LLMProvider
from backend.app.services.llm.mock_provider import MockLLMProvider
from backend.app.services.llm.gemini_provider import GeminiProvider


class LLMService:

    def __init__(
        self,
        provider: LLMProvider | None = None,
    ):
        if provider is not None:
            self.provider = provider
            return

        provider_name = os.getenv("LLM_PROVIDER", "mock").lower()

        if provider_name == "gemini":
            self.provider = GeminiProvider()
        elif provider_name == "mock":
            self.provider = MockLLMProvider()
        else:
            raise ValueError(
                f"Unsupported LLM_PROVIDER: {provider_name}. "
                "Use 'mock' or 'gemini'."
            )

    def generate(self, prompt: str) -> str:
        if not isinstance(prompt, str):
            raise TypeError("prompt must be a string.")

        if not prompt.strip():
            raise ValueError("prompt cannot be empty.")

        return self.provider.generate(prompt)