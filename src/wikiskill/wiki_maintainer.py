"""Structural WikiSkill agent contracts extracted from the original experiment.

See NOTICE.md for provenance. No model calls occur in this module.
"""

from __future__ import annotations

import json

import re

from dataclasses import dataclass

from pathlib import Path

from typing import Any, Mapping

from pydantic import BaseModel, ConfigDict, Field

_FILENAME_RE = re.compile('^[a-z0-9-]+\\.md$')

_FENCE_RE = re.compile('```(?:json)?[ \\t]*\\r?\\n(.*?)\\r?\\n```', re.DOTALL)

class MaintainerContractError(RuntimeError):
    """A Maintainer input, answer, or edit list violated the contract.

    Raised for: a missing prompt file, a non-train outcome row, an
    unparsable or schema-invalid answer, or any edit-list violation
    (filename regex, path escape, duplicate, unknown update target).
    Whenever it is raised during an iteration, no wiki edit from that
    iteration has been applied.
    """

class _Strict(BaseModel):
    model_config = ConfigDict(strict=True, extra='forbid', frozen=True, validate_default=True)

class NewPattern(_Strict):
    """A pattern page to create (structured; the harness renders the page)."""
    filename: str = Field(min_length=1)
    title: str = Field(min_length=1)
    summary: str = Field(min_length=1)
    evidence: list[str] = Field(default_factory=list)
    guidance: str = Field(min_length=1)

class UpdatedPattern(_Strict):
    """An existing pattern page replaced with the given full page text."""
    filename: str = Field(min_length=1)
    content: str = Field(min_length=1)

class LogEntry(_Strict):
    """The iteration narrative appended to ``logs.md``."""
    narrative: str = Field(min_length=1)

class MaintainerAnswer(_Strict):
    """The Maintainer's complete, strict-JSON edit list."""
    new_patterns: list[NewPattern] = Field(default_factory=list)
    updated_patterns: list[UpdatedPattern] = Field(default_factory=list)
    log_entry: LogEntry

@dataclass(frozen=True)
class MaintainerResult:
    """What one Maintainer iteration did, for the audit chain."""
    iteration: int
    new_patterns: tuple[str, ...]
    updated_patterns: tuple[str, ...]
    prompt_sha256: str
    sampled_case_ids: tuple[str, ...]
    stdout_path: Path

def parse_maintainer_answer(stdout: str) -> MaintainerAnswer:
    """Parse the Maintainer's stdout into a validated ``MaintainerAnswer``.

    The answer is one strict JSON object.  A fenced ```` ```json ````
    block is tolerated (and preferred when prose surrounds it); a bare
    trailing JSON object on otherwise-empty stdout is accepted too.
    Anything else -- prose with no parsable object, an array, a scalar,
    or an object that fails the strict schema -- raises
    ``MaintainerContractError`` naming the violation.
    """
    candidates: list[str] = []
    text = stdout.strip()
    for match in _FENCE_RE.finditer(text):
        candidates.append(match.group(1))
    if text:
        candidates.append(text)
    payload: Any = None
    for candidate in candidates:
        try:
            parsed = json.loads(candidate)
        except json.JSONDecodeError:
            continue
        if isinstance(parsed, dict):
            payload = parsed
            break
    if payload is None:
        raise MaintainerContractError('maintainer answer is not a JSON object: no parsable JSON object (bare or in a fenced ```json block) was found in stdout')
    payload = _promote_structured_updates(payload)
    try:
        return MaintainerAnswer.model_validate(payload)
    except Exception as exc:
        raise MaintainerContractError(f'maintainer answer violates the output contract: {exc}') from exc

def _promote_structured_updates(payload: dict[str, Any]) -> dict[str, Any]:
    """Accept NewPattern-shaped items in updated_patterns as full-page replacements.

    Maintainers sometimes reuse the create-shape (title/summary/guidance) when
    revising an existing page. That is still a complete page, not a missing
    edit. Filename-only updates remain a contract error.
    """
    updates = payload.get('updated_patterns')
    if not isinstance(updates, list):
        return payload
    promoted: list[Any] = []
    for item in updates:
        if isinstance(item, dict) and (not str(item.get('content') or '').strip()) and item.get('filename') and item.get('title') and item.get('summary') and item.get('guidance'):
            pattern = NewPattern.model_validate({'filename': item['filename'], 'title': item['title'], 'summary': item['summary'], 'evidence': item.get('evidence') or [], 'guidance': item['guidance']})
            promoted.append({'filename': pattern.filename, 'content': _render_pattern_page(pattern)})
        else:
            promoted.append(item)
    return {**payload, 'updated_patterns': promoted}

def _check_filename(filename: str, *, kind: str) -> None:
    if not _FILENAME_RE.match(filename):
        raise MaintainerContractError(f'{kind} filename {filename!r} violates ^[a-z0-9-]+\\.md$ (path escapes, subdirectories, and uppercase are forbidden)')

