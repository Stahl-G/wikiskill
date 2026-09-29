"""MCP stdio server for the host-agent product workflow.

Tools call the same functions as the product CLI; they invoke no model. Scorer
authorization, skill installation and restoration stay CLI-only so a connected
agent cannot approve its own scorer command or overwrite local skills.
"""
from pathlib import Path
import json
import tempfile
from typing import Any

from . import product as p
from . import product_views as views

INSTRUCTIONS = (
    'WikiSkill improves a reusable SKILL.md from your task outputs and scores. '
    'Loop: wikiskill_next returns work requests; you perform each one with your own tools, then '
    'submit it with wikiskill_record (task output), wikiskill_learn (Wiki patterns) or '
    'wikiskill_propose (candidate skill). Use absolute workspace paths. If next reports '
    'needs_scorer_trust, ask the user to run `wikiskill scorer inspect` and `wikiskill scorer trust` '
    'in a terminal; this server cannot authorize scorers.')


def _path(value):
    return None if value is None else Path(value).expanduser()


def _one(path, text, label):
    if (path is None) == (text is None):
        raise ValueError(f'Provide exactly one of {label}_path or {label}_text')


def _staged(text, name, call):
    # Product functions copy submitted files into the workspace; the temporary copy is discarded.
    with tempfile.TemporaryDirectory(prefix='wikiskill-mcp-') as directory:
        f = Path(directory)/name
        f.write_text(text, encoding='utf-8')
        return call(f)


def start(workspace: str, tasks: str | None = None, skill: str | None = None, rounds: int = 1,
          direction: str = 'maximize', min_improvement: float = 0.0, scorer: list[str] | None = None,
          scorer_timeout: float = 120, project: str | None = None, from_workspace: str | None = None) -> dict:
    """Create a workspace from a task JSON file. A scorer is a JSON command array; it must be
    authorized by the user in a terminal before it runs. No model calls."""
    return p.start(_path(workspace), tasks=_path(tasks), skill=_path(skill), rounds=rounds, direction=direction,
                   min_improvement=min_improvement, scorer=scorer, scorer_timeout=scorer_timeout,
                   project=_path(project), from_workspace=_path(from_workspace))


def next_work(workspace: str, count: int = 1) -> dict:
    """Return the current phase and up to `count` work requests (task, maintainer or proposer)."""
    return p.next_work(_path(workspace), count)


def record(workspace: str, request: str, output_path: str | None = None, output_text: str | None = None,
           output_name: str = 'output.txt', score: float | None = None, feedback: str = '',
           success: bool | None = None, trace_text: str | None = None, model: str | None = None,
           runtime: str | None = None, effort: str | None = None) -> dict:
    """Record the actual output of a task request. Give a score unless a configured scorer grades it."""
    _one(output_path, output_text, 'output')

    def submit(output, trace=None):
        return p.record(_path(workspace), request, output=output, score=score, feedback=feedback, success=success,
                        model=model, runtime=runtime, effort=effort, trace=trace)

    def with_trace(output):
        return _staged(trace_text, 'trace.txt', lambda t: submit(output, t)) if trace_text is not None else submit(output)
    return with_trace(_path(output_path)) if output_path else _staged(output_text, Path(output_name).name, with_trace)


def learn(workspace: str, request: str, patterns: dict[str, Any] | None = None, patterns_path: str | None = None) -> dict:
    """Submit Wiki pattern updates for a maintainer request, as {"patterns": [{name, content, sources}]}."""
    if (patterns is None) == (patterns_path is None):
        raise ValueError('Provide exactly one of patterns or patterns_path')
    if patterns_path:
        return p.learn(_path(workspace), request, _path(patterns_path))
    return _staged(json.dumps(patterns, ensure_ascii=False), 'patterns.json', lambda f: p.learn(_path(workspace), request, f))


def propose(workspace: str, request: str, skill_text: str | None = None, skill_path: str | None = None,
            no_action: bool = False, note: str = '') -> dict:
    """Submit a candidate SKILL.md for a proposer request, or no_action."""
    if no_action:
        if skill_text is not None or skill_path is not None:
            raise ValueError('no_action takes no skill')
        return p.propose(_path(workspace), request, note=note, no_action=True)
    _one(skill_path, skill_text, 'skill')
    if skill_path:
        return p.propose(_path(workspace), request, skill=_path(skill_path), note=note)
    return _staged(skill_text, 'SKILL.md', lambda f: p.propose(_path(workspace), request, skill=f, note=note))


def feedback(workspace: str, text: str, source: str | None = None) -> dict:
    """Add user feedback to the Wiki inbox."""
    return p.feedback(_path(workspace), text, source)


def retry(workspace: str, request: str) -> dict:
    """Explicitly retry a failed request after its cause is resolved."""
    return p.retry(_path(workspace), request)


def status(workspace: str) -> dict:
    """Read workspace progress, retained skill and gate history."""
    return p.status(_path(workspace))


def report(workspace: str) -> dict:
    """Read the result report derived from the workspace journal."""
    return views.report(_path(workspace))


def preflight(workspace: str) -> dict:
    """Check task files and scorer readiness without executing anything."""
    return views.preflight(_path(workspace))


def scorer_inspect(workspace: str) -> dict:
    """Show the configured scorer command and fingerprint. Authorization is terminal-only."""
    return p.scorer_inspect(_path(workspace))


def export(workspace: str, destination: str) -> dict:
    """Export the retained skill and its provenance to a new directory."""
    return p.export(_path(workspace), _path(destination))


def capabilities() -> dict:
    """List product capabilities. No model calls."""
    return p.capabilities()


TOOLS = {'wikiskill_'+f.__name__.removesuffix('_work'): f for f in
         (start, next_work, record, learn, propose, feedback, retry, status, report, preflight, scorer_inspect, export, capabilities)}


def build_server():
    try:
        from mcp.server.fastmcp import FastMCP
    except ImportError as exc:
        raise RuntimeError("MCP support is optional; install it with: python -m pip install 'wikiskill-research[mcp] @ git+https://github.com/Stahl-G/wikiskill.git'") from exc
    server = FastMCP('wikiskill', instructions=INSTRUCTIONS)
    for name, function in TOOLS.items():
        server.add_tool(function, name=name)
    return server


def run():
    build_server().run()
