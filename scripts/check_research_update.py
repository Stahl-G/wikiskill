#!/usr/bin/env python3
"""Recompute the allowlisted 2026-09-06 paired observations without model calls."""
from pathlib import Path
import argparse
import hashlib
import json
import math
import random
import statistics


def analyze(rows, seed, samples):
    if len({r['uid'] for r in rows}) != len(rows):raise ValueError('Duplicate task ID')
    if any(set(r) != {'uid', 's0', 'sk'} or r['s0'] not in (0, 1) or r['sk'] not in (0, 1) for r in rows):
        raise ValueError('Unexpected fields or nonbinary score')
    n = len(rows);diff = [r['sk'] - r['s0'] for r in rows]
    wins, losses = diff.count(1), diff.count(-1);discordant = wins + losses
    p = min(1., 2 * sum(math.comb(discordant, k) for k in range(min(wins, losses) + 1)) / 2 ** discordant) if discordant else 1.
    rng = random.Random(seed);boot = sorted(sum(rng.choices(diff, k=n)) / n for _ in range(samples))
    def q(value):
        x = (samples - 1) * value;i = int(x)
        return boot[i] + (boot[min(i + 1, samples - 1)] - boot[i]) * (x - i)
    return {'n': n, 's0_correct': sum(r['s0'] for r in rows), 'skill_correct': sum(r['sk'] for r in rows),
            'delta': statistics.mean(diff), 'wins': wins, 'losses': losses,
            'both_correct': sum(r['s0'] == r['sk'] == 1 for r in rows),
            'both_wrong': sum(r['s0'] == r['sk'] == 0 for r in rows),
            'p_exact': p, 'bootstrap_95_ci': [q(.025), q(.975)]}


def check(root):
    root = Path(root)
    manifest = json.loads((root / 'manifest.json').read_text())
    for name, digest in manifest['files'].items():
        if hashlib.sha256((root / name).read_bytes()).hexdigest() != digest:raise ValueError('Artifact changed: ' + name)
    studies = json.loads((root / 'studies.json').read_text())
    result = []
    for study in studies['completed_observations']:
        rows = json.loads((root / study['pairs_file']).read_text())
        computed = analyze(rows, study['bootstrap_seed'], study['bootstrap_samples'])
        if computed != study['statistics']:raise ValueError('Statistics mismatch: ' + study['id'])
        result.append({'study': study['id'], 'validity': study['validity'], **computed})
    return result


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('directory', nargs='?', type=Path,
        default=Path(__file__).resolve().parents[1] / 'src/wikiskill/resources/research/update-20260906')
    args = p.parse_args()
    print(json.dumps(check(args.directory), indent=2))
