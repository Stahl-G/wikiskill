# Native subagent workflow — v0.1.1

The main host agent is the coordinator. WikiSkill prepares role-specific files; the host creates fresh subagents, waits and submits their artifacts. The Python CLI does not call a model, create an external CLI session or impersonate a native tool.

## Boundaries and controls

- Each baseline, training and candidate-validation task receives a new executor context. Its payload has only the task, selected skill and output directory. It does not include the Wiki, earlier answers, baseline feedback or reserved scoring fields.
- Maintainer receives training records, Wiki and human feedback. Proposer is dispatched only after that Wiki submission has been accepted by the controller. Learning handoffs include aggregate gate summaries, not per-question validation outputs.
- The coordinator sends the generated handoff message rather than summarizing task answers or its own reasoning into the child prompt. Children write draft files; controller submission remains with the coordinator.
- Native-mode submissions require a bound host ID. Different requests cannot reuse a child ID. A scoring retry reuses the original saved execution and records that reuse explicitly, without claiming another fresh inference.
- Host IDs and context mode are host-reported provenance. They do not independently attest to context isolation. Host policies, project instructions, memory and filesystem access remain in force.
- The existing direct-host interface remains for explicitly chosen integrations. It cannot silently switch into native mode mid-comparison. Missing native tools require a disclosed stop or a separately authorized, clearly labeled direct workflow.

## Actual verification

### Codex desktop native tools

A small real workflow used five calls to the available `spawn_agent` tool, each with `fork_turns="none"` and a distinct returned agent ID:

| Phase | Execution |
|---|---|
| Baseline | Fresh executor, actual output scored 1.0 |
| Training | Different fresh executor, actual output scored 1.0 |
| Wiki maintenance | Fresh Maintainer, source-bound patterns submitted |
| Proposal | Fresh Proposer, given the newly committed Wiki |
| Candidate validation | Different fresh executor, actual output scored 1.0 |

The gate returned REJECT for the 1.0/1.0 tie and preserved the Wiki and candidate record. The coordinator received output paths, bound actual IDs and used collect; it did not write the role outputs. The task set was one learning/one validation item from the public text-cleanup example. This is protocol verification, not a performance result.

This app session used the generic native role with the generated role instructions, because newly installed custom role names are not dynamically added to its exposed tool list. The shipped Codex TOML assets were syntax/installation checked, not claimed as a separately exercised custom-role loader. The installed standalone Codex CLI reported 0.146.0; that separate CLI was not used to launch this workflow.

### Claude Code

The installed Claude Code reported 2.1.224. All three custom-agent Markdown definitions and the coordinating skill were installed in a temporary project and parsed with required names/descriptions and inherited models. No permission bypass, model override or persistent role memory was configured.

`claude plugin validate` in this version accepts plugin manifests, not standalone agents directories; its attempted directory check returned “No manifest found.” This is not reported as a successful host loading test. The official documentation describes agents-directory validation in newer versions. **Claude live inference and end-to-end native delegation have not been verified in this release.** No model call was made merely to turn this configuration check green.

### Software checks

Focused cases verify handoff field boundaries, Maintainer-before-Proposer sequencing, required binding, duplicate IDs, cross-request output rejection, repeated collection, no-action, role failure/retry, saved-output scoring retry, runtime mismatch and preserving existing host assets. Source and installed-package paths use the same packaged role assets. `scripts/sync_native_assets.py --check` verifies generated definitions and the packaged entry skill against their source files.

## Official references

- [Codex subagents and custom TOML agents](https://learn.chatgpt.com/docs/agent-configuration/subagents)
- [Claude Code custom subagents, context and inheritance](https://code.claude.com/docs/en/sub-agents)

The exact tool schema exposed by the running host takes precedence over copied invocation examples. Use an ordinary fresh Claude subagent, not a conversation fork. In Codex, verify the available fresh-context control rather than assuming all versions expose the desktop `fork_turns` parameter.
