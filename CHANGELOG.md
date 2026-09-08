# Changelog

## 0.1.1

- Native Codex and Claude Code role assets and a coordinating entry skill. Fresh task executors, Wiki Maintainer and Skill Proposer use separate context handoffs; the host's native tools create the agents.
- `agents install`, `dispatch`, `bind-agent`, `collect` and `fail` connect native execution to existing scoring and gates. Per-request agent IDs are recorded, duplicate IDs are rejected, and scoring retries reuse saved output.
- Readiness checks, readable progress, journal-derived reports and explicit local skill installation with backups/restoration.
- A public workbook-delivery example and recorded independent product-use checks.
- Shared finite-score and strict-improvement rules. Missing research scores no longer become zero; historical records are unchanged. New product inputs are content-bound, and checker changes cannot silently mix scoring conditions.
- Codex native workflow verification and separate Claude configuration support/validation disclosure. No new model API/backend, permission override or benchmark-isolation claim.

## 0.1.0

Initial independent implementation and host-agent product workflow, with task scoring, persistent Wiki, validation-gated skills, human feedback, local scorer trust and research artifacts.
