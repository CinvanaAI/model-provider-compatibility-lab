# Security

Provider envelopes and failure messages can contain submitted text, account
metadata, or echoed credentials. This package stores normalized evidence only;
raw envelopes should be retained separately under an explicit privacy policy.

- Keep provider keys in the environment.
- The demo and tests are synthetic and offline.
- Evidence files are ignored by default.
- Pricing records are user-supplied and carry source/date metadata; they are
  never treated as live solely because the software was run recently.

