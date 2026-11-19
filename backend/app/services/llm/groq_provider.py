"""Groq chat-completion adapter using its OpenAI-compatible REST API."""

import os
import time
import logging

import httpx
from dotenv import load_dotenv

from backend.app.services.llm.errors import (
    LLMAuthenticationError,
    LLMConfigurationError,
    LLMIncompleteResponseError,
    LLMRateLimitError,
    LLMRequestError,
    LLMTimeoutError,
    LLMUnavailableError,
)


load_dotenv()

GROQ_CHAT_COMPLETIONS_URL = "https://api.groq.com/openai/v1/chat/completions"
DEFAULT_GROQ_MODEL = "openai/gpt-oss-20b"
DEFAULT_GROQ_TIMEOUT_SECONDS = 45.0
DEFAULT_GROQ_MAX_OUTPUT_TOKENS = 2048
DEFAULT_GROQ_MAX_RETRIES = 1
RETRYABLE_STATUS_CODES = {500, 502, 503, 504}
logger = logging.getLogger(__name__)


class GroqProvider:
    """Generate text through Groq's chat-completions endpoint."""

    def __init__(self):
        api_key = os.getenv("GROQ_API_KEY", "").strip()
        if not api_key:
            raise LLMConfigurationError(
                "GROQ_API_KEY must be configured for the Groq provider."
            )

        self.api_key = api_key
        self.model = os.getenv("GROQ_MODEL", DEFAULT_GROQ_MODEL).strip()
        if not self.model:
            raise LLMConfigurationError("GROQ_MODEL cannot be empty.")

        try:
            self.timeout_seconds = float(
                os.getenv(
                    "GROQ_TIMEOUT_SECONDS",
                    str(DEFAULT_GROQ_TIMEOUT_SECONDS),
                )
            )
            self.max_output_tokens = int(
                os.getenv(
                    "GROQ_MAX_OUTPUT_TOKENS",
                    str(DEFAULT_GROQ_MAX_OUTPUT_TOKENS),
                )
            )
            self.max_retries = int(
                os.getenv(
                    "GROQ_MAX_RETRIES",
                    str(DEFAULT_GROQ_MAX_RETRIES),
                )
            )
        except ValueError as exc:
            raise LLMConfigurationError(
                "Groq timeout, output token, and retry settings must be numeric."
            ) from exc

        if self.timeout_seconds <= 0 or self.max_output_tokens <= 0:
            raise LLMConfigurationError(
                "Groq timeout and output token settings must be positive."
            )
        if not 0 <= self.max_retries <= 1:
            raise LLMConfigurationError(
                "GROQ_MAX_RETRIES must be 0 or 1."
            )

    def generate(self, prompt: str) -> str:
        if not isinstance(prompt, str):
            raise TypeError("prompt must be a string.")
        if not prompt.strip():
            raise ValueError("prompt cannot be empty.")

        payload = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "max_completion_tokens": self.max_output_tokens,
        }
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        for attempt in range(self.max_retries + 1):
            try:
                response = httpx.post(
                    GROQ_CHAT_COMPLETIONS_URL,
                    headers=headers,
                    json=payload,
                    timeout=self.timeout_seconds,
                )
            except httpx.TimeoutException as exc:
                raise LLMTimeoutError(
                    "The AI provider timed out. Please try again."
                ) from exc
            except httpx.RequestError as exc:
                raise LLMUnavailableError(
                    "The AI provider could not be reached. Please try again."
                ) from exc

            status_code = response.status_code
            if status_code in {401, 403}:
                raise LLMAuthenticationError(
                    "The AI provider credentials were rejected. Check the server configuration."
                )
            if status_code == 429:
                # Daily quotas and rate limits must not be retried.
                raise LLMRateLimitError(
                    "The AI provider quota or rate limit has been reached. Please try again later."
                )
            if status_code in {408, 504}:
                raise LLMTimeoutError(
                    "The AI provider timed out. Please try again."
                )
            if status_code in RETRYABLE_STATUS_CODES:
                if attempt < self.max_retries:
                    time.sleep(0.25)
                    continue
                raise LLMUnavailableError(
                    "The AI provider is temporarily unavailable. Please try again."
                )
            if status_code >= 400:
                raise LLMRequestError(
                    "The AI provider could not process this request."
                )

            try:
                result = response.json()
            except (ValueError, TypeError) as exc:
                raise LLMUnavailableError(
                    "The AI provider returned an invalid response. Please try again."
                ) from exc

            choices = result.get("choices") if isinstance(result, dict) else None
            if not isinstance(choices, list) or not choices:
                raise LLMUnavailableError(
                    "The AI provider returned an empty response. Please try again."
                )

            choice = choices[0]
            message = choice.get("message") if isinstance(choice, dict) else None
            content = message.get("content") if isinstance(message, dict) else None
            finish_reason = choice.get("finish_reason") if isinstance(choice, dict) else None
            usage = result.get("usage", {}) if isinstance(result, dict) else {}
            output_tokens = usage.get("completion_tokens") if isinstance(usage, dict) else None
            response_chars = len(content) if isinstance(content, str) else 0
            logger.info(
                "Groq completion metadata: finish_reason=%s output_tokens=%s response_chars=%d",
                finish_reason,
                output_tokens,
                response_chars,
            )

            if str(finish_reason).lower() == "length":
                logger.warning(
                    "Groq response was truncated: finish_reason=%s output_tokens=%s response_chars=%d",
                    finish_reason,
                    output_tokens,
                    response_chars,
                )
                raise LLMIncompleteResponseError(
                    "The AI response was cut off before it finished. Please try again."
                )

            if not isinstance(content, str) or not content.strip():
                raise LLMUnavailableError(
                    "The AI provider returned an empty response. Please try again."
                )

            return content.strip()

        raise LLMUnavailableError(
            "The AI provider is temporarily unavailable. Please try again."
        )
