import os

from dotenv import load_dotenv

from backend.app.services.llm.errors import LLMConfigurationError
from backend.app.services.llm.gemini_provider import GeminiProvider
from backend.app.services.llm.groq_provider import GroqProvider


load_dotenv()


class LLMService:
    SUPPORTED_PROVIDERS = {"groq", "gemini"}

    def __init__(self, provider=None):
        if provider is not None:
            self.provider = provider
            return

        provider_name = self.validate_provider_name()
        if provider_name == "groq":
            self.provider = GroqProvider()
        else:
            try:
                self.provider = GeminiProvider()
            except ValueError as exc:
                raise LLMConfigurationError(
                    "GEMINI_API_KEY must be configured for the Gemini provider."
                ) from exc

    @classmethod
    def validate_provider_name(cls) -> str:
        provider_name = os.getenv("LLM_PROVIDER", "groq").strip().lower()
        if provider_name not in cls.SUPPORTED_PROVIDERS:
            raise LLMConfigurationError(
                "LLM_PROVIDER must be set to either 'groq' or 'gemini'."
            )
        return provider_name

    @classmethod
    def validate_provider_configuration(cls) -> str:
        """Validate selection and required credentials without making a request."""
        provider_name = cls.validate_provider_name()
        if provider_name == "groq":
            GroqProvider()
        else:
            try:
                GeminiProvider()
            except ValueError as exc:
                raise LLMConfigurationError(
                    "GEMINI_API_KEY must be configured for the Gemini provider."
                ) from exc
        return provider_name

    def generate(self, prompt: str) -> str:
        if not isinstance(prompt, str):
            raise TypeError("prompt must be a string.")

        if not prompt.strip():
            raise ValueError("prompt cannot be empty.")

        return self.provider.generate(prompt)
