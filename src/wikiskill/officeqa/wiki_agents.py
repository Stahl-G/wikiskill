"""OfficeQA Wiki Maintainer and Skill Proposer.

Same JSON edit / skill contracts as the auditor wiki agents, with an
OfficeQA outcome schema and a separate wiki tree.  Gold answers never
enter prompts or staged traces.
"""

from __future__ import annotations

import hashlib
import json
import shutil
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from wikiskill.officeqa.rollout import (
    SCRATCH_DIR,
    run_codex_exec,
)
from wikiskill.skill_proposer import (
    ProposalPurpose,
    ProposalResult,
    ProposerContractError,
    _changed_line_count,
    _extract_answer,
    _required_string,
    _unified_diff,
)

# Non-audit WikiSkill domains only. Audit-domain skill_proposer.py keeps
# 80 / 60. Paper Table 4 reports evolved skills averaging 84.6–142.5
# lines; the audit caps truncate that proposal distribution.
MAX_SKILL_LINES = 200
MAX_DIFF_CHANGED_LINES = 150
from wikiskill.wiki import (
    SkillImpactEntry,
    load_skill_impacts,
    wiki_snapshot,
)
from wikiskill.wiki_maintainer import (
    MaintainerContractError,
    MaintainerResult,
    apply_pattern_edits,
    parse_maintainer_answer,
)
from pydantic import ValidationError

CATEGORY_ORDER: tuple[str, ...] = (
    "exec_failed",
    "missing_final_answer",
    "wrong_answer",
)
STDOUT_TAIL_LINES = 40
TRACE_SAMPLE_CAP = 12
_BANNED_SKILL_SUBSTRINGS: tuple[str, ...] = (
    "score_answer",
    "R_best",
    "r_best",
    "Eq. 4",
    "Eq.4",
    "officeqa_full.csv",
    "ground_truth",
    "gold answer",
    "true_negative_rate",
    "defect_recall",
)


def _load_outcome_rows(paths: list[Path]) -> list[dict]:
    rows: list[dict] = []
    for path in paths:
        for lineno, line in enumerate(
            Path(path).read_text(encoding="utf-8").splitlines(), start=1
        ):
            if not line.strip():
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError as exc:
                raise MaintainerContractError(
                    f"{path}:{lineno}: outcome row is not valid JSON: {exc}"
                ) from exc
            if not isinstance(row, dict):
                raise MaintainerContractError(
                    f"{path}:{lineno}: outcome row is not a JSON object"
                )
            rows.append(row)
    return rows


def _guard_train_only(rows: list[dict]) -> None:
    for row in rows:
        split = row.get("split")
        if split is not None and split != "train":
            raise MaintainerContractError(
                f"case {row.get('case_id')!r} carries split {split!r}; "
                "OfficeQA wiki agents consume train outcomes only"
            )


def _rows_by_case_id(rows: list[dict]) -> dict[str, dict]:
    indexed: dict[str, dict] = {}
    for row in rows:
        case_id = row.get("case_id") or row.get("uid")
        if isinstance(case_id, str) and case_id:
            indexed[case_id] = row
    return indexed


def _categories(row: Mapping[str, Any]) -> set[str]:
    reason = row.get("fail_reason") or ""
    if reason in CATEGORY_ORDER:
        return {reason}
    if row.get("score") == 1.0:
        return set()
    if row.get("returncode") not in (0, None):
        return {"exec_failed"}
    if not row.get("has_final_answer_tag"):
        return {"missing_final_answer"}
    return {"wrong_answer"}


def stratified_sample(outcome_rows: list[dict], *, max_cases: int = 12) -> list[str]:
    indexed = _rows_by_case_id(outcome_rows)
    buckets: dict[str, list[str]] = {name: [] for name in CATEGORY_ORDER}
    for case_id, row in indexed.items():
        for category in _categories(row):
            buckets[category].append(case_id)
    selected: list[str] = []
    chosen: set[str] = set()
    for category in CATEGORY_ORDER:
        for case_id in sorted(buckets[category]):
            if case_id not in chosen and len(selected) < max_cases:
                selected.append(case_id)
                chosen.add(case_id)
    for case_id in sorted(indexed):
        if len(selected) >= max_cases:
            break
        if case_id not in chosen:
            selected.append(case_id)
            chosen.add(case_id)
    return selected


