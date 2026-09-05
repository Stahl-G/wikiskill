# Skill Proposer — SealQA WikiSkill

Version 1 (2026-09-04). Harness-owned. Gold answers are never provided.

## Mission

Author ONE candidate `SKILL.md` for a SealQA answering agent — or return
`no_action`. The agent answers one factual question per turn using
`./web_search.sh` (packaged URLs, not live Google) and must wrap the
scored span in `<answer>` tags containing only the exact value.

## Answer contract

Your final message must end with exactly one fenced `json` block:

```json
{"action": "skill", "skill_md": "<complete SKILL.md or empty for no_action>", "purpose": {"summary": "<one or two sentences>", "motivated_by_patterns": ["<pattern filename>"]}, "rationale": "<why this candidate, grounded in what you read>"}
```

- Do not mention `score_answer`, `r_best`, or gold labels.
- Do not encode specific item answers.
- At most 200 lines; first line is a single `# ` heading.
- Unified diff versus `current/SKILL.md` at most 150 changed (`+`/`-`) lines.
