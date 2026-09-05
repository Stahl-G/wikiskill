"""Structural WikiSkill agent contracts extracted from the original experiment.

See NOTICE.md for provenance. No model calls occur in this module.
"""

from __future__ import annotations

import difflib

import json

import re

from pathlib import Path

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError

_JSON_FENCE_RE = re.compile('```json[^\\n]*\\n(.*?)```', re.DOTALL)

_BARE_FENCE_RE = re.compile('```[^\\n]*\\n(.*?)```', re.DOTALL)

class ProposerContractError(Exception):
    """A structural validator rejected the proposal; nothing was applied."""

class _Strict(BaseModel):
    model_config = ConfigDict(strict=True, extra='forbid', frozen=True, validate_default=True)

class ProposalPurpose(_Strict):
    """What the candidate is for, and which wiki patterns motivated it."""
    summary: str = ''
    motivated_by_patterns: list[str] = Field(default_factory=list)

class ProposalResult(_Strict):
    """One validated proposal plus the identity of the run that made it."""
    action: Literal['skill', 'no_action']
    skill_md: str
    purpose: ProposalPurpose
    rationale: str
    prompt_sha256: str = Field(pattern='^[0-9a-f]{64}$')
    diff: str
    stdout_path: Path

def _extract_answer(stdout: str) -> dict[str, Any]:
    """Parse the answer object; fenced-block tolerant.

    Prefers the LAST ```` ```json ```` fence (the prompt demands exactly
    one at the end), falls back to a bare fence, then to the raw text.
    """
    blocks = _JSON_FENCE_RE.findall(stdout)
    if not blocks:
        blocks = _BARE_FENCE_RE.findall(stdout)
    text = blocks[-1] if blocks else stdout
    try:
        payload = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ProposerContractError(f'answer is not parseable JSON: {exc}') from exc
    if not isinstance(payload, dict):
        raise ProposerContractError(f'answer must be a JSON object, got {type(payload).__name__}')
    return payload

def _required_string(answer: dict[str, Any], key: str) -> str:
    if key not in answer:
        raise ProposerContractError(f'answer is missing required key {key!r}')
    value = answer[key]
    if not isinstance(value, str):
        raise ProposerContractError(f'answer key {key!r} must be a string, got {type(value).__name__}')
    return value

def _unified_diff(incumbent: str, skill_md: str) -> str:
    diff = difflib.unified_diff(incumbent.splitlines(), skill_md.splitlines(), fromfile='current/SKILL.md', tofile='proposed/SKILL.md', lineterm='')
    return '\n'.join(diff)

def _changed_line_count(diff_text: str) -> int:
    return sum((1 for line in diff_text.splitlines() if (line.startswith('+') or line.startswith('-')) and (not line.startswith(('+++', '---')))))
