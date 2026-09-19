# Origin and extraction

This package isolates provider inventory, execution normalization, compatibility
classification, pricing separation, and selection rules from two generations
of the lab's transcript evaluation tools.

The public extraction uses newly written package boundaries and synthetic
examples while preserving the core idea: compatibility is evidence from an
actual provider/model/task attempt, not an inherited claim about a model name.
No original credentials, provider envelopes, pricing database, or attempt
history were copied.

The current integrated parent is `transcript-model-evaluator`; this focused
repository exists so its provider/model/task evidence rules can be inspected
and reused without the desktop application.
