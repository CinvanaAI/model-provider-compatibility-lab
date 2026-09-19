"""Normalized provider inventory, response, and evidence types."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class ProviderConfig:
    provider: str
    provider_key: str
    base_url: str
    api_key: str | None = None
    timeout_seconds: float = 90.0

    @property
    def configured(self) -> bool:
        return bool(self.base_url.strip())


@dataclass(frozen=True)
class ModelRef:
    provider: str
    provider_key: str
    model_id: str
    display_label: str
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class AnalysisResponse:
    raw_output: str
    response_metadata: dict[str, Any]


@dataclass(frozen=True)
class AttemptEvidence:
    provider_key: str
    model_id: str
    task_name: str
    status: str
    attempted_at: str
    can_list_models: bool | None
    can_execute_task: bool
    blocked_reason: str | None = None
    fix_hint: str | None = None
    error_type: str | None = None
    error_message: str | None = None


class ProviderError(RuntimeError):
    def __init__(
        self,
        message: str,
        *,
        error_type: str = "provider_error",
        status_code: int | None = None,
    ) -> None:
        super().__init__(message)
        self.error_type = error_type
        self.status_code = status_code

