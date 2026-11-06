"""Experimental local-only LLM bridge for llama.cpp OR Ollama.

One OpenAI-compatible chat adapter, not parallel provider-specific clones.
No model is enabled by default; only explicitly approved local model IDs
may be used. This bridge provides text generation, NOT autonomous tool execution.
"""

from __future__ import annotations

from .loopback_http import IntegrationUnavailable, LoopbackJSON


class LocalInference:
    def __init__(
        self,
        base_url: str = "http://127.0.0.1:8080/v1",
        *,
        allowed_models: tuple[str, ...] = (),
        timeout: float = 30.0,
    ):
        self.http = LoopbackJSON(base_url, timeout=timeout)
        if not isinstance(allowed_models, tuple) or any(
            not isinstance(m, str) or not m or len(m) > 200 for m in allowed_models
        ):
            raise ValueError("allowed_models must be a tuple of model IDs")
        self.allowed_models = frozenset(allowed_models)

    def models(self) -> tuple[str, ...]:
        """Probe the live local endpoint. Never equate installed with verified."""
        result = self.http.request("GET", "/models")
        data = result.get("data")
        if not isinstance(data, list):
            raise IntegrationUnavailable("local model list has unexpected shape")
        ids = tuple(item["id"] for item in data if isinstance(item, dict)
                    and isinstance(item.get("id"), str) and 0 < len(item["id"]) <= 200)
        return tuple(dict.fromkeys(ids))

    def chat(self, model: str, prompt: str, *, max_tokens: int = 512) -> str:
        """Explicit, non-streaming local chat; never authorizes model tool calls."""
        if model not in self.allowed_models:
            raise IntegrationUnavailable("model not explicitly approved for local inference")
        if model.lower().endswith(":cloud"):
            raise IntegrationUnavailable("cloud model route is forbidden")
        if not isinstance(prompt, str) or not prompt.strip() or len(prompt) > 16_000:
            raise ValueError("prompt must contain 1..16000 characters")
        if type(max_tokens) is not int or not 1 <= max_tokens <= 2048:
            raise ValueError("max_tokens must be 1..2048")
        if model not in self.models():
            raise IntegrationUnavailable("approved local model was not found at the endpoint")
        result = self.http.request("POST", "/chat/completions", {
            "model": model, "stream": False,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": max_tokens,
        })
        choices = result.get("choices")
        if not isinstance(choices, list) or not choices or not isinstance(choices[0], dict):
            raise IntegrationUnavailable("local chat response has unexpected shape")
        message = choices[0].get("message")
        if not isinstance(message, dict) or not isinstance(message.get("content"), str):
            raise IntegrationUnavailable("local chat response has no text content")
        return message["content"]
