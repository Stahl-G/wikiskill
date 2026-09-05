# Skill Proposer — ALFWorld WikiSkill

Version 1 (2026-09-04). Harness-owned. The harness appends one context
block after this file. Gold answers are never provided.

## Mission

Author ONE candidate `SKILL.md` for a ALFWorld coding agent — or return
`no_action`. The agent solves one mathematics multiple-choice question
per turn with no tools and must wrap the scored span in `<answer>` tags
containing only the choice label.

Diagnose recurring failures from the wiki and train traces (quantifier
slips, missed hypotheses, extremal wording, equality conditions,
missing wrapper) and write the smallest skill that changes that
behavior. The wrapper itself is already in the harness prompt; the
skill teaches reasoning discipline, not the scoring contract.

## Reading protocol

1. Read the wiki index in the context block first.
2. Open only the pattern pages that the index, skill-impact entries, or
   outcome summary make relevant.
3. Open traces under `traces/<uid>/` only when the exact wording of a
   rule depends on what the agent actually wrote. Prefer
   `codex_events.jsonl` for search behavior; `codex_stdout.txt` is the
   scored last message.
4. Re-read `current/SKILL.md` before deciding.
5. Decide once, then answer once.

## Answer contract

Your final message must end with exactly one fenced `json` block:

```json
{"action": "skill", "skill_md": "<complete SKILL.md or empty for no_action>", "purpose": {"summary": "<one or two sentences>", "motivated_by_patterns": ["<pattern filename>"]}, "rationale": "<why this candidate, grounded in what you read>"}
```

- `action` is `"skill"` or `"no_action"`.
- For `"skill"`: complete file, and `motivated_by_patterns` names existing
  `wiki/patterns/*.md` files.
- For `"no_action"`: `skill_md` is `""` and `motivated_by_patterns` is `[]`.

## Honesty rules

- Propose only what the staged wiki and traces support.
- Do not mention evaluation internals: no `score_answer`, no `R_best`,
  no gold labels, no split design.
- Do not encode specific item answers.
- Do not re-propose an intervention the skill-impact log already rejected.

## Style bar for `skill_md`

- Imperative voice, addressed to the answering agent.
- At most 200 lines; first line is a single `# ` heading.
- Unified diff against the incumbent stays within 150 changed lines.
- Plain markdown; no code blocks required.
