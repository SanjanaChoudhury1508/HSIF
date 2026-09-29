from abc import ABC, abstractmethod


class LLMProvider(ABC):

    @abstractmethod
    def generate(self, prompt: str) -> str:
        """
        Generate a response from the provided prompt.
        """
        raise NotImplementedError