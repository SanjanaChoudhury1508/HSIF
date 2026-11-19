
"""
gemini_provider.py

Provides text generation through Google's Gemini API.
"""

import os
import time

from dotenv import load_dotenv
from google import genai
from google.genai import errors, types


load_dotenv()

GEMINI_TIMEOUT_MS = int(
    os.getenv("GEMINI_TIMEOUT_MS", "30000")
)


class GeminiQuotaExceededError(RuntimeError):
    """Raised when Gemini API quota is exhausted."""


class GeminiIncompleteResponseError(RuntimeError):
    """Raised when Gemini stops before producing a complete response."""


class GeminiProvider:
    """Generates responses using the Gemini API."""

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

    @staticmethod
    def _log_response_debug(response) -> None:
        """Log response metadata without exposing prompts or generated text."""
        try:
            response_text = getattr(response, "text", None)
        except Exception:
            response_text = None
        output_length = len(response_text) if isinstance(response_text, str) else 0

        candidates = getattr(response, "candidates", None)
        finish_reason = None
        if isinstance(candidates, (list, tuple)) and candidates:
            candidate = candidates[0]
            finish_reason = getattr(candidate, "finish_reason", None)

        usage_metadata = getattr(
            response,
            "usage_metadata",
            None,
        )
        candidate_tokens = getattr(
            usage_metadata, "candidates_token_count", None
        )
        thinking_tokens = getattr(
            usage_metadata, "thoughts_token_count", None
        )

        print(
            "Gemini response metadata: "
            f"finish_reason={finish_reason!s}, "
            f"candidate_tokens={candidate_tokens!r}, "
            f"thinking_tokens={thinking_tokens!r}, "
            f"output_length={output_length}"
        )

    def generate(self, prompt: str) -> str:
        """Generate a response from Gemini."""

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
                    config=types.GenerateContentConfig(
                        max_output_tokens=1024,
                        thinking_config=types.ThinkingConfig(
                            thinking_level=types.ThinkingLevel.MINIMAL,
                        ),
                    ),
                )

                self._log_response_debug(response)

                candidates = getattr(response, "candidates", None)
                if isinstance(candidates, (list, tuple)) and candidates:
                    finish_reason = getattr(
                        candidates[0], "finish_reason", None
                    )
                    finish_reason_value = getattr(
                        finish_reason, "value", finish_reason
                    )
                    finish_reason_name = str(finish_reason_value).upper().split(".")[-1]
                    if finish_reason_name == "MAX_TOKENS":
                        raise GeminiIncompleteResponseError(
                            "Gemini stopped at the output token limit before "
                            "completing its response. Please try again."
                        )

                response_text = getattr(
                    response,
                    "text",
                    None,
                )

                if not isinstance(response_text, str) or not response_text.strip():
                    raise RuntimeError(
                        "Gemini returned an empty or invalid response."
                    )

                return response_text.strip()

            except errors.ClientError as exc:
                if exc.code == 429:
                    raise GeminiQuotaExceededError(
                        "Gemini quota or rate limit exceeded. "
                        "Check API usage and retry after quota "
                        "becomes available."
                    ) from exc

                raise

            except errors.ServerError as exc:
                retryable = exc.code in (503, 504)

                if not retryable or attempt == max_attempts - 1:
                    raise

                time.sleep(2 ** attempt)

        raise RuntimeError(
            "Gemini request failed after retries."
        )