def _category_summary(rows: list[dict]) -> dict[str, list[str]]:
    indexed = _rows_by_case_id(rows)
    summary: dict[str, list[str]] = {name: [] for name in CATEGORY_ORDER}
    for case_id, row in indexed.items():
        for category in _categories(row):
            summary[category].append(case_id)
    return {name: sorted(ids) for name, ids in summary.items()}


def _stdout_tail(text: str, *, max_lines: int = STDOUT_TAIL_LINES) -> str:
    return "\n".join(text.splitlines()[-max_lines:])


def _public_outcome(row: Mapping[str, Any]) -> dict[str, Any]:
    """Drop anything that could leak a gold answer into wiki memory."""
    keep = (
        "case_id",
        "uid",
        "split",
        "difficulty",
        "score",
        "predicted",
        "has_final_answer_tag",
        "returncode",
        "fail_reason",
        "source_files",
        "error",
    )
    return {key: row.get(key) for key in keep}


def compact_event_log(text: str, *, max_commands: int = 12) -> str:
    """Keep command lines only. File dumps in aggregated_output are dropped."""
    commands: list[str] = []
    for line in text.splitlines():
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        item = event.get("item")
        if not isinstance(item, dict) or item.get("type") != "command_execution":
            continue
        cmd = " ".join((item.get("command") or "").split())
        if len(cmd) > 160:
            cmd = cmd[:157] + "..."
        commands.append(f"{cmd} (exit {item.get('exit_code')})")
    if not commands:
        return "(no command_execution events parsed)"
    omitted = len(commands) - max_commands
    kept = commands[-max_commands:]
    prefix = f"({omitted} earlier commands omitted)\n" if omitted > 0 else ""
    return prefix + "\n".join(f"- {item}" for item in kept)


def _collect_trace(row: Mapping[str, Any]) -> dict[str, Any]:
    workspace = row.get("workspace")
    trace: dict[str, Any] = {
        "case_id": str(row.get("case_id") or row.get("uid") or "?"),
        "outcome": _public_outcome(row),
        "stdout_tail": None,
        "commands": None,
    }
    if not isinstance(workspace, str) or not workspace:
        return trace
    stdout_path = Path(workspace) / SCRATCH_DIR / "codex_stdout.txt"
    if stdout_path.is_file():
        trace["stdout_tail"] = _stdout_tail(stdout_path.read_text(encoding="utf-8"))
    events_path = Path(workspace) / SCRATCH_DIR / "codex_events.jsonl"
    if events_path.is_file():
        trace["commands"] = compact_event_log(
            events_path.read_text(encoding="utf-8")
        )
    return trace


def _assemble_maintainer_prompt(
    prompt_text: str,
    snapshot: Mapping[str, str],
    summary: Mapping[str, list[str]],
    traces: list[dict[str, Any]],
    *,
    answer_tag: str = "<FINAL_ANSWER>",
) -> str:
    parts: list[str] = [prompt_text.rstrip("\n")]
    parts.append("## Current wiki (read-only snapshot)\n")
    if snapshot:
        for relpath in sorted(snapshot):
            parts.append(f"### {relpath}\n\n{snapshot[relpath].rstrip()}\n")
    else:
        parts.append("(the wiki is empty: no pattern pages exist yet)\n")
    lines = [
        f"- exec failed ({len(summary['exec_failed'])} cases): "
        f"{', '.join(summary['exec_failed']) or 'none'}",
        f"- missing {answer_tag} tag ({len(summary['missing_final_answer'])} cases): "
        f"{', '.join(summary['missing_final_answer']) or 'none'}",
        f"- tagged but wrong ({len(summary['wrong_answer'])} cases): "
        f"{', '.join(summary['wrong_answer']) or 'none'}",
    ]
    parts.append(
        "## Iteration evidence summary (train outcomes only)\n\n"
        + "\n".join(lines)
        + "\n"
    )
    parts.append(f"## Sampled rollout traces ({len(traces)} cases)\n")
    if not traces:
        parts.append("(no cases were sampled this iteration)\n")
    for trace in traces:
        case_id = trace["case_id"]
        outcome_json = json.dumps(trace["outcome"], indent=2)
        parts.append(f"### case {case_id} -- outcome (no gold answer)\n\n```json\n{outcome_json}\n```\n")
        if trace.get("stdout_tail"):
            parts.append(
                f"### case {case_id} -- stdout tail\n\n```text\n"
                f"{trace['stdout_tail'].rstrip()}\n```\n"
            )
        else:
            parts.append(
                f"### case {case_id} -- stdout tail\n\n"
                "[trace missing: no codex_stdout.txt]\n"
            )
        if trace.get("commands"):
            parts.append(
                f"### case {case_id} -- commands (bodies omitted)\n\n"
                f"{trace['commands'].rstrip()}\n"
            )
        parts.append(
            f"Full event log: traces/{case_id}/codex_events.jsonl "
            "(read on demand; do not paste it back).\n"
        )
    return "\n".join(parts) + "\n"


