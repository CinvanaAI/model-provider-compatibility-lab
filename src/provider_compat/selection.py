"""Selection rules that consume evidence without changing its meaning."""

from __future__ import annotations

from typing import Any

from .types import ModelRef


def models_with_status(
    models: list[ModelRef],
    ledger_payload: dict[str, Any],
    *,
    task_name: str,
    statuses: set[str],
) -> list[ModelRef]:
    allowed = {
        (str(record.get("provider_key", "")), str(record.get("model_id", "")))
        for record in ledger_payload.get("records", [])
        if isinstance(record, dict)
        and record.get("task_name") == task_name
        and record.get("status") in statuses
    }
    return [model for model in models if (model.provider_key, model.model_id) in allowed]


def allowed_models(
    models: list[ModelRef],
    *,
    include_providers: set[str] | None = None,
    exclude_providers: set[str] | None = None,
    exclude_models: set[tuple[str, str]] | None = None,
) -> list[ModelRef]:
    included = include_providers
    excluded_providers = exclude_providers or set()
    excluded_models = exclude_models or set()
    return [
        model
        for model in models
        if (included is None or model.provider_key in included)
        and model.provider_key not in excluded_providers
        and (model.provider_key, model.model_id) not in excluded_models
    ]

