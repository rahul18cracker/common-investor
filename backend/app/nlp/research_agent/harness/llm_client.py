"""Anthropic LLM client adapter for the qualitative agent harness.

Wraps the Anthropic SDK into the LLMCallable protocol expected by
builder.py and evaluator.py. Handles prompt caching via cache_control
blocks on the static prefix.
"""

from __future__ import annotations

import os
from pathlib import Path

import anthropic
import httpx

MODEL_MAP = {
    "haiku": "claude-haiku-4-5-20251001",
    "sonnet": "claude-sonnet-4-6",
    "opus": "claude-opus-4-7",
}

_SSL_CERT_CANDIDATES = [
    "/opt/homebrew/etc/openssl@3/cert.pem",
    "/usr/local/etc/openssl@3/cert.pem",
    "/etc/ssl/certs/ca-certificates.crt",
]


def _resolve_ssl_cert() -> str | None:
    """Find a usable SSL cert bundle for corporate proxy environments."""
    env_cert = os.environ.get("SSL_CERT_FILE")
    if env_cert and Path(env_cert).exists():
        return env_cert
    for candidate in _SSL_CERT_CANDIDATES:
        if Path(candidate).exists():
            return candidate
    return None


class AnthropicLLMClient:
    """Adapter that matches the LLMCallable protocol: (system, user) -> str."""

    def __init__(
        self,
        model: str = "haiku",
        api_key: str | None = None,
        max_tokens: int = 4096,
    ):
        self.model_id = MODEL_MAP.get(model, model)
        self.max_tokens = max_tokens
        self._api_key = api_key or os.environ.get("ANTHROPIC_API_KEY")

        ssl_cert = _resolve_ssl_cert()
        if ssl_cert:
            http_client = httpx.Client(verify=ssl_cert)
            self.client = anthropic.Anthropic(
                api_key=self._api_key,
                http_client=http_client,
            )
        else:
            self.client = anthropic.Anthropic(api_key=self._api_key)
        self.last_usage: dict[str, int] = {}

    def __call__(self, system_prompt: str, user_prompt: str, static_context: str | None = None) -> str:
        system_blocks = []
        if static_context:
            system_blocks.append(
                {
                    "type": "text",
                    "text": static_context,
                    "cache_control": {"type": "ephemeral"},
                }
            )
        system_blocks.append(
            {
                "type": "text",
                "text": system_prompt,
            }
        )
        response = self.client.messages.create(
            model=self.model_id,
            max_tokens=self.max_tokens,
            system=system_blocks,
            messages=[{"role": "user", "content": user_prompt}],
        )

        self.last_usage = {
            "input_tokens": response.usage.input_tokens,
            "output_tokens": response.usage.output_tokens,
            "cache_creation_input_tokens": getattr(response.usage, "cache_creation_input_tokens", 0) or 0,
            "cache_read_input_tokens": getattr(response.usage, "cache_read_input_tokens", 0) or 0,
        }

        return response.content[0].text

    def with_model(self, model: str) -> "AnthropicLLMClient":
        """Return a new client instance with a different model tier."""
        return AnthropicLLMClient(
            model=model,
            api_key=self._api_key,
            max_tokens=self.max_tokens,
        )
