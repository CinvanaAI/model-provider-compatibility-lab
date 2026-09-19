"""Small provider adapters with an injectable HTTP boundary."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Callable
from typing import Any

import requests

from .types import AnalysisResponse, ModelRef, ProviderConfig, ProviderError


HttpTransport = Callable[
    [str, str, dict[str, str], dict[str, Any] | None, float],
    tuple[int, dict[str, Any]],
]


def requests_transport(
    method: str,
    url: str,
    headers: dict[str, str],
    payload: dict[str, Any] | None,
    timeout: float,
) -> tuple[int, dict[str, Any]]:
    try:
        response = requests.request(
            method, url, headers=headers, json=payload, timeout=timeout, allow_redirects=False
        )
    except requests.RequestException as exc:
        raise ProviderError(str(exc), error_type="connection_error") from exc
    try:
        body = response.json()
    except ValueError as exc:
        raise ProviderError("provider returned non-JSON", error_type="response_format_error") from exc
    if not isinstance(body, dict):
        raise ProviderError("provider returned a non-object JSON value", error_type="response_format_error")
    if response.status_code >= 400:
        message = str(body.get("error") or body.get("message") or f"HTTP {response.status_code}")
        raise ProviderError(message, error_type="http_error", status_code=response.status_code)
    return response.status_code, body


class ProviderAdapter(ABC):
    def __init__(self, config: ProviderConfig, transport: HttpTransport = requests_transport) -> None:
        self.config = config
        self.transport = transport

    def _headers(self) -> dict[str, str]:
        headers = {"Accept": "application/json", "Content-Type": "application/json"}
        if self.config.api_key:
            headers["Authorization"] = f"Bearer {self.config.api_key}"
        return headers

    def _request(
        self, method: str, path: str, payload: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        if not self.config.configured:
            raise ProviderError("provider base URL is missing", error_type="configuration_error")
        _, body = self.transport(
            method,
            f"{self.config.base_url.rstrip('/')}/{path.lstrip('/')}",
            self._headers(),
            payload,
            self.config.timeout_seconds,
        )
        return body

    @abstractmethod
    def list_models(self) -> list[ModelRef]:
        raise NotImplementedError

    @abstractmethod
    def analyze(self, model: ModelRef, text: str) -> AnalysisResponse:
        raise NotImplementedError


class OpenAIAdapter(ProviderAdapter):
    def _headers(self) -> dict[str, str]:
        if not self.config.api_key:
            raise ProviderError("OpenAI API key is missing", error_type="configuration_error")
        return super()._headers()

    def list_models(self) -> list[ModelRef]:
        body = self._request("GET", "/models")
        data = body.get("data")
        if not isinstance(data, list):
            raise ProviderError("model list did not contain data", error_type="response_format_error")
        models = [
            ModelRef("OpenAI", "openai", item["id"], f"OpenAI : {item['id']}", dict(item))
            for item in data
            if isinstance(item, dict) and isinstance(item.get("id"), str) and item["id"].strip()
        ]
        return sorted(models, key=lambda item: item.model_id.casefold())

    def analyze(self, model: ModelRef, text: str) -> AnalysisResponse:
        if not text.strip():
            raise ValueError("analysis text is empty")
        body = self._request("POST", "/responses", {"model": model.model_id, "input": text, "store": False})
        output = _responses_text(body)
        if not output:
            raise ProviderError("Responses payload contained no output text", error_type="empty_response")
        return AnalysisResponse(
            raw_output=output,
            response_metadata={
                "endpoint": "responses",
                "id": body.get("id"),
                "model": body.get("model", model.model_id),
                "usage": body.get("usage"),
            },
        )


class OllamaAdapter(ProviderAdapter):
    def list_models(self) -> list[ModelRef]:
        body = self._request("GET", "/api/tags")
        data = body.get("models")
        if not isinstance(data, list):
            raise ProviderError("model list did not contain models", error_type="response_format_error")
        models: list[ModelRef] = []
        for item in data:
            if not isinstance(item, dict):
                continue
            model_id = str(item.get("name") or item.get("model") or "").strip()
            if model_id:
                models.append(
                    ModelRef(
                        self.config.provider,
                        self.config.provider_key,
                        model_id,
                        f"{self.config.provider} : {model_id}",
                        dict(item),
                    )
                )
        return sorted(models, key=lambda item: item.model_id.casefold())

    def analyze(self, model: ModelRef, text: str) -> AnalysisResponse:
        if not text.strip():
            raise ValueError("analysis text is empty")
        body = self._request(
            "POST",
            "/api/chat",
            {"model": model.model_id, "messages": [{"role": "user", "content": text}], "stream": False},
        )
        message = body.get("message")
        output = message.get("content") if isinstance(message, dict) else body.get("response")
        if not isinstance(output, str) or not output.strip():
            raise ProviderError("Ollama payload contained no output text", error_type="empty_response")
        return AnalysisResponse(raw_output=output, response_metadata={
            "model": body.get("model", model.model_id),
            "usage": {"input_tokens": body.get("prompt_eval_count"), "output_tokens": body.get("eval_count"),
                      "input_tokens_details": {"cached_tokens": body.get("prompt_eval_cached_count")}},
            "raw_usage": {key: body[key] for key in ("prompt_eval_count", "eval_count", "prompt_eval_cached_count") if key in body},
            "done": body.get("done"),
        })


def _responses_text(body: dict[str, Any]) -> str | None:
    direct = body.get("output_text")
    if isinstance(direct, str) and direct.strip():
        return direct
    parts: list[str] = []
    for item in body.get("output", []) if isinstance(body.get("output"), list) else []:
        if not isinstance(item, dict):
            continue
        for content in item.get("content", []) if isinstance(item.get("content"), list) else []:
            if isinstance(content, dict) and content.get("type") == "output_text" and isinstance(content.get("text"), str):
                parts.append(content["text"])
    return "\n".join(parts) if parts else None

