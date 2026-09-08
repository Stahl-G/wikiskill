"""Read-only product diagnostics and reports derived from the event journal."""
from importlib import metadata
from pathlib import Path
import difflib
import re
import sys

from . import product as p


def identity():
    try:
        version = metadata.version('wikiskill-research')
    except metadata.PackageNotFoundError:
        version = 'unknown (source checkout)'
    return {'project': 'Stahl-G/wikiskill', 'distribution': 'wikiskill-research',
            'version': version, 'module': str(Path(p.__file__).resolve()),
            'python': sys.executable}


def preflight(root):
    """Inspect readiness without running a checker, issuing work or changing state."""
    root = Path(root).resolve()
    s = p._load(root)
    issues = []
    warnings = []
    counts = {split: sum(t['split'] == split for t in s['tasks'])
              for split in ('train', 'validation')}
    try:
        p._check_task_files(s)
    except ValueError as exc:
        issues.append(str(exc))
    if not all(counts.values()):
        issues.append('Attach training and validation tasks with wikiskill tasks.')
    missing = sorted({f for t in s['tasks'] for f in t['files'] if not Path(f).is_file()})
    if missing:
        issues.append('Restore missing task files before requesting work.')
    groups = {}
    for t in s['tasks']:
        for key in ([('group', str(t['group']))] if t.get('group') is not None else []) + [('file', f) for f in t['files']]:
            groups.setdefault(key, set()).add(t['split'])
    shared = [{'kind': k[0], 'value': k[1]} for k, splits in groups.items() if len(splits) > 1]
    if shared:
        warnings.append('Some sources occur in both splits. Check whether these are shared resources or near-duplicate cases before interpreting validation.')
    checker = None
    if s['config']['scorer']:
        try:
            checker = p.scorer_inspect(root)
            p._check_scorer_comparison(s, checker)
            if not checker['trusted']:
                issues.append('Inspect and authorize the configured scorer before running tasks.')
        except (OSError, ValueError, RuntimeError) as exc:
            issues.append('Scorer configuration: ' + str(exc))
    else:
        warnings.append('Manual scoring: use the agreed rubric and record its evaluation basis with each score.')
    if not Path(s['config']['project']).is_dir():
        issues.append('Restore the configured project directory.')
    failures = [r for r in s['requests'].values() if r['status'] == 'failed']
    if failures:
        issues.append('Resolve the recorded failures, then retry those requests; do not restart the workspace.')
    return {'identity': identity(), 'workspace': str(root), 'ready': not issues,
            'task_counts': counts, 'missing_files': missing, 'shared_sources': shared,
            'issues': issues, 'warnings': warnings, 'scorer': checker,
            'checks': 'File and command availability only; no scorer or model was executed.',
            'evaluation_boundary': 'Normal host access; this check does not establish benchmark isolation.'}


def status_text(value):
    progress = value['progress']
    lines = [f"WikiSkill — {value['phase']} (round {value['round']}/{value['rounds']})",
             f"This phase: {progress['completed']}/{progress['total']} completed; {progress['pending']} pending",
             f"Retained score: {value['best_score'] if value['best_score'] is not None else 'not measured'} ({value['direction']})",
             'Next: ' + value['action'], 'Wiki: ' + value['wiki']]
    for failure in value['failures']:
        lines += [f"Failed {failure['id']}: {failure['error']}",
                  f"  After resolving the cause: wikiskill retry {value['workspace']!r} --request {failure['id']}"]
        if failure['output']:
            lines.append('  Saved output available for scoring retry: ' + failure['output'])
    return '\n'.join(lines)


