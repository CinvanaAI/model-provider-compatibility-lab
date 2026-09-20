# From one attempt to a selection decision

Run `python -m examples.offline_demo` first. Its transport is an in-memory fixture;
it exercises actual adapter normalization and ledger writing without contacting a
provider. The working route returns text and usage, the missing model is fixable,
and the timeout remains unknown. These outcomes concern this supplied task only.

| Status | What the attempt supports | Next decision |
| --- | --- | --- |
| `supported` | The adapter returned text | Evaluate task correctness separately |
| `unsupported` | The error text says unsupported | Inspect the actual request/error before ruling out a task |
| `fixable` | The error suggests credential, model or endpoint configuration | Correct that configuration and repeat the same task |
| `unknown` | No conclusive compatibility outcome | Preserve the failure and decide whether a retry is useful |

`attempt_task` returns an `AnalysisResponse` on success and re-raises the provider
exception after recording failure. Keep the returned `raw_output` and
`response_metadata` if the response itself matters: the compatibility ledger
stores status, not the raw successful response or usage. Errors can contain
private details; review before sharing them. `can_list_models=None` means no
inventory observation was supplied, not that listing is unsupported.

```python
from provider_compat import models_with_status

supported = models_with_status(
    observed_inventory, ledger.load(),
    task_name="extract_owner", statuses={"supported"},
)
```

Here `observed_inventory` is the list of `ModelRef` values your adapter actually
returned. Selection matches provider key, model ID and task name exactly. A route
that passed another task is not automatically included. `allowed_models` can
apply your own provider/model exclusions independently of observed status.

Records are latest-per-provider/model/task. Retrying that exact key replaces its
previous record; this is not a complete attempt archive, and selection does not
expire old evidence automatically. Preserve separate dated records if history
or freshness is part of your decision. Dated pricing is separate again: provide
rates and returned token counts explicitly, and treat missing usage as unknown,
not a free call. The bundled rates are synthetic examples, not current prices.

A missing ledger begins empty. An existing malformed/unreadable ledger now raises
instead of silently becoming empty on the next write. Preserve its bytes, inspect
or restore a known-good copy, and retry only after fixing it. This safeguard is
part of the public continuation. One writer per file is assumed; atomic replacement
does not resolve simultaneous independent updates.
