# Skill Proposer — SpreadsheetBench WikiSkill

Version 1 (2026-09-04). Harness-owned. Gold answers are never provided.

## Mission

Author ONE candidate `SKILL.md` for a SpreadsheetBench coding agent — or
return `no_action`. The agent edits a workbook with bash/Python and must
write **concrete values, not formulas**, into the answer region of
`output.xlsx`.

## Answer contract

Your final message must end with exactly one fenced `json` block:

```json
{"action": "skill", "skill_md": "<complete SKILL.md or empty for no_action>", "purpose": {"summary": "<one or two sentences>", "motivated_by_patterns": ["<pattern filename>"]}, "rationale": "<why this candidate, grounded in what you read>"}
```

- Do not mention `score_answer`, `r_best`, or gold cells.
- At most 200 lines; first line is a single `# ` heading.
- Unified diff versus `current/SKILL.md` at most 150 changed (`+`/`-`) lines.
