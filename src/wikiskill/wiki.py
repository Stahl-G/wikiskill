"""Wiki layer harness: the B'' loop's persistent, never-rolled-back memory.

The wiki lives at ``evaluation/wiki/`` as plain markdown (patterns,
index, logs) plus one machine-appended audit file, ``skill-impact.md``.
This module owns ONLY the programmatic side: appending one structured
skill-impact entry per gating outcome and reading the wiki back for the
agents.  Pattern pages themselves are written by the Wiki Maintainer
agent through its JSON edit list -- never directly by this harness.

An entry is a fenced ``json`` block, human-readable in place and
strictly parseable: the Skill Proposer reads these to avoid re-proposing
failed interventions (the paper's skill-impact tracker), and the audit
chain (pre-registration block, proposal diff, component scores, gate
verdict, acceptance) is the G2 record.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

WIKI_DIR = Path("evaluation/wiki")
SKILL_IMPACT_PATH = WIKI_DIR / "skill-impact.md"


class _Strict(BaseModel):
    model_config = ConfigDict(
        strict=True, extra="forbid", frozen=True, validate_default=True
    )


class PreRegistration(_Strict):
    """The gate inputs frozen BEFORE the candidate val runs."""

    target_component: Literal["tnr", "defect_recall", "paper_eq4"]
    minimum_effect: int = Field(ge=1)
    protocol_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    pair_id: str = Field(min_length=1)


class SkillImpactEntry(_Strict):
    """One gating outcome, appended verbatim to ``skill-impact.md``."""

    schema_version: Literal["wikiskill.skill_impact.v1"]
    iteration: int = Field(ge=1)
    recorded_at: str
    prereg: PreRegistration
    proposal_kind: Literal["skill", "no_action"]
    skill_sha256: str = Field(default="", pattern=r"^(|[0-9a-f]{64})$")
    purpose_summary: str = ""
    motivated_by_patterns: list[str] = Field(default_factory=list)
    unified_diff: str = ""
    incumbent_skill_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    # Descriptive component scores per arm (never the acceptance input).
    incumbent_descriptive: dict[str, float] = Field(default_factory=dict)
    candidate_descriptive: dict[str, float] = Field(default_factory=dict)
    gate_verdict: Literal[
        "ACCEPT", "REJECT", "NEEDS_CONFIRMATION", "NOT_GATED", "INFRA_FAILURE"
    ]
    gate_p_value: float | None = Field(default=None, ge=0.0, le=1.0)
    gate_b: int = Field(default=0)
    gate_c: int = Field(default=0)
    hard_guard_summary: str = ""
    soft_budget_summary: str = ""
    accepted: bool
    notes: str = ""


def append_skill_impact(
    path: Path = SKILL_IMPACT_PATH, entry: SkillImpactEntry | None = None, **fields: Any
) -> None:
    """Append exactly one entry; the impact log is never rewritten."""
    if entry is None:
        entry = SkillImpactEntry(**fields)
    path.parent.mkdir(parents=True, exist_ok=True)
    block = f"```json\n{entry.model_dump_json(indent=2)}\n```"
    with path.open("a", encoding="utf-8") as handle:
        handle.write(
            f"\n<!-- iteration {entry.iteration}: "
            f"{entry.proposal_kind} -> {entry.gate_verdict}"
            f"{' ACCEPTED' if entry.accepted else ''} -->\n{block}\n"
        )


def _impact_mirror_key(entry: SkillImpactEntry) -> tuple[str, str, str]:
    """INFRA then ACCEPT/REJECT share a pair_id; both must stay visible."""
    return (entry.prereg.pair_id, entry.gate_verdict, entry.recorded_at)


def mirror_skill_impacts(private_path: Path, public_path: Path) -> list[SkillImpactEntry]:
    """Append private entries that public does not already have.

    Key is (pair_id, gate_verdict, recorded_at) so a later Eq.4 gate after
    INFRA_FAILURE is not dropped. The public file stays append-only.
    """
    public_keys = {_impact_mirror_key(entry) for entry in load_skill_impacts(public_path)}
    mirrored: list[SkillImpactEntry] = []
    if not private_path.is_file():
        return mirrored
    for entry in load_skill_impacts(private_path):
        key = _impact_mirror_key(entry)
        if key in public_keys:
            continue
        append_skill_impact(public_path, entry)
        public_keys.add(key)
        mirrored.append(entry)
    return mirrored


def load_skill_impacts(path: Path = SKILL_IMPACT_PATH) -> list[SkillImpactEntry]:
    """Parse every entry; a malformed log is an error, not a partial read."""
    if not path.exists():
        return []
    entries: list[SkillImpactEntry] = []
    text = path.read_text(encoding="utf-8")
    starts = [i for i in range(len(text)) if text.startswith("```json\n", i)]
    for ordinal, start in enumerate(starts, start=1):
        end = text.find("\n```", start)
        if end == -1:
            raise ValueError(f"skill-impact entry {ordinal} is unterminated")
        payload = text[start + len("```json\n") : end]
        try:
            entries.append(SkillImpactEntry.model_validate(json.loads(payload)))
        except Exception as exc:  # noqa: BLE001 - surfaced as log error
            raise ValueError(f"skill-impact entry {ordinal} is invalid: {exc}") from exc
    return entries


def wiki_snapshot(wiki_dir: Path = WIKI_DIR) -> dict[str, str]:
    """Read the full wiki (index, patterns, logs, skill-impact) as text.

    This is the Maintainer's read surface: everything the loop remembers,
    in one mapping keyed by repo-relative path.
    """
    if not wiki_dir.exists():
        return {}
    snapshot: dict[str, str] = {}
    for path in sorted(wiki_dir.rglob("*.md")):
        if "prompts" in path.parts:
            continue  # harness-owned prompt files are not loop memory
        snapshot[path.relative_to(wiki_dir).as_posix()] = path.read_text(
            encoding="utf-8"
        )
    return snapshot
