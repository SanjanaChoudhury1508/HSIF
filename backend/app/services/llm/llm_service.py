from backend.app.services.llm.gemini_provider import GeminiProvider


class LLMService:

    def __init__(self, provider=None):
        self.provider = provider or GeminiProvider()

    def generate(self, prompt: str) -> str:
        if not isinstance(prompt, str):
            raise TypeError("prompt must be a string.")

        if not prompt.strip():
            raise ValueError("prompt cannot be empty.")

        return self.provider.generate(prompt)