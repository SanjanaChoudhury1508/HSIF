"""Safe, provider-neutral LLM failures used at the API boundary."""


class LLMProviderError(RuntimeError):
    """Base class for failures communicating with a configured LLM provider."""


class LLMConfigurationError(LLMProviderError):
    """The selected provider cannot be configured from the environment."""


class LLMTimeoutError(LLMProviderError):
    """The provider did not respond before the configured timeout."""


class LLMAuthenticationError(LLMProviderError):
    """The provider rejected the configured credentials."""


class LLMRateLimitError(LLMProviderError):
    """The provider rejected the request because of quota or rate limits."""


class LLMUnavailableError(LLMProviderError):
    """The provider is unavailable or returned an invalid response."""


class LLMIncompleteResponseError(LLMProviderError):
    """The provider stopped generation before completing its response."""


class LLMRequestError(LLMProviderError):
    """The provider rejected a request that could not be completed."""