def _write_run_record(iter_dir: Path, record: dict[str, Any]) -> None:
    (iter_dir / "run.json").write_text(
        json.dumps(record, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


def build_maintainer(
    *,
    model: str,
    workdir: str | Path,
    reasoning_effort: str = "medium",
    exec_timeout_seconds: int = 900,
    answer_tag: str = "<FINAL_ANSWER>",
    domain: str = "OfficeQA",
):
    workdir = Path(workdir)

    def run_maintainer(
        train_outcomes_paths: list[Path],
        iteration: int,
        wiki_dir: Path,
    ) -> MaintainerResult:
        if iteration < 1:
            raise MaintainerContractError(f"iteration must be >= 1, got {iteration}")
        wiki_dir = Path(wiki_dir)
        prompt_path = wiki_dir / "prompts" / "maintainer.md"
        if not prompt_path.is_file():
            raise MaintainerContractError(f"maintainer prompt missing: {prompt_path}")
        rows = _load_outcome_rows(list(train_outcomes_paths))
        _guard_train_only(rows)
        sampled = stratified_sample(rows)
        rows_by_id = _rows_by_case_id(rows)
        iter_dir = workdir / ".maintainer" / f"iteration-{iteration}"
        if iter_dir.exists():
            shutil.rmtree(iter_dir)
        iter_dir.mkdir(parents=True)
        sampled_rows = [rows_by_id[case_id] for case_id in sampled]
        _stage_traces(iter_dir / "traces", sampled_rows)
        traces = [_collect_trace(row) for row in sampled_rows]
        prompt = _assemble_maintainer_prompt(
            prompt_path.read_text(encoding="utf-8"),
            wiki_snapshot(wiki_dir),
            _category_summary(rows),
            traces,
            answer_tag=answer_tag,
        )
        if len(prompt) > 900_000:
            raise MaintainerContractError(
                f"maintainer prompt is {len(prompt)} chars; exceeds the "
                "900k safety cap (event bodies must not be inlined)"
            )
        prompt_sha256 = hashlib.sha256(prompt.encode("utf-8")).hexdigest()
        (iter_dir / "prompt.md").write_text(prompt, encoding="utf-8")
        record: dict[str, Any] = {
            "agent": f"{domain.lower()}-wiki-maintainer",
            "iteration": iteration,
            "model": model,
            "reasoning_effort": reasoning_effort,
            "prompt_sha256": prompt_sha256,
            "sampled_case_ids": sampled,
        }
        try:
            proc = run_codex_exec(
                prompt=prompt,
                workdir=iter_dir,
                model=model,
                reasoning_effort=reasoning_effort,
                timeout_seconds=exec_timeout_seconds,
            )
        except Exception as exc:  # noqa: BLE001
            record["error"] = f"{type(exc).__name__}: {exc}"
            _write_run_record(iter_dir, record)
            raise
        (iter_dir / "codex_stdout.txt").write_text(proc.stdout, encoding="utf-8")
        (iter_dir / "codex_stderr.txt").write_text(proc.stderr, encoding="utf-8")
        record["returncode"] = proc.returncode
        if proc.returncode != 0:
            record["error"] = f"codex exec exited {proc.returncode}"
            _write_run_record(iter_dir, record)
            raise RuntimeError(
                f"{domain} maintainer exec failed (exit {proc.returncode}); see {iter_dir}"
            )
        try:
            answer = parse_maintainer_answer(proc.stdout)
            new_files, updated_files = apply_pattern_edits(
                wiki_dir, answer, iteration=iteration
            )
        except MaintainerContractError as exc:
            record["error"] = str(exc)
            _write_run_record(iter_dir, record)
            raise
        record["applied"] = {
            "new_patterns": new_files,
            "updated_patterns": updated_files,
        }
        _write_run_record(iter_dir, record)
        return MaintainerResult(
            iteration=iteration,
            new_patterns=tuple(new_files),
            updated_patterns=tuple(updated_files),
            prompt_sha256=prompt_sha256,
            sampled_case_ids=tuple(sampled),
            stdout_path=iter_dir / "codex_stdout.txt",
        )

    return run_maintainer


def _summary_text(rows: list[dict], *, answer_tag: str = "<FINAL_ANSWER>") -> str:
    indexed = _rows_by_case_id(rows)
    n = len(indexed)
    n_correct = sum(1 for row in indexed.values() if row.get("score") == 1.0)
    summary = _category_summary(rows)
    lines = [
        f"train cases: {n}; correct: {n_correct}; accuracy: "
        f"{(n_correct / n) if n else 0:.4f}",
        f"exec failed: {len(summary['exec_failed'])}",
        *[f"  - {cid}" for cid in summary["exec_failed"]],
        f"missing {answer_tag} tag: {len(summary['missing_final_answer'])}",
        *[f"  - {cid}" for cid in summary["missing_final_answer"]],
        f"tagged but wrong: {len(summary['wrong_answer'])}",
        *[
            f"  - {cid}: predicted={indexed[cid].get('predicted')!r}"
            for cid in summary["wrong_answer"]
        ],
    ]
    return "\n".join(lines)


def _stage_traces(destination: Path, rows: list[dict]) -> list[str]:
    destination.mkdir(parents=True, exist_ok=True)
    staged: list[str] = []
    for case_id, row in sorted(_rows_by_case_id(rows).items()):
        if len(staged) >= TRACE_SAMPLE_CAP:
            break
        workspace = row.get("workspace")
        if not isinstance(workspace, str) or not workspace:
            continue
        stdout = Path(workspace) / SCRATCH_DIR / "codex_stdout.txt"
        if not stdout.is_file():
            continue
        case_dir = destination / case_id
        case_dir.mkdir(parents=True, exist_ok=True)
        shutil.copy2(stdout, case_dir / "codex_stdout.txt")
        events = Path(workspace) / SCRATCH_DIR / "codex_events.jsonl"
        if events.is_file():
            shutil.copy2(events, case_dir / "codex_events.jsonl")
        (case_dir / "outcome.json").write_text(
            json.dumps(_public_outcome(row), indent=2) + "\n", encoding="utf-8"
        )
        staged.append(case_id)
    return staged


def _validate_officeqa_skill(
    skill_md: str,
    *,
    purpose: ProposalPurpose,
    pattern_names: list[str],
) -> None:
    if not skill_md.strip():
        raise ProposerContractError("action 'skill' requires a non-blank skill_md")
    lines = skill_md.splitlines()
    if len(lines) > MAX_SKILL_LINES:
        raise ProposerContractError(
            f"skill_md exceeds the {MAX_SKILL_LINES}-line ceiling ({len(lines)} lines)"
        )
    if not lines[0].startswith("# "):
        raise ProposerContractError(
            f"skill_md must open with a single '# ' heading; first line is {lines[0]!r}"
        )
    if not purpose.motivated_by_patterns:
        raise ProposerContractError(
            "action 'skill' requires at least one motivated_by_patterns entry"
        )
    for name in purpose.motivated_by_patterns:
        if name not in pattern_names:
            raise ProposerContractError(
                f"motivated_by_patterns names unknown pattern page {name!r}; "
                f"existing pages: {pattern_names}"
            )
    for banned in _BANNED_SKILL_SUBSTRINGS:
        if banned in skill_md:
            raise ProposerContractError(
                f"skill_md contains evaluation-vocabulary string {banned!r}"
            )


def _validate_proposer_answer(
    answer: dict[str, Any],
    *,
    incumbent: str,
    pattern_names: list[str],
) -> tuple[str, str, ProposalPurpose, str, str]:
    action = answer.get("action")
    if action not in ("skill", "no_action"):
        raise ProposerContractError(
            f"action must be 'skill' or 'no_action', got {action!r}"
        )
    skill_md = _required_string(answer, "skill_md")
    rationale = _required_string(answer, "rationale")
    purpose_raw = answer.get("purpose")
    if not isinstance(purpose_raw, dict):
        raise ProposerContractError("answer key 'purpose' must be an object")
    try:
        purpose = ProposalPurpose.model_validate(purpose_raw)
    except ValidationError as exc:
        raise ProposerContractError(f"purpose is invalid: {exc}") from exc
    diff = ""
    if action == "skill":
        _validate_officeqa_skill(
            skill_md, purpose=purpose, pattern_names=pattern_names
        )
        diff = _unified_diff(incumbent, skill_md)
        changed = _changed_line_count(diff)
        if changed > MAX_DIFF_CHANGED_LINES:
            raise ProposerContractError(
                f"unified diff exceeds {MAX_DIFF_CHANGED_LINES} changed lines "
                f"({changed})"
            )
    else:
        if skill_md:
            raise ProposerContractError(
                f"action 'no_action' requires empty skill_md (got {len(skill_md)} chars)"
            )
        if purpose.motivated_by_patterns:
            raise ProposerContractError(
                "action 'no_action' requires empty motivated_by_patterns"
            )
    return action, skill_md, purpose, rationale, diff


def _build_proposer_prompt(
    *,
    prompt_text: str,
    iteration: int,
    index_text: str,
    impacts_text: str,
    summary_text: str,
    incumbent_text: str,
    pattern_names: list[str],
    trace_case_ids: list[str],
) -> str:
    if incumbent_text.strip():
        incumbent_block = "```markdown\n" + incumbent_text.rstrip("\n") + "\n```"
    else:
        incumbent_block = "(empty — S0, no skill injected)"
    pattern_lines = [f"- wiki/patterns/{name}" for name in pattern_names] or [
        "- wiki/patterns/ — no pattern pages exist yet"
    ]
    trace_lines: list[str] = []
    for case_id in trace_case_ids:
        trace_lines.append(f"- traces/{case_id}/codex_stdout.txt")
        trace_lines.append(f"- traces/{case_id}/codex_events.jsonl")
    if not trace_lines:
        trace_lines = ["- traces/ — no train traces were staged"]
    context = "\n".join(
        [
            "---",
            "",
            f"## Context block (harness-supplied; iteration {iteration})",
            "",
            "### Wiki index (wiki/index.md, verbatim)",
            "",
            index_text.rstrip("\n") or "(no index staged)",
            "",
            "### Skill-impact entries",
            "",
            impacts_text,
            "",
            "### Train outcome summary",
            "",
            summary_text,
            "",
            "### Incumbent SKILL.md (current/SKILL.md)",
            "",
            incumbent_block,
            "",
            "### Staged files you may read on demand",
            "",
            *pattern_lines,
            *trace_lines,
        ]
    )
    return prompt_text.rstrip("\n") + "\n\n" + context + "\n"


def _render_impacts(impacts: list[SkillImpactEntry]) -> str:
    if not impacts:
        return "(no prior gating outcomes)"
    lines: list[str] = []
    for entry in impacts:
        lines.append(
            f"- iteration {entry.iteration}: {entry.proposal_kind} -> "
            f"{entry.gate_verdict}"
            + (" (ACCEPTED)" if entry.accepted else " (not accepted)")
        )
        if entry.purpose_summary:
            lines.append(f"  purpose: {entry.purpose_summary}")
        if entry.motivated_by_patterns:
            lines.append(f"  patterns: {', '.join(entry.motivated_by_patterns)}")
    return "\n".join(lines)


def build_proposer(
    *,
    model: str,
    workdir: str | Path,
    reasoning_effort: str = "medium",
    exec_timeout_seconds: int = 900,
    answer_tag: str = "<FINAL_ANSWER>",
    domain: str = "OfficeQA",
):
    workdir = Path(workdir)

    def run_proposer(
        incumbent_skill_text: str,
        train_outcomes_paths: list[Path],
        iteration: int,
        wiki_dir: Path,
    ) -> ProposalResult:
        if iteration < 1:
            raise ValueError("iteration numbers are 1-based")
        rows = _load_outcome_rows([Path(path) for path in train_outcomes_paths])
        _guard_train_only(rows)
        if not rows:
            raise ProposerContractError("no train outcome records were supplied")
        iteration_dir = workdir / ".proposer" / f"iteration-{iteration}"
        if iteration_dir.exists():
            shutil.rmtree(iteration_dir)
        iteration_dir.mkdir(parents=True)
        staged_wiki = iteration_dir / "wiki"
        staged_wiki.mkdir()
        for name in ("index.md", "skill-impact.md"):
            source = wiki_dir / name
            if source.is_file():
                shutil.copy2(source, staged_wiki / name)
        patterns = wiki_dir / "patterns"
        if patterns.is_dir():
            shutil.copytree(patterns, staged_wiki / "patterns")
        current = iteration_dir / "current"
        current.mkdir()
        (current / "SKILL.md").write_text(incumbent_skill_text, encoding="utf-8")
        trace_ids = _stage_traces(iteration_dir / "traces", rows)
        index_text = (
            (staged_wiki / "index.md").read_text(encoding="utf-8")
            if (staged_wiki / "index.md").is_file()
            else ""
        )
        impacts = load_skill_impacts(staged_wiki / "skill-impact.md")
        patterns_dir = staged_wiki / "patterns"
        pattern_names = (
            sorted(path.name for path in patterns_dir.glob("*.md"))
            if patterns_dir.is_dir()
            else []
        )
        prompt_path = wiki_dir / "prompts" / "proposer.md"
        prompt = _build_proposer_prompt(
            prompt_text=prompt_path.read_text(encoding="utf-8"),
            iteration=iteration,
            index_text=index_text,
            impacts_text=_render_impacts(impacts),
            summary_text=_summary_text(rows, answer_tag=answer_tag),
            incumbent_text=incumbent_skill_text,
            pattern_names=pattern_names,
            trace_case_ids=trace_ids,
        )
        prompt_sha256 = hashlib.sha256(prompt.encode("utf-8")).hexdigest()
        (iteration_dir / "prompt.md").write_text(prompt, encoding="utf-8")
        proc = run_codex_exec(
            prompt=prompt,
            workdir=iteration_dir,
            model=model,
            reasoning_effort=reasoning_effort,
            timeout_seconds=exec_timeout_seconds,
        )
        stdout_path = iteration_dir / "codex_stdout.txt"
        stdout_path.write_text(proc.stdout, encoding="utf-8")
        (iteration_dir / "codex_stderr.txt").write_text(proc.stderr, encoding="utf-8")
        if proc.returncode != 0:
            raise RuntimeError(
                f"{domain} proposer exec failed (exit {proc.returncode}); "
                f"see {iteration_dir}"
            )
        answer = _extract_answer(proc.stdout)
        action, skill_md, purpose, rationale, diff = _validate_proposer_answer(
            answer, incumbent=incumbent_skill_text, pattern_names=pattern_names
        )
        return ProposalResult(
            action=action,
            skill_md=skill_md,
            purpose=purpose,
            rationale=rationale,
            prompt_sha256=prompt_sha256,
            diff=diff,
            stdout_path=stdout_path,
        )

    return run_proposer
