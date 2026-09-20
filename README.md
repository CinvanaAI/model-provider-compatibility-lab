# Model Provider Compatibility Lab

Record what a specific model/provider route actually did for a particular task and distinguish unsupported behavior from fixable configuration.

## Try it

Python 3.11+. Run from this checkout:

```sh
python -m pip install -e .
python -m examples.offline_demo
```

**Input:** Three fake HTTP outcomes for the same owner-extraction task: usable output, unknown model and a timeout.

**Result:** The actual adapter/ledger records supported, fixable and unknown states; returned token usage is retained, while unobserved inventory is null.

See [the captured example](examples/RESULT.md) for the observed output and reproduction command.

## How it works

An attempt establishes evidence only for one provider/model/task. Classification is separate from raw output, and a ledger record can inform selection without inventing capability from price or model names.

Source: [src/provider_compat/adapters.py](src/provider_compat/adapters.py), [src/provider_compat/lab.py](src/provider_compat/lab.py), [src/provider_compat/pricing.py](src/provider_compat/pricing.py).

## Use it for your work

Use `ProviderConfig` with your explicit endpoint and environment-derived credential, instantiate an adapter, and call `attempt_task`. Supply `can_list_models` only from an actual inventory observation. For task-quality comparisons, use [Rubric Rumble](https://github.com/CinvanaAI/rubric-rumble).

Follow the [evidence and selection guide](docs/EVIDENCE.md) to interpret a record, select candidates and recover from malformed local evidence.

## Scope

Supported means the call returned text; it is not a correctness grade. The ledger keeps the latest record per task, not full attempt history. Error-text classification is heuristic. No live endpoint or model availability is established by the fixture.

Owned code is available under the [MIT license](LICENSE.md).
