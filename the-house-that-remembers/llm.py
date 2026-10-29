import json
import os
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

import ollama


OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
DEFAULT_OPENROUTER_MODEL = "google/gemma-4-26b-a4b-it:free"
DEFAULT_OLLAMA_MODEL = "gemma4:e4b"


class ModelConfigurationError(Exception):
    """Raised when the selected model provider is not configured correctly."""


class OpenRouterError(Exception):
    def __init__(self, message, status_code=None):
        super().__init__(message)
        self.status_code = status_code


def provider_name():
    provider = os.getenv("MODEL_PROVIDER", "ollama").strip().lower()
    if provider not in {"ollama", "openrouter"}:
        raise ModelConfigurationError(
            "MODEL_PROVIDER must be either 'ollama' or 'openrouter'."
        )
    return provider


def model_name():
    if provider_name() == "openrouter":
        name = os.getenv("OPENROUTER_MODEL", DEFAULT_OPENROUTER_MODEL).strip()
        if not name:
            raise ModelConfigurationError("OPENROUTER_MODEL cannot be empty.")
        return name
    name = os.getenv("OLLAMA_MODEL", DEFAULT_OLLAMA_MODEL).strip()
    if not name:
        raise ModelConfigurationError("OLLAMA_MODEL cannot be empty.")
    return name


def chat(messages, options):
    provider = provider_name()
    if provider == "ollama":
        result = ollama.chat(
            model=model_name(),
            messages=messages,
            think=False,
            options=options,
        )
        return result.message.content

    api_key = os.getenv("OPENROUTER_API_KEY", "").strip()
    if not api_key:
        raise ModelConfigurationError(
            "OPENROUTER_API_KEY is required when MODEL_PROVIDER is 'openrouter'."
        )

    payload = {
        "model": model_name(),
        "messages": messages,
        "temperature": options.get("temperature", 0.6),
        "max_tokens": options.get("num_predict", 200),
    }
    request = Request(
        OPENROUTER_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "X-Title": "The House That Remembers",
        },
        method="POST",
    )

    try:
        with urlopen(request, timeout=120) as response:
            try:
                result = json.loads(response.read().decode("utf-8"))
            except json.JSONDecodeError as error:
                raise OpenRouterError("OpenRouter returned invalid JSON.") from error
    except HTTPError as error:
        body = error.read().decode("utf-8", errors="replace")
        try:
            error_response = json.loads(body)
            if isinstance(error_response, dict):
                error_detail = error_response.get("error")
                if isinstance(error_detail, dict):
                    body = error_detail.get("message", body)
                elif isinstance(error_detail, str):
                    body = error_detail
        except json.JSONDecodeError:
            pass
        raise OpenRouterError(str(body), error.code) from error
    except (TimeoutError, URLError) as error:
        raise OpenRouterError(f"Could not connect to OpenRouter: {error}") from error

    try:
        content = result["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as error:
        raise OpenRouterError("OpenRouter returned an unexpected response.") from error
    if not isinstance(content, str):
        raise OpenRouterError("OpenRouter did not return a text response.")
    return content
