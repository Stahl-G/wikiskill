# Changelog

## 0.2.0

- MCP server: `python -m pip install 'wikiskill-research[mcp] @ git+https://github.com/Stahl-G/wikiskill.git'` and `wikiskill mcp` expose the host-agent workflow (start, next, record, learn, propose, feedback, retry, status, report, preflight, scorer inspection, export, capabilities) to any MCP client. Tools accept output, pattern and skill text directly and make no model calls. Scorer authorization, skill installation and restoration remain terminal-only.
- Feedback-first host API: `wikiskill.feedback_loop.begin/work/finish` starts Wiki maintenance from saved user revisions and comments, with host-supplied paired comparisons and an optional better-than-worse adoption policy. Numeric scoring is unchanged.
- Portable Python scorers: `{python}` in a scorer command resolves to WikiSkill's own interpreter.
- Research adapters: `engine.evolve()` accepts `domain_loader`, `maintainer_factory` and `proposer_factory`; `engine.initialize()` accepts a Wiki template and role prompts. `paper_alignment.PaperAgents` runs the paper's appendix Maintainer and Proposer prompts on TRAIN-only evidence and requires four actual trace reads before a proposal. The engine still owns validation selection, rollback and the journal.
- Documentation: [paper-to-code conformance map](docs/paper-conformance.md) and a README section on WikiSkill inside BriefLoop.
- Package version drops the local `+briefloop` suffix. No research result was remeasured; historical records are unchanged.

## 0.1.1

- Native Codex and Claude Code role assets and a coordinating entry skill. Fresh task executors, Wiki Maintainer and Skill Proposer use separate context handoffs; the host's native tools create the agents.
- `agents install`, `dispatch`, `bind-agent`, `collect` and `fail` connect native execution to existing scoring and gates. Per-request agent IDs are recorded, duplicate IDs are rejected, and scoring retries reuse saved output.
- Readiness checks, readable progress, journal-derived reports and explicit local skill installation with backups/restoration.
- A public workbook-delivery example and recorded independent product-use checks.
- Shared finite-score and strict-improvement rules. Missing research scores no longer become zero; historical records are unchanged. New product inputs are content-bound, and checker changes cannot silently mix scoring conditions.
- Codex native workflow verification and separate Claude configuration support/validation disclosure. No new model API/backend, permission override or benchmark-isolation claim.

## 0.1.0

Initial independent implementation and host-agent product workflow, with task scoring, persistent Wiki, validation-gated skills, human feedback, local scorer trust and research artifacts.