def report(root):
    root = Path(root).resolve()
    s = p._load(root)
    baseline = p._task_results(s, 'baseline', 1)
    baseline_score = sum(x['score'] for x in baseline.values()) / len(baseline) if baseline else None
    baseline_complete = len(baseline) == sum(t['split'] == 'validation' for t in s['tasks']) and bool(baseline)
    comparisons = []
    incumbent = baseline
    incumbent_skill = s['config']['initial_skill']
    sign = 1 if s['config']['direction'] == 'maximize' else -1
    for gate in s['history']:
        candidate = p._task_results(s, 'validation', gate['round'])
        pairs = []
        for uid in sorted(set(incumbent) & set(candidate)):
            before, after = incumbent[uid]['score'], candidate[uid]['score']
            delta = (after - before) * sign
            pairs.append({'id': uid, 'incumbent': before, 'candidate': after,
                          'outcome': 'improved' if delta > 0 else 'regressed' if delta < 0 else 'unchanged'})
        before = (root / incumbent_skill['file']).read_text(encoding='utf-8') if incumbent_skill else ''
        cs = gate['candidate_skill']
        after = (root / cs['file']).read_text(encoding='utf-8') if cs else None
        diff = ''.join(difflib.unified_diff(before.splitlines(keepends=True), after.splitlines(keepends=True),
                                          fromfile='incumbent', tofile='candidate')) if after is not None else ''
        comparisons.append({**gate, 'pairs': pairs, 'diff': diff})
        if gate['accepted']:
            incumbent = candidate
            incumbent_skill = cs
    return {'workspace': str(root), 'phase': p._status(root, s)['phase'],
            'source_event_sha256': s['last_hash'], 'direction': s['config']['direction'],
            'min_improvement': s['config']['min_improvement'],
            'baseline_score': baseline_score if baseline_complete else None,
            'baseline_completed': len(baseline), 'baseline_complete': baseline_complete,
            'retained_score': s['best_score'], 'retained_skill': s['current_skill'],
            'delegations': [{'request_id':r['id'],'kind':r['kind'],'status':r['status'],**r['delegation']} for r in s['requests'].values() if r.get('delegation')],
            'rounds': comparisons, 'patterns': s['patterns'], 'feedback_count': len(s['feedback']),
            'wiki': str(root / 'wiki/index.md'),
            'evaluation': 'Validation selection under the host environment; no held-out or statistical improvement claim.',
            'next_action': ('Export the retained skill with wikiskill export, or install to an explicitly chosen local directory.'
                            if s['phase'] == 'complete' and s['current_skill'] else
                            'No retained skill to export. The Wiki and candidate records remain available.' if s['phase'] == 'complete' else
                            'Continue the existing workspace with wikiskill next; this report is partial.')}


def report_markdown(value):
    lines = ['# WikiSkill result', '', f"State: **{value['phase']}**", '',
             f"Baseline: {value['baseline_score'] if value['baseline_complete'] else 'not yet complete'}",
             f"Retained score: {value['retained_score'] if value['retained_score'] is not None else 'not measured'}",
             f"Direction: {value['direction']}; required improvement: strictly greater than {value['min_improvement']}", '',
             value['evaluation'], '', '## Rounds', '']
    if not value['rounds']:
        lines.append('No completed candidate decision yet.')
    for g in value['rounds']:
        lines += [f"### Round {g['round']}: {g['verdict']}", '',
                  f"Incumbent: {g['incumbent_score']}; candidate: {g['candidate_score'] if g['candidate_score'] is not None else 'not evaluated'}", '',
                  'Proposal note (agent supplied): ' + g['note'], '',
                  '| Task | Incumbent | Candidate | Outcome |', '|---|---:|---:|---|']
        for row in g['pairs']:
            uid = row['id'].replace('|', '\\|').replace('\n', ' ')
            lines.append(f"| {uid} | {row['incumbent']} | {row['candidate']} | {row['outcome']} |")
        if g['diff']:
            # A fence longer than any run of backticks in user content keeps the diff literal.
            fence = '`' * max(3, max((len(x) for x in re.findall(r'`+', g['diff'])), default=0) + 1)
            lines += ['', 'Skill changes:', '', fence + 'diff', g['diff'], fence, '']
    lines += ['', '## Agent execution', '']
    if value['delegations']:
        for d in value['delegations']:
            reuse='; reused execution from '+d['reused_from'] if d.get('reused_from') else ''
            lines.append(f"- {d['request_id']}: {d['runtime']} / {d['agent_id']} / {d['context_mode']}{reuse}")
        lines.append('These are host-reported IDs and context modes, not independent isolation attestations.')
    else:
        lines.append('No native subagent provenance recorded (direct-host or legacy workflow).')
    lines += ['', '## Learned patterns', '']
    for name, pattern in value['patterns'].items():
        lines += ['### ' + name, '', pattern['content'], '', 'Sources: ' + ', '.join(pattern['sources']), '']
    if not value['patterns']:
        lines.append('No patterns recorded yet.')
    lines += ['', f"Human feedback notes retained: {value['feedback_count']}",
              'Wiki: ' + value['wiki'], '', '## Use the result', '', value['next_action'], '',
              'Source event hash: ' + str(value['source_event_sha256']), '']
    return '\n'.join(lines)
