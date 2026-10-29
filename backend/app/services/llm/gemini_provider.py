import os
import time

from dotenv import load_dotenv
from google import genai
from google.genai import errors, types


load_dotenv()
GEMINI_TIMEOUT_MS=30_000

class GeminiQuotaExceededError(RuntimeError):
    """Raised when Gemini API quota is exhausted."""


class GeminiProvider:
    def __init__(self, model: str = "gemini-3.6-flash"):
        api_key = os.getenv("GEMINI_API_KEY")

        if not api_key:
            raise ValueError(
                "GEMINI_API_KEY environment variable is not set."
            )

        self.client = genai.Client(
            api_key=api_key,
            http_options=types.HttpOptions(
                timeout=GEMINI_TIMEOUT_MS,
            ),
        )
        self.model = model

    def generate(self, prompt: str) -> str:
        if not isinstance(prompt, str):
            raise TypeError("prompt must be a string.")

        if not prompt.strip():
            raise ValueError("prompt cannot be empty.")

        max_attempts = 3

        for attempt in range(max_attempts):
            try:
                response = self.client.models.generate_content(
                    model=self.model,
                    contents=prompt,
                )

                if not response.text:
                    raise RuntimeError(
                        "Gemini returned an empty response."
                    )

                return response.text.strip()

            except errors.ClientError as exc:
                if exc.code == 429:
                    raise GeminiQuotaExceededError(
                        "Gemini quota is exhausted. Check your API "
                        "usage and retry after quota becomes available."
                    ) from exc
                raise

            except errors.ServerError as exc:
                if exc.code != 503 or attempt == max_attempts - 1:
                    raise

                time.sleep(2 ** attempt)

        raise RuntimeError("Gemini request failed after retries.")