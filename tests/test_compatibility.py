from __future__ import annotations

from datetime import datetime, timezone

import pytest

from provider_compat import (
    CompatibilityLedger,
    ModelRef,
    OllamaAdapter,
    OpenAIAdapter,
    PricingRecord,
    ProviderConfig,
    ProviderError,
    allowed_models,
    attempt_task,
    classify_failure,
    estimate_cost,
    is_stale,
    models_with_status,
)
from provider_compat.evidence import evidence_from_failure, evidence_from_success


def model(model_id: str, provider_key: str = "openai") -> ModelRef:
    provider = "OpenAI" if provider_key == "openai" else "Ollama Local"
    return ModelRef(provider, provider_key, model_id, f"{provider} : {model_id}")


@pytest.mark.parametrize(
    ("error", "status"),
    [
        (ProviderError("API key is missing"), "fixable"),
        (ProviderError("unknown model", status_code=404), "fixable"),
        (ProviderError("task not supported"), "unsupported"),
        (TimeoutError("timed out"), "unknown"),
        (RuntimeError("strange failure"), "unknown"),
    ],
)
def test_failure_classification_is_bounded(error: BaseException, status: str) -> None:
    assert classify_failure(error)[0] == status


def test_ledger_upsert_keeps_latest_record_per_task(tmp_path) -> None:
    ledger = CompatibilityLedger(tmp_path / "ledger.json")
    ledger.upsert(evidence_from_failure("openai", "m1", "text", RuntimeError("offline"), can_list_models=True))
    ledger.upsert(evidence_from_success("openai", "m1", "text"))
    records = ledger.load()["records"]
    assert len(records) == 1
    assert records[0]["status"] == "supported"


def test_selection_reads_status_without_reclassifying() -> None:
    models = [model("good"), model("retry"), model("other", "ollama_local")]
    ledger = {
        "records": [
            {"provider_key": "openai", "model_id": "good", "task_name": "text", "status": "supported"},
            {"provider_key": "openai", "model_id": "retry", "task_name": "text", "status": "fixable"},
        ]
    }
    assert [item.model_id for item in models_with_status(models, ledger, task_name="text", statuses={"supported"})] == ["good"]
    assert [item.model_id for item in allowed_models(models, include_providers={"openai"}, exclude_models={("openai", "retry")})] == ["good"]


def test_pricing_is_dated_and_separate() -> None:
    record = PricingRecord("demo", "m", 2.0, 4.0, "synthetic", "2026-01-01T00:00:00+00:00")
    estimate = estimate_cost(record, input_tokens=500_000, output_tokens=250_000)
    assert estimate.input_cost == 1.0
    assert estimate.output_cost == 1.0
    assert estimate.total_cost == 2.0
    assert is_stale(record, now=datetime(2026, 1, 20, tzinfo=timezone.utc)) is True


def test_openai_adapter_lists_and_analyzes_with_responses_api() -> None:
    calls: list[tuple[str, str, object]] = []

    def transport(method, url, headers, payload, timeout):
        calls.append((method, url, payload))
        if method == "GET":
            return (200, {"data": [{"id": "gpt-b"}, {"id": "gpt-a"}]})
        return (
            200,
            {
                "id": "r1",
                "model": "gpt-a",
                "output": [{"type": "message", "content": [{"type": "output_text", "text": "ok"}]}],
            },
        )

    adapter = OpenAIAdapter(
        ProviderConfig("OpenAI", "openai", "https://example.invalid/v1", "test-key"),
        transport,
    )
    models = adapter.list_models()
    response = adapter.analyze(models[0], "synthetic input")
    assert [entry.model_id for entry in models] == ["gpt-a", "gpt-b"]
    assert response.raw_output == "ok"
    assert calls[1][1].endswith("/responses")
    assert calls[1][2] == {"model": "gpt-a", "input": "synthetic input", "store": False}


def test_ollama_adapter_normalizes_inventory_and_chat() -> None:
    def transport(method, url, headers, payload, timeout):
        if method == "GET":
            return (200, {"models": [{"name": "qwen"}]})
        return (200, {"model": "qwen", "message": {"content": "local result"}})

    adapter = OllamaAdapter(
        ProviderConfig("Ollama Local", "ollama_local", "http://localhost:11434"),
        transport,
    )
    selected = adapter.list_models()[0]
    assert adapter.analyze(selected, "synthetic").raw_output == "local result"


def test_attempt_runner_records_success_and_rethrows_failure(tmp_path) -> None:
    responses = [
        (200, {"output_text": "worked"}),
        ProviderError("task not supported"),
    ]

    def transport(method, url, headers, payload, timeout):
        value = responses.pop(0)
        if isinstance(value, BaseException):
            raise value
        return value

    adapter = OpenAIAdapter(
        ProviderConfig("OpenAI", "openai", "https://example.invalid/v1", "test-key"),
        transport,
    )
    ledger = CompatibilityLedger(tmp_path / "ledger.json")
    selected = model("gpt-test")
    assert attempt_task(adapter, selected, "text", "first", ledger).raw_output == "worked"
    with pytest.raises(ProviderError):
        attempt_task(adapter, selected, "tools", "second", ledger)
    records = ledger.load()["records"]
    assert {(entry["task_name"], entry["status"]) for entry in records} == {
        ("text", "supported"),
        ("tools", "unsupported"),
    }



@pytest.mark.parametrize("content", ['{broken', '[]', '{"records":{}}', '{"records":[null]}', '{"records":[{"provider_key":"x"}]}'])
def test_upsert_preserves_invalid_existing_ledger(tmp_path, content):
    path = tmp_path / "ledger.json"
    path.write_text(content, encoding="utf-8")
    before = path.read_bytes()
    with pytest.raises(ValueError):
        CompatibilityLedger(path).upsert(evidence_from_success("demo", "m", "text"))
    assert path.read_bytes() == before


@pytest.mark.parametrize("changes", [{"status": "success"}, {"model_id": ""}, {"provider_key": None}])
def test_invalid_incoming_evidence_cannot_poison_existing_ledger(tmp_path, changes):
    from dataclasses import replace
    ledger = CompatibilityLedger(tmp_path / "ledger.json")
    valid = evidence_from_success("demo", "model", "text")
    ledger.upsert(valid)
    before = ledger.path.read_bytes()
    with pytest.raises(ValueError, match="invalid evidence"):
        ledger.upsert(replace(valid, **changes))
    assert ledger.path.read_bytes() == before
    assert ledger.load()["records"][0]["status"] == "supported"
