#!/usr/bin/env python3
"""Recompute frozen-skill repetition results from public score-only records."""
from pathlib import Path
import argparse, hashlib, json, random, statistics
from check_research_update import analyze


def contrast(batches, uids, seed=2026090804):
    maps=[{r['uid']:r for r in rows} for rows in batches]
    values=[statistics.mean(m[u]['sk']-m[u]['s0'] for m in maps) for u in uids]
    rng=random.Random(seed);samples=sorted(statistics.mean(rng.choices(values,k=len(uids))) for _ in range(10000))
    def q(p):
        x=9999*p;i=int(x);return samples[i]+(samples[min(i+1,9999)]-samples[i])*(x-i)
    return {'uid_clusters':len(uids),'repeats':len(maps),'paired_observations':len(uids)*len(maps),'mean_s0_accuracy':statistics.mean(m[u]['s0'] for m in maps for u in uids),'mean_skill_accuracy':statistics.mean(m[u]['sk'] for m in maps for u in uids),'mean_paired_delta':statistics.mean(values),'uid_cluster_bootstrap_95_ci':[q(.025),q(.975)],'bootstrap_seed':seed,'bootstrap_samples':10000,'inference':'exploratory fixed-skill replication'}


def check(root):
    root=Path(root);load=lambda name:json.loads((root/name).read_text())
    for name,h in load('manifest.json')['files'].items():
        if hashlib.sha256((root/name).read_bytes()).hexdigest()!=h:raise ValueError('Artifact hash differs: '+name)
    summary=load('summary.json');batches=[load(f'repeat{n}-pairs.json') for n in (1,2,3)]
    uids=summary['uids'];per=[]
    if len(uids)!=278 or len(set(uids))!=278:raise ValueError('Unexpected task roster')
    for n,rows in enumerate(batches,1):
        if len(rows)!=278 or {r['uid'] for r in rows}!=set(uids):raise ValueError('Incomplete repetition')
        a=analyze(rows,2026090804,10000)
        if any(a[k]!=summary['per_repeat'][n-1][k] for k in ('n','s0_correct','skill_correct','delta','wins','losses')):raise ValueError('Repetition score differs')
        per.append(a)
    for key,rows in [('primary_new_repeat2_and_3',batches[1:]),('supplementary_all_three',batches)]:
        if contrast(rows,uids)!=summary[key]:raise ValueError('Cluster analysis differs: '+key)
    maps=[{r['uid']:r for r in rows} for rows in batches];transitions={}
    for i,j in ((0,1),(1,2),(0,2)):
        transitions[f'repeat{i+1}_to_repeat{j+1}']={'wrong_to_correct':sum(maps[i][u]['s0']==0 and maps[j][u]['s0']==1 for u in uids),'correct_to_wrong':sum(maps[i][u]['s0']==1 and maps[j][u]['s0']==0 for u in uids)}
    flips={'uids_with_any_flip':sum(len({m[u]['s0'] for m in maps})>1 for u in uids),'transitions':transitions}
    if flips!=summary['s0_repeat_flips']:raise ValueError('Repeatability counts differ')
    return {'verified':True,'per_repeat':per,'primary':summary['primary_new_repeat2_and_3'],'supplementary':summary['supplementary_all_three'],'s0_repeat_flips':flips}

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('directory',nargs='?',type=Path,default=Path(__file__).resolve().parents[1]/'src/wikiskill/resources/research/repeatability-20260908')
    print(json.dumps(check(p.parse_args().directory),indent=2))