def _render_pattern_page(pattern: NewPattern) -> str:
    lines = [f'# {pattern.title}', '', f'Summary: {pattern.summary}', '', '## Evidence', '']
    evidence_lines = [f'- {ref}' for ref in pattern.evidence]
    if not evidence_lines:
        evidence_lines = ['- (no case references recorded)']
    lines += evidence_lines
    lines += ['', '## Guidance', '', pattern.guidance, '']
    return '\n'.join(lines)

def _page_title_summary(content: str, *, filename: str) -> tuple[str, str]:
    """First heading and ``Summary:`` line of a page, with fallbacks."""
    title = ''
    summary = ''
    for line in content.splitlines():
        if not title:
            match = re.match('^#\\s+(.+?)\\s*$', line)
            if match:
                title = match.group(1)
        if not summary:
            match = re.match('^Summary:\\s*(.*)$', line)
            if match:
                summary = match.group(1).strip()
        if title and summary:
            break
    if not title:
        title = filename[:-len('.md')]
    return (title, summary)

def _regenerate_index(wiki_dir: Path) -> None:
    """Rewrite ``index.md`` from the union of pattern pages on disk."""
    patterns_dir = wiki_dir / 'patterns'
    rows: list[tuple[str, str, str]] = []
    if patterns_dir.is_dir():
        for path in sorted(patterns_dir.glob('*.md')):
            title, summary = _page_title_summary(path.read_text(encoding='utf-8'), filename=path.name)
            rows.append((path.name, title, summary))
    lines = ['# Wiki Index', '', '<!-- maintained by the Wiki Maintainer; never hand-edited -->', '', '| Pattern | Summary |', '|---|---|']
    for filename, title, summary in rows:
        escaped = summary.replace('|', '\\|')
        lines.append(f'| [{title}](patterns/{filename}) | {escaped} |')
    (wiki_dir / 'index.md').write_text('\n'.join(lines) + '\n', encoding='utf-8')

def _append_log_entry(wiki_dir: Path, entry: LogEntry, *, iteration: int) -> None:
    logs = wiki_dir / 'logs.md'
    header = '# Evolution Log\n'
    existing = logs.read_text(encoding='utf-8') if logs.is_file() else header
    if not existing.endswith('\n'):
        existing += '\n'
    block = f'\n## Iteration {iteration}\n\n{entry.narrative.strip()}\n'
    logs.write_text(existing + block, encoding='utf-8')

def apply_pattern_edits(wiki_dir: Path, answer: MaintainerAnswer, *, iteration: int) -> tuple[list[str], list[str]]:
    """Validate the whole edit list, then apply it; all or nothing.

    Validation (every violation raises ``MaintainerContractError`` and
    applies nothing): filenames must match ``^[a-z0-9-]+\\.md$`` (which
    structurally forbids ``../`` escapes, absolute paths, and
    subdirectories); filenames must be unique within and across the new
    and updated lists; a new page must not already exist (an update is
    the only legal way to change an existing page); an updated page must
    already exist (updates are in-place full-content replacements).

    Application: new pages are rendered from their structured fields
    under ``patterns/``; updated pages are overwritten with the supplied
    full text; ``index.md`` is regenerated from the union of pattern
    files then on disk; the narrative is appended to ``logs.md`` under
    an iteration header.  Returns ``(new_filenames, updated_filenames)``
    in answer order.
    """
    patterns_dir = wiki_dir / 'patterns'
    new_files: list[str] = []
    for pattern in answer.new_patterns:
        _check_filename(pattern.filename, kind='new_patterns')
        if pattern.filename in new_files:
            raise MaintainerContractError(f'new_patterns lists filename {pattern.filename!r} twice')
        if (patterns_dir / pattern.filename).exists():
            raise MaintainerContractError(f'new_patterns filename {pattern.filename!r} already exists; revise it through updated_patterns instead')
        new_files.append(pattern.filename)
    updated_files: list[str] = []
    for pattern in answer.updated_patterns:
        _check_filename(pattern.filename, kind='updated_patterns')
        if pattern.filename in updated_files:
            raise MaintainerContractError(f'updated_patterns lists filename {pattern.filename!r} twice')
        if pattern.filename in new_files:
            raise MaintainerContractError(f'filename {pattern.filename!r} appears as both new and updated in one edit list')
        if not (patterns_dir / pattern.filename).exists():
            raise MaintainerContractError(f'updated_patterns filename {pattern.filename!r} does not exist under patterns/; only existing pages may be updated')
        updated_files.append(pattern.filename)
    patterns_dir.mkdir(parents=True, exist_ok=True)
    for pattern in answer.new_patterns:
        target = patterns_dir / pattern.filename
        target.write_text(_render_pattern_page(pattern), encoding='utf-8')
    for pattern in answer.updated_patterns:
        target = patterns_dir / pattern.filename
        target.write_text(pattern.content, encoding='utf-8')
    _regenerate_index(wiki_dir)
    _append_log_entry(wiki_dir, answer.log_entry, iteration=iteration)
    return (new_files, updated_files)
