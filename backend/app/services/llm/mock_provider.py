from backend.app.services.llm.provider import LLMProvider


class MockLLMProvider(LLMProvider):

    def generate(self, prompt: str) -> str:
        if not isinstance(prompt, str):
            raise TypeError("prompt must be a string.")

        return (
            "This is a mock AI response generated for testing. "
            "The dialogue policy and human state were successfully "
            "processed."
        )